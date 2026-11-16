#!/usr/bin/env python3
"""Agente SentinelIoT para o laboratório de rede doméstica simulada.

Lê os metadados produzidos pelo honeypot Apache, classifica eventos, registra
em SQLite e, no modo ``enforce``, bloqueia temporariamente o IP de origem com
nftables (ou iptables como fallback).

Privacidade: senhas, corpos de requisição, query strings e payloads nunca são
persistidos. O honeypot envia apenas IP, porta, caminho, método, código HTTP,
User-Agent truncado e tipo de evento.

Modos:
  observe  - apenas registra (padrão)
  dry_run  - calcula e audita a decisão, sem alterar o firewall
  enforce  - aplica bloqueio temporário nas faixas autorizadas do laboratório
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import logging
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import unquote_plus

DEFAULT_CONFIG = Path("/etc/sentinel/agent.json")
DEFAULT_SPOOL = Path("/var/log/sentinel/honeypot.jsonl")
DEFAULT_ACCESS_LOG = Path("/var/log/sentinel/apache/sentinel-access.log")
DEFAULT_DATABASE = Path("/var/lib/sentinel/sentinel.db")
DEFAULT_LOG = Path("/var/log/sentinel/agent.log")

LAB_NETWORKS = (
    ipaddress.ip_network("10.10.10.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
)
PROTECTED_ADDRESSES = {
    ipaddress.ip_address("10.10.10.1"),   # roteador / gateway do laboratório
    ipaddress.ip_address("10.10.10.10"),  # próprio honeypot
    ipaddress.ip_address("203.0.113.2"),  # WAN do roteador
    ipaddress.ip_address("127.0.0.1"),
}
MGMT_NETWORK = ipaddress.ip_network("192.168.57.0/24")

ATTACK_TOOL_RE = re.compile(
    r"(sqlmap|nikto|hydra|medusa|nmap|masscan|gobuster|ffuf|dirb|dirbuster|"
    r"wpscan|nuclei|zaproxy|acunetix|openvas|nessus|whatweb)",
    re.IGNORECASE,
)
INJECTION_RE = re.compile(
    r"(union\s+select|or\s+1\s*=\s*1|'\s*or\s*'|sleep\s*\(|benchmark\s*\(|"
    r"information_schema|--\s|/\*.*?\*/|<\s*script)",
    re.IGNORECASE,
)
SENSITIVE_PATH_RE = re.compile(
    r"(/admin|/camera|/api|/cgi-bin|/\.env|/\.git|/phpmyadmin|/server-status|"
    r"/wp-admin|/manager|/console)",
    re.IGNORECASE,
)

ACCESS_RE = re.compile(
    r"^(?P<ip>[^|]+)\|(?P<ts>[^|]+)\|(?P<method>[^|]+)\|"
    r"(?P<path>[^|]*)\|(?P<query>[^|]*)\|(?P<status>\d+)\|(?P<ua>.*)$"
)

SEVERITY_BY_TYPE = {
    "attack_tool": "high",
    "injection_attempt": "high",
    "credential_attempt": "high",
    "config_attempt": "medium",
    "auth_failure": "medium",
    "honeypot_probe": "medium",
    "request": "low",
}

SCORE_BY_TYPE = {
    "attack_tool": 5,
    "injection_attempt": 5,
    "credential_attempt": 3,
    "config_attempt": 3,
    "auth_failure": 2,
    "honeypot_probe": 2,
    "request": 1,
}

LOGGER = logging.getLogger("sentinel")


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


@dataclass
class Settings:
    mode: str = "observe"
    block_seconds: int = 300
    threshold: int = 5
    window_seconds: int = 120
    max_active_blocks: int = 20
    spool: Path = DEFAULT_SPOOL
    access_log: Path = DEFAULT_ACCESS_LOG
    database: Path = DEFAULT_DATABASE
    log: Path = DEFAULT_LOG

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG) -> Settings:
        data: dict[str, Any] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        settings = cls(
            mode=str(data.get("mode", cls.mode)),
            block_seconds=int(data.get("block_seconds", cls.block_seconds)),
            threshold=int(data.get("threshold", cls.threshold)),
            window_seconds=int(data.get("window_seconds", cls.window_seconds)),
            max_active_blocks=int(data.get("max_active_blocks", cls.max_active_blocks)),
            spool=Path(data.get("spool", str(cls.spool))),
            access_log=Path(data.get("access_log", str(cls.access_log))),
            database=Path(data.get("database", str(cls.database))),
            log=Path(data.get("log", str(cls.log))),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.mode not in {"observe", "dry_run", "enforce"}:
            raise ValueError(f"modo inválido: {self.mode}")
        if not 10 <= self.block_seconds <= 3600:
            raise ValueError("block_seconds deve estar entre 10 e 3600")
        if not 1 <= self.threshold <= 100:
            raise ValueError("threshold deve estar entre 1 e 100")
        if not 10 <= self.window_seconds <= 3600:
            raise ValueError("window_seconds deve estar entre 10 e 3600")
        if not 1 <= self.max_active_blocks <= 100:
            raise ValueError("max_active_blocks deve estar entre 1 e 100")


@dataclass
class Event:
    source_ip: str
    honeypot: str
    event_type: str
    path: str = ""
    method: str = ""
    status: int = 0
    user_agent: str = ""
    detail: str = ""
    timestamp: datetime = field(default_factory=utc_now)
    event_id: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            raw = f"{self.source_ip}|{iso(self.timestamp)}|{self.path}|{self.event_type}"
            self.event_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def severity(self) -> str:
        return SEVERITY_BY_TYPE.get(self.event_type, "low")

    @property
    def score(self) -> int:
        return SCORE_BY_TYPE.get(self.event_type, 1)


@dataclass
class Decision:
    source_ip: str
    action: str
    reason: str
    ttl: int = 0
    applied: bool = False
    adapter: str = ""
    detail: str = ""


def parse_ip(value: str) -> ipaddress.IPv4Address | None:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if not isinstance(address, ipaddress.IPv4Address):
        return None
    return address


def blockable(source_ip: str) -> tuple[bool, str]:
    """Só permite bloquear origens dentro do laboratório autorizado."""
    address = parse_ip(source_ip)
    if address is None:
        return False, "endereço inválido"
    if address in PROTECTED_ADDRESSES:
        return False, "endereço protegido"
    if address in MGMT_NETWORK:
        return False, "rede de gerenciamento protegida"
    if not any(address in network for network in LAB_NETWORKS):
        return False, "fora das faixas autorizadas do laboratório"
    return True, ""


def classify_access(line: str) -> list[Event]:
    match = ACCESS_RE.match(line.strip())
    if not match:
        return []

    source_ip = match.group("ip").strip()
    path = match.group("path").strip()
    query = match.group("query").strip()
    method = match.group("method").strip().upper()
    user_agent = match.group("ua").strip()[:200]
    try:
        status = int(match.group("status"))
    except ValueError:
        status = 0

    target = f"{path}{query}"
    decoded_target = unquote_plus(target)
    events: list[Event] = []

    if ATTACK_TOOL_RE.search(user_agent):
        events.append(
            Event(
                source_ip=source_ip,
                honeypot="http",
                event_type="attack_tool",
                path=path,
                method=method,
                status=status,
                user_agent=user_agent,
                detail="User-Agent de ferramenta de varredura/exploração",
            )
        )

    if INJECTION_RE.search(decoded_target):
        events.append(
            Event(
                source_ip=source_ip,
                honeypot="http",
                event_type="injection_attempt",
                path=path,
                method=method,
                status=status,
                user_agent=user_agent,
                detail="padrão de injeção na URL",
            )
        )

    if SENSITIVE_PATH_RE.search(path) and "/cgi-bin" not in path:
        events.append(
            Event(
                source_ip=source_ip,
                honeypot=_honeypot_from_path(path),
                event_type="honeypot_probe",
                path=path,
                method=method,
                status=status,
                user_agent=user_agent,
                detail="acesso a caminho de honeypot",
            )
        )

    if status in {401, 403}:
        events.append(
            Event(
                source_ip=source_ip,
                honeypot=_honeypot_from_path(path),
                event_type="auth_failure",
                path=path,
                method=method,
                status=status,
                user_agent=user_agent,
                detail=f"HTTP {status}",
            )
        )

    return events


def _honeypot_from_path(path: str) -> str:
    lowered = path.lower()
    if "/admin" in lowered:
        return "admin-portal"
    if "/camera" in lowered:
        return "camera-config"
    if "/api" in lowered:
        return "device-api"
    return "http"


def event_from_spool(line: str) -> Event | None:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None

    source_ip = str(data.get("source_ip", "")).strip()
    if parse_ip(source_ip) is None:
        return None

    try:
        timestamp = datetime.fromisoformat(str(data.get("timestamp_utc", "")))
    except ValueError:
        timestamp = utc_now()

    event_type = str(data.get("event_type", "request"))
    if event_type not in SEVERITY_BY_TYPE:
        event_type = "request"

    return Event(
        source_ip=source_ip,
        honeypot=str(data.get("honeypot", "http"))[:64],
        event_type=event_type,
        path=str(data.get("path", ""))[:256],
        method=str(data.get("method", ""))[:16],
        status=int(data.get("status", 0) or 0),
        user_agent=str(data.get("user_agent", ""))[:200],
        detail=str(data.get("detail", ""))[:200],
        timestamp=timestamp,
    )


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                timestamp_utc TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                honeypot TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                score INTEGER NOT NULL,
                path TEXT,
                method TEXT,
                status INTEGER,
                user_agent TEXT,
                detail TEXT,
                decision TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_timestamp ON events(timestamp_utc);
            CREATE INDEX IF NOT EXISTS events_source ON events(source_ip);

            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_ip TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                adapter TEXT NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                result TEXT NOT NULL,
                detail TEXT
            );
            """
        )
        self.connection.commit()

    def save_event(self, event: Event, decision: str) -> None:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO events (
                event_id, timestamp_utc, source_ip, honeypot, event_type,
                severity, score, path, method, status, user_agent, detail,
                decision, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                iso(event.timestamp),
                event.source_ip,
                event.honeypot,
                event.event_type,
                event.severity,
                event.score,
                event.path,
                event.method,
                event.status,
                event.user_agent,
                event.detail,
                decision,
                iso(utc_now()),
            ),
        )
        self.connection.commit()

    def save_block(self, source_ip: str, expires_at: datetime, reason: str, adapter: str) -> None:
        self.connection.execute(
            """
            INSERT INTO blocks (source_ip, created_at, expires_at, reason, adapter, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            ON CONFLICT(source_ip) DO UPDATE SET
                created_at=excluded.created_at,
                expires_at=excluded.expires_at,
                reason=excluded.reason,
                adapter=excluded.adapter,
                status='active'
            """,
            (source_ip, iso(utc_now()), iso(expires_at), reason, adapter),
        )
        self.connection.commit()

    def remove_block(self, source_ip: str) -> None:
        self.connection.execute("DELETE FROM blocks WHERE source_ip = ?", (source_ip,))
        self.connection.commit()

    def active_blocks(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM blocks WHERE status = 'active' ORDER BY created_at"
            )
        )

    def expired_blocks(self, now: datetime) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM blocks WHERE status = 'active' AND expires_at <= ?",
                (iso(now),),
            )
        )

    def audit(self, action: str, target: str, result: str, detail: str = "") -> None:
        self.connection.execute(
            """
            INSERT INTO audit_log (timestamp_utc, actor, action, target, result, detail)
            VALUES (?, 'sentinel-agent', ?, ?, ?, ?)
            """,
            (iso(utc_now()), action, target, result, detail[:500]),
        )
        self.connection.commit()

    def status(self) -> dict[str, Any]:
        by_type = {
            row["event_type"]: row["total"]
            for row in self.connection.execute(
                "SELECT event_type, COUNT(*) AS total FROM events GROUP BY event_type"
            )
        }
        by_honeypot = {
            row["honeypot"]: row["total"]
            for row in self.connection.execute(
                "SELECT honeypot, COUNT(*) AS total FROM events GROUP BY honeypot"
            )
        }
        return {
            "events": self.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "by_type": by_type,
            "by_honeypot": by_honeypot,
            "blocks": [dict(row) for row in self.active_blocks()],
        }

    def last_events(self, limit: int = 12) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            )
        )

    def close(self) -> None:
        self.connection.close()


