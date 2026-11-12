"""Escrita append-only do spool JSONL consumido pelo agente."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from sentineliot.events.models import Event


class SpoolWriter:
    """Grava uma linha JSON por evento, com exclusao mutua entre threads."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: Event) -> None:
        line = json.dumps(event.to_record(), ensure_ascii=False) + "\n"
        payload = line.encode("utf-8")
        with self._lock:
            descriptor = self.path.open("ab")
            try:
                descriptor.write(payload)
                descriptor.flush()
            finally:
                descriptor.close()
