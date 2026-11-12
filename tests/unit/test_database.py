"""Testes de persistencia, deduplicacao e decisoes da lista de ban."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentineliot.core.errors import StorageError
from sentineliot.events.models import Event
from sentineliot.storage.database import Database, EventRepository, SuspectRepository


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    instance = Database(tmp_path / "test.db")
    try:
        yield instance
    finally:
        instance.close()


def _event(
    *,
    event_id: str = "event-1",
    source_ip: str = "10.0.0.5",
    event_type: str = "honeypot_probe",
    timestamp: datetime | None = None,
    path: str = "/admin/",
) -> Event:
    return Event(
        source_ip=source_ip,
        honeypot_id="camera-01",
        profile="camera-http",
        protocol="http",
        event_type=event_type,
        timestamp_utc=timestamp or datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        event_id=event_id,
        method="GET",
        path=path,
    )


def test_event_save_is_idempotent(database: Database) -> None:
    repository = EventRepository(database)

    assert repository.save(_event()) is True
    assert repository.save(_event()) is False
    assert repository.count() == 1
    assert repository.get("event-1") is not None
    assert repository.find_by_prefix("event")[0].event_id == "event-1"


def test_observe_accumulates_hits_and_max_severity(database: Database) -> None:
    suspects = SuspectRepository(database)

    suspects.observe(_event(event_id="low", event_type="connection"), allowlisted=False)
    observed = suspects.get("10.0.0.5")
    assert observed is not None
    assert observed.hits == 1
    assert observed.max_severity == "low"
    assert observed.status == "pending"

    suspects.observe(_event(event_id="high", event_type="attack_tool"), allowlisted=False)
    suspects.observe(_event(event_id="again", event_type="request"), allowlisted=False)
    observed = suspects.get("10.0.0.5")
    assert observed is not None
    assert observed.hits == 3
    assert observed.max_severity == "high"
    assert observed.last_path == "/admin/"


def test_allowlisted_events_mark_suspect(database: Database) -> None:
    suspects = SuspectRepository(database)

    suspects.observe(_event(source_ip="127.0.0.1"), allowlisted=True)

    observed = suspects.get("127.0.0.1")
    assert observed is not None
    assert observed.status == "allowlisted"


def test_decision_updates_status_and_note(database: Database) -> None:
    suspects = SuspectRepository(database)
    suspects.observe(_event(), allowlisted=False)

    blocked = suspects.decide("10.0.0.5", "blocked", "teste manual")

    assert blocked.status == "blocked"
    assert blocked.decision_note == "teste manual"
    assert blocked.decision_at is not None
    assert suspects.stats() == {"blocked": 1}
    assert suspects.pending_count() == 0


def test_decision_requires_observed_ip(database: Database) -> None:
    with pytest.raises(StorageError, match="sem interacoes"):
        SuspectRepository(database).decide("10.9.9.9", "blocked", "")


def test_invalid_decision_status_raises(database: Database) -> None:
    suspects = SuspectRepository(database)
    suspects.observe(_event(), allowlisted=False)

    with pytest.raises(StorageError, match="status invalido"):
        suspects.decide("10.0.0.5", "destroyed", "")


def test_list_filters_by_status_and_orders_by_severity(database: Database) -> None:
    suspects = SuspectRepository(database)
    suspects.observe(_event(event_id="a", source_ip="10.0.0.1"), allowlisted=False)
    suspects.observe(
        _event(event_id="b", source_ip="10.0.0.2", event_type="attack_tool"),
        allowlisted=False,
    )
    suspects.decide("10.0.0.2", "blocked", "")

    all_suspects = suspects.list()
    blocked = suspects.list(status="blocked")

    assert [item.source_ip for item in all_suspects] == ["10.0.0.2", "10.0.0.1"]
    assert [item.source_ip for item in blocked] == ["10.0.0.2"]


def test_event_queries_and_prune(database: Database) -> None:
    events = EventRepository(database)
    old = datetime.now(UTC) - timedelta(days=10)
    events.save(_event(event_id="old", timestamp=old))
    events.save(
        _event(
            event_id="new",
            source_ip="10.0.0.6",
            event_type="attack_tool",
            timestamp=datetime.now(UTC),
        )
    )

    assert events.count() == 2
    assert [item.event_id for item in events.list_events(source_ip="10.0.0.6")] == ["new"]
    assert [item.event_id for item in events.list_events(event_type="honeypot_probe")] == [
        "old"
    ]
    assert events.events_for_ip("10.0.0.6")[0].event_id == "new"
    assert events.last_event() is not None

    assert events.prune(retention_days=1) == 1
    assert events.count() == 1
