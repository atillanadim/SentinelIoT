"""Testes do dashboard local: dados, rotas HTTP e protecoes."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from sentineliot.cli.commands import dispatch
from sentineliot.cli.context import CommandContext, create_context
from sentineliot.cli.parser import build_parser
from sentineliot.core.errors import SentinelError
from sentineliot.events.models import utc_now
from sentineliot.storage.database import Database, EventRepository
from sentineliot.web.demo import DEMO_EVENTS, seed_demo
from sentineliot.web.server import DashboardServer
from sentineliot.web.snapshot import WebDataService


@pytest.fixture
def context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[CommandContext]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENTINELIOT_CONFIG", raising=False)
    yield create_context(data_dir=tmp_path / "data")


def _run(context: CommandContext, *argv: str) -> int:
    args = build_parser().parse_args(list(argv))
    return dispatch(args, context)


@contextmanager
def _running(service: WebDataService) -> Iterator[str]:
    server = DashboardServer(service, port=0, refresh_seconds=1)
    httpd = server.build()
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _get_json(base_url: str, path: str) -> dict[str, Any]:
    with urllib.request.urlopen(base_url + path, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_demo_seed_and_summary(context: CommandContext) -> None:
    created = seed_demo(context.config, context.paths)
    assert created == len(DEMO_EVENTS)

    summary = WebDataService(context.config, context.paths).summary()

    stats = summary["stats"]
    assert isinstance(stats, dict)
    assert stats["events_total"] == len(DEMO_EVENTS)
    assert stats["events_24h"] == len(DEMO_EVENTS)
    assert stats["suspects_total"] == 5
    assert stats["pending"] == 2
    assert stats["decisions"] == {"allowed": 1, "blocked": 1, "ignored": 1, "pending": 2}
    assert stats["severity"]["high"] >= 4

    timeline = summary["timeline"]
    assert isinstance(timeline, list)
    assert len(timeline) == 24
    assert sum(int(item["count"]) for item in timeline) == len(DEMO_EVENTS)

    events = summary["events"]
    assert isinstance(events, list)
    assert len(events) == len(DEMO_EVENTS)
    assert {event["source_ip"] for event in events} == {
        "10.10.10.20",
        "192.168.57.66",
        "10.10.10.55",
        "172.16.0.14",
        "203.0.113.20",
    }

    honeypots = summary["honeypots"]
    assert isinstance(honeypots, list)
    assert honeypots
    assert all(honeypot["running"] is False for honeypot in honeypots)
    assert summary["agent"] == {
        "running": False,
        "pid": None,
        "started_at": None,
        "mode": "observe",
        "instances": 0,
    }
    warnings = summary["warnings"]
    assert isinstance(warnings, list)
    assert any("agente esta parado" in warning for warning in warnings)


def test_demo_seed_is_idempotent(context: CommandContext) -> None:
    assert seed_demo(context.config, context.paths) == len(DEMO_EVENTS)
    assert seed_demo(context.config, context.paths) == 0

    database = Database(context.paths.database)
    try:
        assert EventRepository(database).count() == len(DEMO_EVENTS)
    finally:
        database.close()


def test_server_serves_read_only_dashboard(context: CommandContext) -> None:
    seed_demo(context.config, context.paths)
    service = WebDataService(context.config, context.paths)

    with _running(service) as base_url:
        with urllib.request.urlopen(base_url + "/", timeout=5) as response:
            assert response.status == 200
            assert response.headers["Content-Type"].startswith("text/html")
            body = response.read().decode("utf-8")
        assert "SentinelIoT" in body
        assert "Fluxo de eventos" in body
        assert "__REFRESH_MS__" not in body
        assert "REFRESH_MS = 1000" in body

        summary = _get_json(base_url, "/api/summary")
        assert summary["app"]["version"] == "0.1.0"
        assert summary["stats"]["events_total"] == len(DEMO_EVENTS)

        events = _get_json(base_url, "/api/events?limit=2")
        assert events["count"] == 2
        assert len(events["events"]) == 2

        high = _get_json(base_url, "/api/events?severity=high")
        assert high["count"] >= 1
        assert all(event["severity"] == "high" for event in high["events"])

        event_id = str(events["events"][0]["event_id"])
        detail = _get_json(base_url, f"/api/events/{event_id}")
        assert detail["event"]["event_id"] == event_id

        blocked = _get_json(base_url, "/api/suspects?status=blocked")
        assert blocked["count"] == 1
        assert blocked["suspects"][0]["source_ip"] == "10.10.10.20"

        health = _get_json(base_url, "/healthz")
        assert health["status"] == "ok"
        assert health["database"]["ok"] is True

        with urllib.request.urlopen(base_url + "/api/events?limit=1", timeout=5) as response:
            assert response.status == 200
            assert response.headers["Cache-Control"].startswith("no-store")
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
            assert response.read()

        with urllib.request.urlopen(
            urllib.request.Request(base_url + "/api/summary", method="HEAD"), timeout=5
        ) as response:
            assert response.status == 200
            assert int(response.headers["Content-Length"]) > 0
            assert response.read() == b""

        with pytest.raises(urllib.error.HTTPError) as not_found:
            urllib.request.urlopen(base_url + "/nao-existe", timeout=5)
        assert not_found.value.code == 404

        with pytest.raises(urllib.error.HTTPError) as invalid:
            urllib.request.urlopen(base_url + "/api/events?severity=extreme", timeout=5)
        assert invalid.value.code == 400

        with pytest.raises(urllib.error.HTTPError) as missing:
            urllib.request.urlopen(base_url + "/api/events/inexistente", timeout=5)
        assert missing.value.code == 404


def test_server_does_not_expose_write_methods(context: CommandContext) -> None:
    service = WebDataService(context.config, context.paths)
    with _running(service) as base_url:
        request = urllib.request.Request(base_url + "/api/summary", method="POST")
        with pytest.raises(urllib.error.HTTPError) as post:
            urllib.request.urlopen(request, timeout=5)
        assert post.value.code == 405
        assert "somente leitura" in post.value.read().decode("utf-8")


def test_serve_rejects_non_loopback_host(context: CommandContext) -> None:
    with pytest.raises(SentinelError, match="loopback"):
        _run(context, "serve", "--host", "0.0.0.0")


def test_web_events_repository_filters(context: CommandContext) -> None:
    seed_demo(context.config, context.paths)
    database = Database(context.paths.database)
    try:
        events = EventRepository(database)
        assert len(events.list_events(limit=50, source_ip="10.10.10.20")) == 5
        assert len(events.list_events(limit=50, severity="medium")) == 5
        assert events.severity_counts() == {"high": 6, "medium": 5, "low": 1}
        hourly = events.hourly_counts(utc_now() - timedelta(hours=24))
        assert sum(hourly.values()) == len(DEMO_EVENTS)
        assert events.type_counts(limit=3)
    finally:
        database.close()
