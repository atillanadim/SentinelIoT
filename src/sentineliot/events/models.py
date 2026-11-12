"""Modelo de evento e normalizacao do spool JSONL."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sentineliot.security.validation import parse_ip, safe_text

SEVERITY_ORDER: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

SCORE_BY_TYPE: dict[str, int] = {
    "attack_tool": 5,
    "injection_attempt": 5,
    "credential_attempt": 3,
    "config_attempt": 3,
    "auth_failure": 2,
    "honeypot_probe": 2,
    "probe": 2,
    "connection": 1,
    "request": 1,
}

SEVERITY_BY_TYPE: dict[str, str] = {
    "attack_tool": "high",
    "injection_attempt": "high",
    "credential_attempt": "high",
    "config_attempt": "medium",
    "auth_failure": "medium",
    "honeypot_probe": "medium",
    "probe": "medium",
    "connection": "low",
    "request": "low",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_utc(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def _parse_timestamp(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        return utc_now()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return utc_now()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_port(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        port = int(text)
    except ValueError:
        return None
    return port if 0 < port <= 65535 else None


def _parse_status(value: object) -> int:
    try:
        status = int(str(value).strip())
    except ValueError:
        return 0
    return status if 100 <= status <= 599 else 0


@dataclass(frozen=True)
class Event:
    """Metadados minimos de uma interacao com uma isca."""

    source_ip: str
    honeypot_id: str
    profile: str
    protocol: str
    event_type: str
    timestamp_utc: datetime
    event_id: str
    source_port: int | None = None
    method: str = ""
    path: str = ""
    status: int = 0
    user_agent: str = ""
    detail: str = ""

    @property
    def severity(self) -> str:
        return SEVERITY_BY_TYPE.get(self.event_type, "low")

    @property
    def score(self) -> int:
        return SCORE_BY_TYPE.get(self.event_type, 1)

    def to_record(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "timestamp_utc": iso_utc(self.timestamp_utc),
            "source_ip": self.source_ip,
            "source_port": self.source_port or "",
            "honeypot": self.honeypot_id,
            "honeypot_id": self.honeypot_id,
            "profile": self.profile,
            "protocol": self.protocol,
            "event_type": self.event_type,
            "severity": self.severity,
            "method": self.method,
            "path": self.path,
            "status": self.status,
            "user_agent": self.user_agent,
            "detail": self.detail,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> Event | None:
        source_ip = str(data.get("source_ip", "")).strip()
        if parse_ip(source_ip) is None:
            return None
        timestamp = _parse_timestamp(data.get("timestamp_utc"))
        event_type = str(data.get("event_type", "request")).strip()
        if event_type not in SCORE_BY_TYPE:
            event_type = "request"
        honeypot_id = safe_text(data.get("honeypot_id") or data.get("honeypot"), 64) or "unknown"
        profile = safe_text(data.get("profile"), 64) or honeypot_id
        protocol = safe_text(data.get("protocol"), 16) or "http"
        method = safe_text(data.get("method"), 16).upper()
        path = safe_text(data.get("path"), 256)
        user_agent = safe_text(data.get("user_agent"), 200)
        detail = safe_text(data.get("detail"), 200)
        event_id = safe_text(data.get("event_id"), 64)
        if not event_id:
            raw = "|".join(
                (
                    source_ip,
                    iso_utc(timestamp),
                    honeypot_id,
                    event_type,
                    path,
                    str(data.get("source_port", "")),
                )
            )
            event_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
        return cls(
            source_ip=str(parse_ip(source_ip)),
            honeypot_id=honeypot_id,
            profile=profile,
            protocol=protocol,
            event_type=event_type,
            timestamp_utc=timestamp,
            event_id=event_id,
            source_port=_parse_port(data.get("source_port")),
            method=method,
            path=path,
            status=_parse_status(data.get("status")),
            user_agent=user_agent,
            detail=detail,
        )
