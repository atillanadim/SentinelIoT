"""Testes do coletor incremental do spool JSONL."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sentineliot.events.collector import EventCollector
from sentineliot.events.models import Event
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.storage.database import Database, EventRepository, SuspectRepository


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    instance = Database(tmp_path / "test.db")
    try:
        yield instance
    finally:
        instance.close()


def _event(event_id: str = "event-1", **overrides: object) -> Event:
    values: dict[str, object] = {
        "source_ip": "10.0.0.5",
        "honeypot_id": "camera-01",
        "profile": "camera-http",
        "protocol": "http",
        "event_type": "honeypot_probe",
        "timestamp_utc": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        "event_id": event_id,
        "method": "GET",
        "path": "/admin/",
    }
    values.update(overrides)
    return Event(**values)  # type: ignore[arg-type]


def test_collect_is_incremental(database: Database, tmp_path: Path) -> None:
    spool = tmp_path / "spool" / "honeypot.jsonl"
    writer = SpoolWriter(spool)
    writer.write(_event("one"))
    writer.write(_event("two", source_ip="10.0.0.6"))
    collector = EventCollector(database, spool)

    first = collector.collect()

    assert first.read_lines == 2
    assert first.saved_events == 2
    assert first.new_ips == 2
    assert first.malformed_lines == 0
    assert EventRepository(database).count() == 2
    assert int(database.get_setting("spool_offset")) == spool.stat().st_size

    second = collector.collect()
    assert second.read_lines == 0
    assert second.saved_events == 0


def test_partial_line_waits_for_newline(database: Database, tmp_path: Path) -> None:
    spool = tmp_path / "honeypot.jsonl"
    spool.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_event("partial").to_record(), ensure_ascii=False).encode("utf-8")
    spool.write_bytes(payload)
    collector = EventCollector(database, spool)

    result = collector.collect()

    assert result.saved_events == 0
    assert database.get_setting("spool_offset", "0") == "0"

    with spool.open("ab") as handle:
        handle.write(b"\n")
    result = collector.collect()

    assert result.saved_events == 1
    assert int(database.get_setting("spool_offset")) == spool.stat().st_size


def test_offset_is_exact_with_multibyte_text(database: Database, tmp_path: Path) -> None:
    spool = tmp_path / "honeypot.jsonl"
    writer = SpoolWriter(spool)
    writer.write(_event("one", detail="tentativa de login (credenciais nao armazenadas)"))
    writer.write(_event("two", detail="ação suspeita — UTF-8 ✓"))
    collector = EventCollector(database, spool)

    assert collector.collect().saved_events == 2
    assert int(database.get_setting("spool_offset")) == spool.stat().st_size

    assert collector.collect().saved_events == 0


def test_malformed_and_duplicate_lines(database: Database, tmp_path: Path) -> None:
    spool = tmp_path / "honeypot.jsonl"
    spool.parent.mkdir(parents=True, exist_ok=True)
    valid = json.dumps(_event("same").to_record(), ensure_ascii=False) + "\n"
    spool.write_text("not-json\n" + valid + valid, encoding="utf-8")
    collector = EventCollector(database, spool)

    result = collector.collect()

    assert result.malformed_lines == 1
    assert result.saved_events == 1
    assert result.duplicate_events == 1
    assert EventRepository(database).count() == 1
    assert SuspectRepository(database).get("10.0.0.5") is not None


def test_allowlisted_source_starts_as_allowlisted(
    database: Database, tmp_path: Path
) -> None:
    spool = tmp_path / "honeypot.jsonl"
    writer = SpoolWriter(spool)
    writer.write(_event("loopback", source_ip="127.0.0.1", event_type="connection"))
    collector = EventCollector(database, spool, allowlist=("127.0.0.0/8",))

    assert collector.collect().saved_events == 1

    suspect = SuspectRepository(database).get("127.0.0.1")
    assert suspect is not None
    assert suspect.status == "allowlisted"


def test_reset_offset_reprocesses_but_deduplicates(database: Database, tmp_path: Path) -> None:
    spool = tmp_path / "honeypot.jsonl"
    writer = SpoolWriter(spool)
    writer.write(_event("one"))
    collector = EventCollector(database, spool)
    assert collector.collect().saved_events == 1

    collector.reset_offset()
    result = collector.collect()

    assert result.duplicate_events == 1
    assert result.saved_events == 0
    assert EventRepository(database).count() == 1
