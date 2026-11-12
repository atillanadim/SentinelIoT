"""Leitura incremental do spool JSONL das iscas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sentineliot.events.models import Event
from sentineliot.security.validation import is_allowlisted
from sentineliot.storage.database import Database, EventRepository, SuspectRepository

OFFSET_KEY = "spool_offset"


@dataclass(frozen=True)
class CollectResult:
    read_lines: int
    saved_events: int
    duplicate_events: int
    malformed_lines: int
    new_ips: int

    @property
    def has_activity(self) -> bool:
        return self.saved_events > 0


class EventCollector:
    """Consome o spool append-only sem reler linhas ja processadas."""

    def __init__(
        self,
        database: Database,
        spool_file: Path,
        allowlist: tuple[str, ...] = (),
    ) -> None:
        self.database = database
        self.spool_file = spool_file
        self.allowlist = allowlist
        self.events = EventRepository(database)
        self.suspects = SuspectRepository(database)

    def collect(self) -> CollectResult:
        if not self.spool_file.is_file():
            return CollectResult(0, 0, 0, 0, 0)

        size = self.spool_file.stat().st_size
        offset = self._read_offset()
        if size < offset:
            offset = 0

        with self.spool_file.open("rb") as handle:
            handle.seek(offset)
            chunk = handle.read()

        if not chunk:
            return CollectResult(0, 0, 0, 0, 0)

        complete, remainder = self._split_complete_lines(chunk)
        text = complete.decode("utf-8", errors="replace")
        lines = [line for line in text.splitlines() if line.strip()]
        saved = 0
        duplicates = 0
        malformed = 0
        new_ips = 0

        for line in lines:
            event = self._parse_line(line)
            if event is None:
                malformed += 1
                continue
            if not self.events.save(event):
                duplicates += 1
                continue
            before = self.suspects.get(event.source_ip)
            allowed = is_allowlisted(event.source_ip, self.allowlist)
            self.suspects.observe(event, allowlisted=allowed)
            if before is None:
                new_ips += 1
            saved += 1

        consumed = offset + len(complete)
        self.database.set_setting(OFFSET_KEY, str(consumed))
        _ = remainder
        return CollectResult(len(lines), saved, duplicates, malformed, new_ips)

    def reset_offset(self) -> None:
        self.database.set_setting(OFFSET_KEY, "0")

    def _read_offset(self) -> int:
        raw = self.database.get_setting(OFFSET_KEY, "0")
        try:
            return max(0, int(raw))
        except ValueError:
            return 0

    @staticmethod
    def _split_complete_lines(chunk: bytes) -> tuple[bytes, bytes]:
        if chunk.endswith(b"\n"):
            return chunk, b""
        index = chunk.rfind(b"\n")
        if index < 0:
            return b"", chunk
        return chunk[: index + 1], chunk[index + 1 :]

    @staticmethod
    def _parse_line(line: str) -> Event | None:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        return Event.from_record(data)
