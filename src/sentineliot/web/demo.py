"""Dados de demonstracao para o dashboard local.

O seed so grava quando o banco ainda nao tem eventos. Ele usa o mesmo spool
JSONL e o mesmo coletor do agente, portanto nao cria um caminho paralelo de
persistencia. Nenhuma isca real e contatada.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sentineliot.core.config import Config
from sentineliot.core.paths import RuntimePaths
from sentineliot.events.collector import EventCollector
from sentineliot.events.models import Event, utc_now
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.storage.database import Database, EventRepository, SuspectRepository


@dataclass(frozen=True)
class DemoEvent:
    minutes_ago: int
    source_ip: str
    source_port: int
    honeypot_id: str
    profile: str
    protocol: str
    event_type: str
    method: str
    path: str
    status: int
    user_agent: str
    detail: str


DEMO_EVENTS: tuple[DemoEvent, ...] = (
    DemoEvent(
        88,
        "10.10.10.20",
        51_204,
        "camera-01",
        "camera-http",
        "http",
        "attack_tool",
        "GET",
        "/admin/",
        200,
        "sqlmap/1.8.7#stable",
        "User-Agent de ferramenta automatizada",
    ),
    DemoEvent(
        84,
        "10.10.10.20",
        51_205,
        "camera-01",
        "camera-http",
        "http",
        "honeypot_probe",
        "GET",
        "/.env",
        404,
        "sqlmap/1.8.7#stable",
        "Sondagem de arquivo sensivel",
    ),
    DemoEvent(
        80,
        "10.10.10.20",
        51_206,
        "router-01",
        "router-admin",
        "http",
        "credential_attempt",
        "POST",
        "/cgi-bin/login",
        401,
        "python-requests/2.31",
        "Tentativa de login (credenciais nao armazenadas)",
    ),
    DemoEvent(
        63,
        "10.10.10.20",
        51_207,
        "router-01",
        "router-admin",
        "http",
        "injection_attempt",
        "GET",
        "/cgi-bin/diagnostic?cmd=id",
        403,
        "sqlmap/1.8.7#stable",
        "Padrao de injecao de comando detectado",
    ),
    DemoEvent(
        52,
        "192.168.57.66",
        60_118,
        "ssh-01",
        "ssh-banner",
        "ssh",
        "credential_attempt",
        "",
        "",
        0,
        "libssh2_1.11",
        "Tentativa de autenticacao SSH (sem senha armazenada)",
    ),
    DemoEvent(
        47,
        "192.168.57.66",
        60_119,
        "ssh-01",
        "ssh-banner",
        "ssh",
        "connection",
        "",
        "",
        0,
        "libssh2_1.11",
        "Handshake SSH aceito pela isca",
    ),
    DemoEvent(
        35,
        "10.10.10.55",
        47_310,
        "telnet-01",
        "telnet-iot",
        "telnet",
        "credential_attempt",
        "",
        "",
        0,
        "busybox telnet",
        "Login Telnet recebido; credenciais descartadas",
    ),
    DemoEvent(
        28,
        "172.16.0.14",
        39_002,
        "router-01",
        "router-admin",
        "http",
        "honeypot_probe",
        "GET",
        "/server-status",
        404,
        "Mozilla/5.0",
        "Sondagem de painel administrativo",
    ),
    DemoEvent(
        19,
        "203.0.113.20",
        58_800,
        "camera-01",
        "camera-http",
        "http",
        "attack_tool",
        "GET",
        "/camera/",
        200,
        "nikto/2.5.0",
        "Scanner web identificado no User-Agent",
    ),
    DemoEvent(
        12,
        "10.10.10.55",
        47_311,
        "telnet-01",
        "telnet-iot",
        "telnet",
        "probe",
        "",
        "",
        0,
        "busybox telnet",
        "Conexao Telnet para enumeracao",
    ),
    DemoEvent(
        6,
        "203.0.113.20",
        58_801,
        "router-01",
        "router-admin",
        "http",
        "config_attempt",
        "POST",
        "/setup.cgi",
        403,
        "nikto/2.5.0",
        "Tentativa de alteracao de configuracao",
    ),
    DemoEvent(
        2,
        "10.10.10.20",
        51_208,
        "camera-01",
        "camera-http",
        "http",
        "honeypot_probe",
        "GET",
        "/api/v1/",
        401,
        "sqlmap/1.8.7#stable",
        "Sondagem da API da camera",
    ),
)

DEMO_DECISIONS: dict[str, tuple[str, str]] = {
    "10.10.10.20": ("blocked", "demonstracao: scanner web no laboratorio"),
    "10.10.10.55": ("ignored", "demonstracao: dispositivo interno conhecido"),
    "192.168.57.66": ("allowed", "demonstracao: estacao de administracao"),
}


def seed_demo(config: Config, paths: RuntimePaths) -> int:
    """Popula o banco com um cenario de demonstracao; retorna eventos criados."""
    paths.ensure()
    database = Database(paths.database)
    try:
        repository = EventRepository(database)
        if repository.count() > 0:
            return 0

        writer = SpoolWriter(paths.spool_file)
        now = utc_now()
        for item in DEMO_EVENTS:
            writer.write(
                Event(
                    source_ip=item.source_ip,
                    source_port=item.source_port,
                    honeypot_id=item.honeypot_id,
                    profile=item.profile,
                    protocol=item.protocol,
                    event_type=item.event_type,
                    timestamp_utc=now - timedelta(minutes=item.minutes_ago),
                    event_id=uuid.uuid4().hex[:20],
                    method=item.method,
                    path=item.path,
                    status=item.status,
                    user_agent=item.user_agent,
                    detail=item.detail,
                )
            )

        collected = EventCollector(database, paths.spool_file, config.allowlist).collect()
        suspects = SuspectRepository(database)
        for source_ip, (status, note) in DEMO_DECISIONS.items():
            if suspects.get(source_ip) is not None:
                suspects.decide(source_ip, status, note, actor="demo")
        return collected.saved_events
    finally:
        database.close()
