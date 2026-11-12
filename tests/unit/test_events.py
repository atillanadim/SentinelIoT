"""Testes dos modelos de evento e da classificacao HTTP."""

from __future__ import annotations

from datetime import UTC, datetime

from sentineliot.events.classification import classify_http
from sentineliot.events.models import Event


def _event(**overrides: object) -> Event:
    values: dict[str, object] = {
        "source_ip": "10.0.0.5",
        "honeypot_id": "camera-01",
        "profile": "camera-http",
        "protocol": "http",
        "event_type": "honeypot_probe",
        "timestamp_utc": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        "event_id": "abc123",
    }
    values.update(overrides)
    return Event(**values)  # type: ignore[arg-type]


def test_event_from_record_normalizes_fields() -> None:
    event = Event.from_record(
        {
            "source_ip": "10.0.0.5",
            "honeypot": "camera-01",
            "profile": "camera-http",
            "protocol": "http",
            "event_type": "attack_tool",
            "timestamp_utc": "2026-01-02T03:04:05Z",
            "source_port": "4567",
            "method": "get",
            "path": "/admin/",
            "status": "401",
            "user_agent": "sqlmap/1.8",
            "detail": "teste",
        }
    )

    assert event is not None
    assert event.source_ip == "10.0.0.5"
    assert event.event_type == "attack_tool"
    assert event.source_port == 4567
    assert event.method == "GET"
    assert event.status == 401
    assert event.severity == "high"
    assert event.score == 5
    assert event.timestamp_utc.tzinfo is not None
    assert len(event.event_id) == 20


def test_event_rejects_invalid_ip() -> None:
    assert Event.from_record({"source_ip": "not-an-ip"}) is None
    assert Event.from_record({"source_ip": ""}) is None


def test_event_unknown_type_falls_back_to_request() -> None:
    event = Event.from_record({"source_ip": "10.0.0.5", "event_type": "unknown"})
    assert event is not None
    assert event.event_type == "request"
    assert event.severity == "low"


def test_to_record_contains_minimal_metadata() -> None:
    record = _event(method="GET", path="/admin/", status=200).to_record()

    assert record["honeypot_id"] == "camera-01"
    assert record["source_port"] == ""
    assert record["severity"] == "medium"
    assert record["path"] == "/admin/"


def test_attack_tool_and_sensitive_path_generate_multiple_signals() -> None:
    signals = classify_http(
        target="/admin/",
        method="GET",
        user_agent="sqlmap/1.8",
        status=200,
        is_post=False,
    )

    assert [signal.event_type for signal in signals] == ["attack_tool", "honeypot_probe"]


def test_login_post_generates_credential_attempt_without_probe() -> None:
    signals = classify_http(
        target="/cgi-bin/sentinel_login.py",
        method="POST",
        user_agent="python-requests/2.31",
        status=401,
        is_post=True,
    )

    assert [signal.event_type for signal in signals] == ["attack_tool", "credential_attempt"]


def test_injection_pattern_is_recorded() -> None:
    signals = classify_http(
        target="/?id=1%20UNION%20SELECT%20password",
        method="GET",
        user_agent="Mozilla/5.0",
        status=200,
        is_post=False,
    )

    assert any(signal.event_type == "injection_attempt" for signal in signals)


def test_plain_request_has_single_low_severity_signal() -> None:
    signals = classify_http(
        target="/",
        method="GET",
        user_agent="Mozilla/5.0",
        status=200,
        is_post=False,
    )

    assert [signal.event_type for signal in signals] == ["request"]


def test_auth_failure_is_classified() -> None:
    signals = classify_http(
        target="/private",
        method="GET",
        user_agent="Mozilla/5.0",
        status=401,
        is_post=False,
    )

    assert [signal.event_type for signal in signals] == ["auth_failure"]
