"""Leitura dos dados do agente para o dashboard local.

O dashboard e somente leitura: este modulo nao altera eventos, decisoes,
configuracao ou firewall. Cada consulta abre uma conexao curta com o SQLite,
o que evita disputa de thread e mantem o agente como unico escritor.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sentineliot import __author__, __version__
from sentineliot.core.config import Config
from sentineliot.core.errors import HoneypotError, StorageError
from sentineliot.core.paths import RuntimePaths
from sentineliot.core.runtime import active_snapshot
from sentineliot.events.models import iso_utc, utc_now
from sentineliot.honeypot.profiles import get_profile
from sentineliot.honeypot.state import HoneypotInstance, load_instances
from sentineliot.storage.database import Database, EventRepository, SuspectRepository

TIMELINE_HOURS = 24
MAX_EVENT_LIMIT = 500
MAX_SUSPECT_LIMIT = 500


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _path_info(path: Path) -> dict[str, object]:
    try:
        size = path.stat().st_size
        exists = True
    except OSError:
        size = 0
        exists = False
    return {"path": str(path), "exists": exists, "size_bytes": size}


def _timeline(raw: dict[str, int], now: datetime) -> list[dict[str, object]]:
    current = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    series: list[dict[str, object]] = []
    for offset in range(TIMELINE_HOURS - 1, -1, -1):
        hour = current - timedelta(hours=offset)
        series.append(
            {
                "hour_utc": iso_utc(hour),
                "count": raw.get(iso_utc(hour)[:13], 0),
            }
        )
    return series


class WebDataService:
    """Monta os payloads JSON consumidos pelo dashboard."""

    def __init__(self, config: Config, paths: RuntimePaths) -> None:
        self.config = config
        self.paths = paths

    @contextmanager
    def _database(self) -> Iterator[Database]:
        self.paths.ensure()
        database = Database(self.paths.database)
        try:
            yield database
        finally:
            database.close()

    def summary(self) -> dict[str, object]:
        now = utc_now()
        with self._database() as database:
            events = EventRepository(database)
            suspects = SuspectRepository(database)
            events_total = events.count()
            events_24h = events.count_since(now - timedelta(hours=24))
            last_event = events.last_event()
            severity_counts = events.severity_counts()
            type_counts = events.type_counts(limit=8)
            hourly = events.hourly_counts(now - timedelta(hours=TIMELINE_HOURS - 1))
            suspect_stats = suspects.stats()
            pending = suspects.pending_count()
            suspects_total = suspects.total()
            recent_events = events.list_events(limit=40)
            top_suspects = suspects.list(limit=40)

        snapshot = active_snapshot(self.paths.runtime_state)
        running_ids = {item.id for item in snapshot.instances} if snapshot else set()
        instances = self._instances()
        honeypots = [
            {
                "id": instance.id,
                "profile": instance.profile,
                "protocol": _protocol(instance),
                "host": instance.host,
                "port": instance.port,
                "endpoint": instance.endpoint,
                "running": instance.id in running_ids,
            }
            for instance in instances
        ]

        return {
            "generated_at": iso_utc(now),
            "app": {
                "name": "SentinelIoT",
                "version": __version__,
                "author": __author__,
                "environment": self.config.app.environment,
                "mode": self.config.mode,
                "runtime": self.config.honeypot.runtime,
            },
            "agent": {
                "running": snapshot is not None,
                "pid": snapshot.pid if snapshot is not None else None,
                "started_at": snapshot.started_at if snapshot is not None else None,
                "mode": snapshot.mode if snapshot is not None else self.config.mode,
                "instances": len(snapshot.instances) if snapshot is not None else 0,
            },
            "database": _path_info(self.paths.database),
            "spool": _path_info(self.paths.spool_file),
            "stats": {
                "events_total": events_total,
                "events_24h": events_24h,
                "suspects_total": suspects_total,
                "pending": pending,
                "decisions": suspect_stats,
                "severity": severity_counts,
                "types": type_counts,
                "last_event": asdict(last_event) if last_event is not None else None,
            },
            "timeline": _timeline(hourly, now),
            "honeypots": honeypots,
            "events": [asdict(event) for event in recent_events],
            "suspects": [asdict(suspect) for suspect in top_suspects],
            "warnings": self._warnings(snapshot is not None),
        }

    def events(
        self,
        *,
        limit: int = 50,
        source_ip: str | None = None,
        event_type: str | None = None,
        severity: str | None = None,
    ) -> dict[str, object]:
        selected_limit = _clamp(limit, 1, MAX_EVENT_LIMIT)
        with self._database() as database:
            repository = EventRepository(database)
            items = repository.list_events(
                limit=selected_limit,
                source_ip=source_ip or None,
                event_type=event_type or None,
                severity=severity or None,
            )
            total = repository.count()
        return {
            "count": len(items),
            "total": total,
            "events": [asdict(event) for event in items],
        }

    def suspects(self, *, status: str | None = None, limit: int = 100) -> dict[str, object]:
        selected_limit = _clamp(limit, 1, MAX_SUSPECT_LIMIT)
        with self._database() as database:
            repository = SuspectRepository(database)
            items = repository.list(status=status or None, limit=selected_limit)
            stats = repository.stats()
            pending = repository.pending_count()
        return {
            "count": len(items),
            "pending": pending,
            "stats": stats,
            "suspects": [asdict(suspect) for suspect in items],
        }

    def event(self, event_id: str) -> dict[str, object] | None:
        cleaned = event_id.strip()
        if not cleaned:
            return None
        with self._database() as database:
            repository = EventRepository(database)
            found = repository.get(cleaned)
            if found is None:
                matches = repository.find_by_prefix(cleaned)
                found = matches[0] if len(matches) == 1 else None
        if found is None:
            return None
        return {"event": asdict(found)}

    def health(self) -> dict[str, object]:
        database_ok = False
        detail = "quick_check indisponivel"
        try:
            with self._database() as database:
                row = database.connection.execute("PRAGMA quick_check").fetchone()
                database_ok = row is not None and str(row[0]) == "ok"
                detail = str(row[0]) if row is not None else "sem resposta"
        except (StorageError, sqlite3.Error) as exc:
            detail = str(exc)
        return {
            "status": "ok" if database_ok else "degraded",
            "version": __version__,
            "time_utc": iso_utc(utc_now()),
            "database": {"ok": database_ok, "detail": detail},
        }

    def _instances(self) -> list[HoneypotInstance]:
        try:
            return load_instances(self.paths.honeypots_state, self.config)
        except HoneypotError:
            return []

    def _warnings(self, agent_running: bool) -> list[str]:
        warnings = [
            "Modo observacao: nenhuma regra de firewall e criada ou alterada.",
            "Decisoes de bloqueio sao apenas registradas nesta versao.",
        ]
        if not agent_running:
            warnings.append("O agente esta parado; os dados exibidos sao historicos.")
        if self.config.honeypot.runtime == "local":
            warnings.append(
                "Runtime local em processo: use containers para isolamento real das iscas."
            )
        return warnings


def _protocol(instance: HoneypotInstance) -> str:
    try:
        return get_profile(instance.profile).protocol
    except HoneypotError:
        return "?"
