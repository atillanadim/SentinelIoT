"""SQLite local, schema e repositorios de eventos e IPs observados."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sentineliot.core.errors import StorageError
from sentineliot.events.models import Event, iso_utc, utc_now
from sentineliot.security.validation import parse_ip

SUSPECT_STATUSES = ("pending", "blocked", "allowed", "ignored", "allowlisted")

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    timestamp_utc TEXT NOT NULL,
    source_ip TEXT NOT NULL,
    source_port INTEGER,
    honeypot_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    protocol TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    score INTEGER NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status INTEGER NOT NULL,
    user_agent TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_timestamp_idx ON events(timestamp_utc);
CREATE INDEX IF NOT EXISTS events_source_idx ON events(source_ip);
CREATE INDEX IF NOT EXISTS events_type_idx ON events(event_type);

CREATE TABLE IF NOT EXISTS suspects (
    source_ip TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    hits INTEGER NOT NULL DEFAULT 1,
    max_severity TEXT NOT NULL,
    severity_rank INTEGER NOT NULL,
    status TEXT NOT NULL,
    decision_at TEXT,
    decision_note TEXT,
    last_event_id TEXT NOT NULL,
    last_path TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS suspects_status_idx ON suspects(status);
CREATE INDEX IF NOT EXISTS suspects_last_seen_idx ON suspects(last_seen);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    result TEXT NOT NULL,
    detail TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Database:
    """Conexao unica por processo, com WAL e schema idempotente."""

    def __init__(self, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.path = path
            self.connection = sqlite3.connect(str(path), timeout=10)
        except (OSError, sqlite3.Error) as exc:
            raise StorageError(f"nao foi possivel abrir o banco {path}: {exc}") from exc
        self.connection.row_factory = sqlite3.Row
        try:
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA foreign_keys=ON")
            self.connection.execute("PRAGMA busy_timeout=5000")
            self.connection.executescript(SCHEMA)
            self.connection.execute("PRAGMA user_version=1")
            self.connection.commit()
        except sqlite3.Error as exc:
            self.connection.close()
            raise StorageError(f"falha ao inicializar o banco {path}: {exc}") from exc

    def close(self) -> None:
        self.connection.close()

    def audit(self, actor: str, action: str, target: str, result: str, detail: str = "") -> None:
        self.connection.execute(
            """
            INSERT INTO audit_log (timestamp_utc, actor, action, target, result, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (iso_utc(utc_now()), actor, action, target, result, detail[:500]),
        )
        self.connection.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        self.connection.execute(
            """
            INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, value, iso_utc(utc_now())),
        )
        self.connection.commit()


@dataclass(frozen=True)
class StoredEvent:
    event_id: str
    timestamp_utc: str
    source_ip: str
    source_port: int | None
    honeypot_id: str
    profile: str
    protocol: str
    event_type: str
    severity: str
    score: int
    method: str
    path: str
    status: int
    user_agent: str
    detail: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> StoredEvent:
        return cls(
            event_id=str(row["event_id"]),
            timestamp_utc=str(row["timestamp_utc"]),
            source_ip=str(row["source_ip"]),
            source_port=int(row["source_port"]) if row["source_port"] is not None else None,
            honeypot_id=str(row["honeypot_id"]),
            profile=str(row["profile"]),
            protocol=str(row["protocol"]),
            event_type=str(row["event_type"]),
            severity=str(row["severity"]),
            score=int(row["score"]),
            method=str(row["method"]),
            path=str(row["path"]),
            status=int(row["status"]),
            user_agent=str(row["user_agent"]),
            detail=str(row["detail"]),
        )


@dataclass(frozen=True)
class Suspect:
    source_ip: str
    first_seen: str
    last_seen: str
    hits: int
    max_severity: str
    severity_rank: int
    status: str
    decision_at: str | None
    decision_note: str | None
    last_event_id: str
    last_path: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Suspect:
        return cls(
            source_ip=str(row["source_ip"]),
            first_seen=str(row["first_seen"]),
            last_seen=str(row["last_seen"]),
            hits=int(row["hits"]),
            max_severity=str(row["max_severity"]),
            severity_rank=int(row["severity_rank"]),
            status=str(row["status"]),
            decision_at=str(row["decision_at"]) if row["decision_at"] else None,
            decision_note=str(row["decision_note"]) if row["decision_note"] else None,
            last_event_id=str(row["last_event_id"]),
            last_path=str(row["last_path"]),
        )


class EventRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(self, event: Event) -> bool:
        """Persiste um evento; retorna False quando o event_id ja existe."""
        cursor = self.database.connection.execute(
            """
            INSERT OR IGNORE INTO events (
                event_id, timestamp_utc, source_ip, source_port, honeypot_id,
                profile, protocol, event_type, severity, score, method, path,
                status, user_agent, detail, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                iso_utc(event.timestamp_utc),
                event.source_ip,
                event.source_port,
                event.honeypot_id,
                event.profile,
                event.protocol,
                event.event_type,
                event.severity,
                event.score,
                event.method,
                event.path,
                event.status,
                event.user_agent,
                event.detail,
                iso_utc(utc_now()),
            ),
        )
        self.database.connection.commit()
        return cursor.rowcount > 0

    def list_events(
        self,
        *,
        limit: int = 20,
        source_ip: str | None = None,
        event_type: str | None = None,
        severity: str | None = None,
    ) -> list[StoredEvent]:
        clauses: list[str] = []
        params: list[object] = []
        if source_ip:
            clauses.append("source_ip = ?")
            params.append(source_ip)
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if severity:
            clauses.append("severity = ?")
            params.append(severity)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(limit, 1000)))
        rows = self.database.connection.execute(
            f"SELECT * FROM events {where} ORDER BY id DESC LIMIT ?", params
        ).fetchall()
        return [StoredEvent.from_row(row) for row in rows]

    def get(self, event_id: str) -> StoredEvent | None:
        row = self.database.connection.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return StoredEvent.from_row(row) if row is not None else None

    def find_by_prefix(self, prefix: str) -> list[StoredEvent]:
        rows = self.database.connection.execute(
            "SELECT * FROM events WHERE event_id LIKE ? ORDER BY id DESC LIMIT 2",
            (f"{prefix}%",),
        ).fetchall()
        return [StoredEvent.from_row(row) for row in rows]

    def last_event(self) -> StoredEvent | None:
        rows = self.list_events(limit=1)
        return rows[0] if rows else None

    def count(self) -> int:
        row = self.database.connection.execute("SELECT COUNT(*) AS total FROM events").fetchone()
        return int(row["total"]) if row is not None else 0

    def count_since(self, moment: datetime) -> int:
        row = self.database.connection.execute(
            "SELECT COUNT(*) AS total FROM events WHERE timestamp_utc >= ?",
            (iso_utc(moment),),
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    def events_for_ip(self, source_ip: str, limit: int = 20) -> list[StoredEvent]:
        return self.list_events(limit=limit, source_ip=source_ip)

    def severity_counts(self) -> dict[str, int]:
        rows = self.database.connection.execute(
            "SELECT severity, COUNT(*) AS total FROM events GROUP BY severity"
        ).fetchall()
        return {str(row["severity"]): int(row["total"]) for row in rows}

    def type_counts(self, limit: int = 8) -> dict[str, int]:
        rows = self.database.connection.execute(
            """
            SELECT event_type, COUNT(*) AS total FROM events
            GROUP BY event_type ORDER BY total DESC, event_type ASC LIMIT ?
            """,
            (max(1, min(limit, 50)),),
        ).fetchall()
        return {str(row["event_type"]): int(row["total"]) for row in rows}

    def hourly_counts(self, since: datetime) -> dict[str, int]:
        """Contagem por hora UTC no formato usado pelo dashboard."""
        rows = self.database.connection.execute(
            """
            SELECT substr(timestamp_utc, 1, 13) AS hour, COUNT(*) AS total
            FROM events WHERE timestamp_utc >= ?
            GROUP BY hour ORDER BY hour
            """,
            (iso_utc(since),),
        ).fetchall()
        return {str(row["hour"]): int(row["total"]) for row in rows}

    def prune(self, retention_days: int) -> int:
        cutoff = iso_utc(utc_now() - timedelta(days=retention_days))
        cursor = self.database.connection.execute(
            "DELETE FROM events WHERE timestamp_utc < ?", (cutoff,)
        )
        self.database.connection.commit()
        return cursor.rowcount


class SuspectRepository:
    """Lista de IPs observados e decisao do administrador sobre cada um."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def observe(self, event: Event, *, allowlisted: bool) -> None:
        initial_status = "allowlisted" if allowlisted else "pending"
        self.database.connection.execute(
            """
            INSERT INTO suspects (
                source_ip, first_seen, last_seen, hits, max_severity,
                severity_rank, status, last_event_id, last_path
            ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(source_ip) DO UPDATE SET
                last_seen=excluded.last_seen,
                hits=suspects.hits + 1,
                max_severity=CASE
                    WHEN excluded.severity_rank > suspects.severity_rank
                    THEN excluded.max_severity ELSE suspects.max_severity END,
                severity_rank=MAX(suspects.severity_rank, excluded.severity_rank),
                last_event_id=excluded.last_event_id,
                last_path=excluded.last_path
            """,
            (
                event.source_ip,
                iso_utc(event.timestamp_utc),
                iso_utc(event.timestamp_utc),
                event.severity,
                event.score,
                initial_status,
                event.event_id,
                event.path,
            ),
        )
        self.database.connection.commit()

    def list(self, *, status: str | None = None, limit: int = 100) -> list[Suspect]:
        params: list[object] = []
        where = ""
        if status:
            where = "WHERE status = ?"
            params.append(status)
        params.append(max(1, min(limit, 1000)))
        rows = self.database.connection.execute(
            f"""
            SELECT * FROM suspects {where}
            ORDER BY severity_rank DESC, last_seen DESC LIMIT ?
            """,
            params,
        ).fetchall()
        return [Suspect.from_row(row) for row in rows]

    def get(self, source_ip: str) -> Suspect | None:
        if parse_ip(source_ip) is None:
            return None
        row = self.database.connection.execute(
            "SELECT * FROM suspects WHERE source_ip = ?", (source_ip,)
        ).fetchone()
        return Suspect.from_row(row) if row is not None else None

    def decide(self, source_ip: str, status: str, note: str, actor: str = "cli") -> Suspect:
        if status not in SUSPECT_STATUSES:
            raise StorageError(f"status invalido: {status}")
        suspect = self.get(source_ip)
        if suspect is None:
            raise StorageError(f"IP sem interacoes registradas: {source_ip}")
        self.database.connection.execute(
            """
            UPDATE suspects SET status = ?, decision_at = ?, decision_note = ?
            WHERE source_ip = ?
            """,
            (status, iso_utc(utc_now()), note[:300], source_ip),
        )
        self.database.connection.commit()
        self.database.audit(
            actor,
            f"decision_{status}",
            source_ip,
            "ok",
            note or f"decisao manual: {status}",
        )
        updated = self.get(source_ip)
        if updated is None:
            raise StorageError(f"falha ao atualizar o IP {source_ip}")
        return updated

    def stats(self) -> dict[str, int]:
        rows = self.database.connection.execute(
            "SELECT status, COUNT(*) AS total FROM suspects GROUP BY status"
        ).fetchall()
        return {str(row["status"]): int(row["total"]) for row in rows}

    def total(self) -> int:
        row = self.database.connection.execute("SELECT COUNT(*) AS total FROM suspects").fetchone()
        return int(row["total"]) if row is not None else 0

    def pending_count(self) -> int:
        row = self.database.connection.execute(
            "SELECT COUNT(*) AS total FROM suspects WHERE status = 'pending'"
        ).fetchone()
        return int(row["total"]) if row is not None else 0
