"""API publica do dominio de eventos."""

from __future__ import annotations

from sentineliot.events.classification import Signal, classify_http
from sentineliot.events.models import (
    SCORE_BY_TYPE,
    SEVERITY_BY_TYPE,
    SEVERITY_ORDER,
    Event,
    iso_utc,
    utc_now,
)

__all__ = [
    "SCORE_BY_TYPE",
    "SEVERITY_BY_TYPE",
    "SEVERITY_ORDER",
    "Event",
    "Signal",
    "classify_http",
    "iso_utc",
    "utc_now",
]