class Firewall:
    """Bloqueio local no próprio honeypot (nftables, com fallback iptables)."""

    NFT_TABLE = "sentinel_lab"

    def __init__(self) -> None:
        self.adapter = "nftables" if shutil.which("nft") else "iptables"
        if self.adapter == "nftables" and not self._nft_works():
            self.adapter = "iptables"
        if self.adapter == "iptables" and not shutil.which("iptables"):
            self.adapter = "none"

    @staticmethod
    def _run(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def _nft_works(self) -> bool:
        result = self._run(["nft", "list", "tables"])
        return result.returncode == 0

    def _ensure_nft(self) -> None:
        check = self._run(["nft", "list", "table", "inet", self.NFT_TABLE])
        if check.returncode == 0:
            # Migração: instalações antigas tinham só a cadeia input. A cadeia
            # forward é necessária para bloquear portas publicadas pelo Docker.
            chain = self._run(
                ["nft", "list", "chain", "inet", self.NFT_TABLE, "forward"]
            )
            if chain.returncode != 0:
                self._run(
                    ["nft", "-f", "-"],
                    f"add chain inet {self.NFT_TABLE} forward "
                    "{ type filter hook forward priority -10; policy accept; }\n"
                    f"add rule inet {self.NFT_TABLE} forward ip saddr @blocked_v4 drop\n",
                )
            return

        script = (
            f"add table inet {self.NFT_TABLE}\n"
            f"add chain inet {self.NFT_TABLE} input "
            "{ type filter hook input priority -10; policy accept; }\n"
            f"add chain inet {self.NFT_TABLE} forward "
            "{ type filter hook forward priority -10; policy accept; }\n"
            f"add set inet {self.NFT_TABLE} blocked_v4 "
            "{ type ipv4_addr; flags timeout; }\n"
            f"add rule inet {self.NFT_TABLE} input ip saddr @blocked_v4 drop\n"
            f"add rule inet {self.NFT_TABLE} forward ip saddr @blocked_v4 drop\n"
        )
        result = self._run(["nft", "-f", "-"], script)
        if result.returncode != 0:
            raise RuntimeError(f"nftables: {result.stderr.strip()}")

    def block(self, source_ip: str, seconds: int) -> tuple[bool, str]:
        if self.adapter == "nftables":
            try:
                self._ensure_nft()
                script = (
                    f"add element inet {self.NFT_TABLE} blocked_v4 "
                    f"{{ {source_ip} timeout {seconds}s }}\n"
                )
                result = self._run(["nft", "-f", "-"], script)
                if result.returncode != 0:
                    return False, result.stderr.strip()
                listing = self._run(
                    ["nft", "list", "set", "inet", self.NFT_TABLE, "blocked_v4"]
                )
                if source_ip in listing.stdout:
                    return True, "regra nftables confirmada"
                return False, "regra não encontrada na confirmação"
            except (RuntimeError, OSError) as exc:
                return False, str(exc)

        if self.adapter == "iptables":
            for chain in ("INPUT", "FORWARD"):
                result = self._run(
                    ["iptables", "-I", chain, "1", "-s", source_ip, "-j", "DROP"]
                )
                if result.returncode != 0:
                    return False, result.stderr.strip()
            for chain in ("INPUT", "FORWARD"):
                check = self._run(
                    ["iptables", "-C", chain, "-s", source_ip, "-j", "DROP"]
                )
                if check.returncode != 0:
                    return False, f"regra iptables não confirmada em {chain}"
            return True, "regra iptables confirmada (input e forward)"

        return False, "nenhum adaptador de firewall disponível"

    def unblock(self, source_ip: str) -> tuple[bool, str]:
        if self.adapter == "nftables":
            script = (
                f"delete element inet {self.NFT_TABLE} blocked_v4 "
                f"{{ {source_ip} }}\n"
            )
            result = self._run(["nft", "-f", "-"], script)
            return result.returncode == 0, result.stderr.strip()

        if self.adapter == "iptables":
            removed = 0
            for chain in ("INPUT", "FORWARD"):
                check = self._run(
                    ["iptables", "-C", chain, "-s", source_ip, "-j", "DROP"]
                )
                if check.returncode != 0:
                    continue
                result = self._run(
                    ["iptables", "-D", chain, "-s", source_ip, "-j", "DROP"]
                )
                if result.returncode != 0:
                    return False, result.stderr.strip()
                removed += 1
            return True, f"{removed} regra(s) iptables removida(s)"

        return False, "nenhum adaptador de firewall disponível"


class Agent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(settings.database)
        self.firewall = Firewall()
        self.window: dict[str, deque[tuple[float, Event]]] = defaultdict(deque)
        self.blocked: dict[str, datetime] = {}
        self.running = True
        self._access_offset = 0
        self._spool_offset = 0

    def configure_logging(self) -> None:
        settings = self.settings
        settings.log.parent.mkdir(parents=True, exist_ok=True)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        LOGGER.setLevel(logging.INFO)
        LOGGER.handlers.clear()

        file_handler = logging.FileHandler(settings.log, encoding="utf-8")
        file_handler.setFormatter(formatter)
        LOGGER.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        LOGGER.addHandler(stream_handler)

    def reconcile(self) -> None:
        now = utc_now()
        for row in self.database.active_blocks():
            expires_at = datetime.fromisoformat(row["expires_at"])
            source_ip = row["source_ip"]
            if expires_at <= now:
                self._release(source_ip, "expirado na reconciliação")
                continue
            self.blocked[source_ip] = expires_at
            if self.settings.mode == "enforce":
                remaining = max(10, int((expires_at - now).total_seconds()))
                ok, detail = self.firewall.block(source_ip, remaining)
                LOGGER.info("reconciliação %s: %s (%s)", source_ip, ok, detail)

    def _release(self, source_ip: str, reason: str) -> None:
        # Remoção explícita: tenta sempre, mesmo em observe/dry_run, para não
        # deixar regra órfã de um teste anterior em enforce.
        self.firewall.unblock(source_ip)
        self.blocked.pop(source_ip, None)
        self.database.remove_block(source_ip)
        self.database.audit("unblock", source_ip, "ok", reason)
        LOGGER.info("desbloqueado %s (%s)", source_ip, reason)

    def expire_blocks(self) -> None:
        now = utc_now()
        for source_ip, expires_at in list(self.blocked.items()):
            if expires_at <= now:
                self._release(source_ip, "TTL expirado")
        for row in self.database.expired_blocks(now):
            self._release(row["source_ip"], "TTL expirado (banco)")

    def _score_for(self, source_ip: str, event: Event) -> int:
        now = time.monotonic()
        entries = self.window[source_ip]
        entries.append((now, event))
        while entries and now - entries[0][0] > self.settings.window_seconds:
            entries.popleft()
        return sum(item.score for _, item in entries)

    def decide(self, source_ip: str, event: Event) -> Decision:
        allowed, reason = blockable(source_ip)
        if not allowed:
            return Decision(source_ip, "none", f"origem não bloqueável: {reason}")

        score = self._score_for(source_ip, event)
        attempts = sum(
            1 for _, item in self.window[source_ip] if item.event_type == "credential_attempt"
        )

        if event.event_type in {"attack_tool", "injection_attempt"}:
            return Decision(source_ip, "block", f"{event.event_type} detectado (score {score})")
        if attempts >= 3:
            return Decision(source_ip, "block", f"{attempts} tentativas de credencial na janela")
        if score >= self.settings.threshold:
            return Decision(source_ip, "block", f"score {score} >= {self.settings.threshold}")

        return Decision(source_ip, "monitor", f"score {score} abaixo do limite")

    def apply(self, decision: Decision) -> None:
        if decision.action != "block":
            return
        if len(self.blocked) >= self.settings.max_active_blocks:
            decision.action = "none"
            decision.reason = "limite de bloqueios ativos atingido"
            self.database.audit("block", decision.source_ip, "skipped", decision.reason)
            return

        if self.settings.mode in {"observe", "dry_run"}:
            decision.applied = False
            decision.detail = f"modo {self.settings.mode}: bloqueio não aplicado"
            self.database.audit("block", decision.source_ip, "simulated", decision.reason)
            LOGGER.info(
                "DECISÃO %s: %s (%s) [%s]",
                decision.source_ip,
                decision.action,
                decision.reason,
                decision.detail,
            )
            return

        ok, detail = self.firewall.block(decision.source_ip, self.settings.block_seconds)
        decision.applied = ok
        decision.detail = detail
        decision.adapter = self.firewall.adapter
        if ok:
            expires_at = utc_now() + timedelta(seconds=self.settings.block_seconds)
            self.blocked[decision.source_ip] = expires_at
            self.database.save_block(
                decision.source_ip, expires_at, decision.reason, self.firewall.adapter
            )
            self.database.audit(
                "block", decision.source_ip, "ok", f"{decision.reason}; {detail}"
            )
            LOGGER.warning(
                "BLOQUEADO %s por %ss: %s (%s)",
                decision.source_ip,
                self.settings.block_seconds,
                decision.reason,
                detail,
            )
        else:
            self.database.audit("block", decision.source_ip, "failed", detail)
            LOGGER.error("FALHA ao bloquear %s: %s", decision.source_ip, detail)

    def handle_event(self, event: Event) -> None:
        decision = self.decide(event.source_ip, event)
        label = decision.action if decision.action != "block" else "block"
        self.database.save_event(event, label)
        LOGGER.info(
            "evento %s ip=%s honeypot=%s tipo=%s %s",
            event.event_id,
            event.source_ip,
            event.honeypot,
            event.event_type,
            event.path,
        )
        self.apply(decision)

    def _read_new(self, path: Path, offset: int) -> tuple[list[str], int]:
        if not path.exists():
            return [], offset
        size = path.stat().st_size
        if size < offset:
            offset = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(offset)
            lines = handle.readlines()
            return [line for line in lines if line.strip()], handle.tell()

    def run(self) -> None:
        self.configure_logging()
        LOGGER.info(
            "iniciando agente modo=%s firewall=%s banco=%s",
            self.settings.mode,
            self.firewall.adapter,
            self.settings.database,
        )
        self.database.audit("start", "agent", "ok", f"modo={self.settings.mode}")
        self.reconcile()
        if self.settings.access_log.exists():
            self._access_offset = self.settings.access_log.stat().st_size
        else:
            self._access_offset = 0
        if self.settings.spool.exists():
            self._spool_offset = self.settings.spool.stat().st_size
        else:
            self._spool_offset = 0

        while self.running:
            access_lines, self._access_offset = self._read_new(
                self.settings.access_log, self._access_offset
            )
            for line in access_lines:
                for event in classify_access(line):
                    self.handle_event(event)

            spool_lines, self._spool_offset = self._read_new(
                self.settings.spool, self._spool_offset
            )
            for line in spool_lines:
                event = event_from_spool(line)
                if event is not None:
                    self.handle_event(event)

            self.expire_blocks()
            time.sleep(0.5)

    def stop(self, _signum: int | None = None, _frame: Any = None) -> None:
        self.running = False

    def block_now(self, source_ip: str, ttl: int, reason: str) -> Decision:
        allowed, why = blockable(source_ip)
        if not allowed:
            return Decision(source_ip, "none", f"origem não bloqueável: {why}")
        decision = Decision(source_ip, "block", reason, ttl=ttl)
        ok, detail = self.firewall.block(source_ip, ttl)
        decision.applied = ok
        decision.detail = detail
        decision.adapter = self.firewall.adapter
        if ok:
            expires_at = utc_now() + timedelta(seconds=ttl)
            self.blocked[source_ip] = expires_at
            self.database.save_block(source_ip, expires_at, reason, self.firewall.adapter)
            self.database.audit("block", source_ip, "ok", f"manual: {reason}; {detail}")
        else:
            self.database.audit("block", source_ip, "failed", detail)
        return decision


def load_settings(args: argparse.Namespace) -> Settings:
    settings = Settings.load(Path(args.config))
    mode = getattr(args, "mode", None)
    if mode:
        settings.mode = mode
    block_seconds = getattr(args, "block_seconds", None)
    if block_seconds is not None:
        settings.block_seconds = block_seconds
    threshold = getattr(args, "threshold", None)
    if threshold is not None:
        settings.threshold = threshold
    window_seconds = getattr(args, "window_seconds", None)
    if window_seconds is not None:
        settings.window_seconds = window_seconds
    settings.validate()
    return settings


def print_status(settings: Settings) -> int:
    database = Database(settings.database)
    stats = database.status()
    print("SentinelIoT - laboratório")
    print(f"modo: {settings.mode}")
    print(f"firewall: {Firewall().adapter}")
    print(f"eventos: {stats['events']}")
    print("por tipo:", json.dumps(stats["by_type"], ensure_ascii=False))
    print("por honeypot:", json.dumps(stats["by_honeypot"], ensure_ascii=False))
    print(f"bloqueios ativos: {len(stats['blocks'])}")
    for block in stats["blocks"]:
        print(
            f"  - {block['source_ip']} até {block['expires_at']} "
            f"({block['adapter']}) {block['reason']}"
        )
    print("últimos eventos:")
    for event in database.last_events(12):
        print(
            f"  {event['timestamp_utc']} {event['source_ip']:15} "
            f"{event['honeypot']:14} {event['event_type']:18} "
            f"{event['method']:6} {event['path']}"
        )
    database.close()
    return 0


def run_selftest() -> int:
    cases = [
        (
            "10.10.10.20|2026-11-09T17:00:00+0000|GET|/admin/||200|sqlmap/1.8",
            "attack_tool",
        ),
        (
            "10.10.10.20|2026-11-09T17:00:00+0000|GET|/camera/|?id=1%27+OR+1=1|200|curl/8.5",
            "injection_attempt",
        ),
        (
            "10.10.10.20|2026-11-09T17:00:00+0000|GET|/api/||401|Mozilla/5.0",
            "auth_failure",
        ),
    ]
    for line, expected in cases:
        events = classify_access(line)
        types = {event.event_type for event in events}
        if expected not in types:
            print(f"FALHA: esperado {expected}, obtido {sorted(types)}")
            return 1

    if blockable("192.168.57.1")[0]:
        print("FALHA: rede de gerenciamento deveria ser protegida")
        return 1
    if blockable("192.168.1.9")[0]:
        print("FALHA: rede real deveria ser recusada")
        return 1
    if not blockable("10.10.10.20")[0]:
        print("FALHA: atacante do laboratório deveria ser bloqueável")
        return 1

    print("SELFTEST OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SentinelIoT - agente de laboratório")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="executa o agente")
    run.add_argument("--mode", choices=["observe", "dry_run", "enforce"])
    run.add_argument("--block-seconds", type=int)
    run.add_argument("--threshold", type=int)
    run.add_argument("--window-seconds", type=int)

    status = sub.add_parser("status", help="mostra eventos e bloqueios")
    status.add_argument("--mode", default=None)

    block = sub.add_parser("block", help="bloqueia um IP manualmente")
    block.add_argument("ip")
    block.add_argument("--ttl", type=int, default=300)
    block.add_argument("--reason", default="bloqueio manual")

    unblock = sub.add_parser("unblock", help="remove o bloqueio de um IP")
    unblock.add_argument("ip")

    sub.add_parser("selftest", help="valida classificadores e faixas permitidas")
    sub.add_parser("simulate", help="gera eventos de exemplo no spool")

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    settings = load_settings(args)

    if args.command == "status":
        return print_status(settings)

    if args.command == "selftest":
        return run_selftest()

    if args.command == "simulate":
        settings.spool.parent.mkdir(parents=True, exist_ok=True)
        now = utc_now()
        samples = []
        for index in range(3):
            samples.append(
                {
                    "timestamp_utc": iso(now + timedelta(seconds=index)),
                    "source_ip": "10.10.10.20",
                    "honeypot": "admin-portal",
                    "event_type": "credential_attempt",
                    "method": "POST",
                    "path": "/cgi-bin/sentinel_login.py",
                    "status": 401,
                    "user_agent": "hydra/9.5",
                    "detail": "tentativa de login (metadados)",
                }
            )
        with settings.spool.open("a", encoding="utf-8") as handle:
            for sample in samples:
                handle.write(json.dumps(sample) + "\n")
        print(f"{len(samples)} eventos simulados em {settings.spool}")
        return 0

    agent = Agent(settings)

    if args.command == "block":
        decision = agent.block_now(args.ip, args.ttl, args.reason)
        print(json.dumps(decision.__dict__, ensure_ascii=False, indent=2))
        return 0 if decision.applied else 1

    if args.command == "unblock":
        agent._release(args.ip, "desbloqueio manual")
        print(f"desbloqueado {args.ip}")
        return 0

    if args.command == "run":
        try:
            agent.run()
        except KeyboardInterrupt:
            agent.stop()
        finally:
            agent.database.close()
        return 0

    agent.database.close()
    return 1


if __name__ == "__main__":
    sys.exit(main())
