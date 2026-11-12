"""Testes de despacho dos comandos da CLI sem subprocesso."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sentineliot.cli.commands import dispatch
from sentineliot.cli.context import CommandContext, create_context
from sentineliot.cli.main import main
from sentineliot.cli.parser import build_parser
from sentineliot.events.models import Event
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.honeypot.state import load_instances
from sentineliot.storage.database import Database, SuspectRepository


def _event(event_id: str, **overrides: object) -> Event:
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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[CommandContext]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENTINELIOT_CONFIG", raising=False)
    yield create_context(data_dir=tmp_path / "data")


def _run(context: CommandContext, *argv: str) -> int:
    args = build_parser().parse_args(list(argv))
    return dispatch(args, context)


def test_simulate_scan_and_ban_decision(
    context: CommandContext, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(context, "simulate", "--ip", "10.10.10.66") == 0

    database = Database(context.paths.database)
    try:
        suspects = SuspectRepository(database)
        suspect = suspects.get("10.10.10.66")
        assert suspect is not None
        assert suspect.status == "pending"
        assert suspect.hits == 4
    finally:
        database.close()

    assert _run(context, "bans", "block", "10.10.10.66", "--note", "teste") == 0

    database = Database(context.paths.database)
    try:
        suspect = SuspectRepository(database).get("10.10.10.66")
        assert suspect is not None
        assert suspect.status == "blocked"
        assert suspect.decision_note == "teste"
    finally:
        database.close()

    assert _run(context, "bans", "reset", "10.10.10.66") == 0
    assert _run(context, "scan") == 0

    output = capsys.readouterr().out
    assert "Lista de ban" in output or "Varredura" in output


def test_scan_collects_new_spool_events(
    context: CommandContext, capsys: pytest.CaptureFixture[str]
) -> None:
    writer = SpoolWriter(context.paths.spool_file)
    writer.write(
        _event(
            "scan-1",
            source_ip="192.168.57.66",
            event_type="credential_attempt",
            honeypot_id="ssh-01",
            profile="ssh-banner",
            protocol="ssh",
        )
    )

    assert _run(context, "scan") == 0

    database = Database(context.paths.database)
    try:
        suspect = SuspectRepository(database).get("192.168.57.66")
        assert suspect is not None
        assert suspect.max_severity == "high"
    finally:
        database.close()

    output = capsys.readouterr().out
    assert "eventos novos" in output


def test_honeypots_add_and_remove(context: CommandContext) -> None:
    port = _free_port()

    assert (
        _run(
            context,
            "honeypots",
            "add",
            "router-admin",
            "--id",
            "router-test",
            "--port",
            str(port),
        )
        == 0
    )
    instances = load_instances(context.paths.honeypots_state, context.config)
    assert any(item.id == "router-test" for item in instances)

    assert _run(context, "honeypots", "remove", "router-test") == 0
    instances = load_instances(context.paths.honeypots_state, context.config)
    assert all(item.id != "router-test" for item in instances)


def test_bans_export_csv_has_no_blank_lines(
    context: CommandContext, tmp_path: Path
) -> None:
    assert _run(context, "simulate", "--ip", "10.0.0.9") == 0
    output = tmp_path / "bans.csv"

    assert _run(context, "bans", "export", "--format", "csv", "--output", str(output)) == 0

    content = output.read_text(encoding="utf-8")
    assert content.startswith("source_ip,hits,max_severity,status")
    assert "10.0.0.9" in content
    assert "\r\r\n" not in content
    assert content.count("\n") == 2


def test_events_show_accepts_prefix(
    context: CommandContext, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(context, "simulate") == 0

    database = Database(context.paths.database)
    try:
        event_id = database.connection.execute(
            "SELECT event_id FROM events ORDER BY id LIMIT 1"
        ).fetchone()["event_id"]
    finally:
        database.close()

    assert _run(context, "events", "show", str(event_id)[:8]) == 0
    output = capsys.readouterr().out
    assert "Evento" in output
    assert "Nenhum corpo" in output


def test_diagnostics_and_version(
    context: CommandContext, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(context, "diagnostics") == 0
    assert _run(context, "version") == 0

    output = capsys.readouterr().out
    assert "Diagnostico" in output
    assert "SentinelIoT 0.1.0" in output
    assert "s0ra" in output


def test_main_keeps_config_path_with_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("SENTINELIOT_CONFIG", raising=False)
    config = tmp_path / "nested" / "lab.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("agent:\n  mode: observe\n", encoding="utf-8")

    assert main(["--config", str(config), "--data-dir", str(tmp_path / "d"), "status"]) == 0

    output = capsys.readouterr().out
    assert str(config) in output
