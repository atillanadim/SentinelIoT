#!/usr/bin/python3
"""Funções comuns dos honeypots Apache (metadados apenas)."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs

SPOOL = Path("/var/log/sentinel/honeypot.jsonl")


def client_ip() -> str:
    # Apenas o peer TCP. X-Forwarded-For não é confiável para decisão.
    return os.environ.get("REMOTE_ADDR", "0.0.0.0")


def read_form() -> dict[str, list[str]]:
    try:
        length = int(os.environ.get("CONTENT_LENGTH", "0") or 0)
    except ValueError:
        length = 0
    raw = sys.stdin.buffer.read(length) if length > 0 else b""
    return parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)


def log_event(
    *,
    honeypot: str,
    event_type: str,
    path: str,
    method: str,
    status: int,
    detail: str = "",
) -> None:
    record = {
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_ip": client_ip(),
        "source_port": os.environ.get("REMOTE_PORT", ""),
        "honeypot": honeypot,
        "event_type": event_type,
        "method": method,
        "path": path[:256],
        "status": status,
        "user_agent": os.environ.get("HTTP_USER_AGENT", "")[:200],
        "detail": detail[:200],
    }
    line = json.dumps(record, ensure_ascii=False) + "\n"
    SPOOL.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(SPOOL, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    try:
        os.write(descriptor, line.encode("utf-8"))
    finally:
        os.close(descriptor)


def respond(status: int, body: str, content_type: str = "text/html; charset=utf-8") -> None:
    payload = body.encode("utf-8")
    reason = {
        200: "OK",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        500: "Internal Server Error",
    }.get(status, "OK")
    sys.stdout.write(f"Status: {status} {reason}\r\n")
    sys.stdout.write(f"Content-Type: {content_type}\r\n")
    sys.stdout.write(f"Content-Length: {len(payload)}\r\n")
    sys.stdout.write("Cache-Control: no-store\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()
