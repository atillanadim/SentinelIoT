"""Estado do processo daemon e deteccao de execucao."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from sentineliot.honeypot.servers import RunningHoneypot


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class RuntimeInstance:
    id: str
    profile: str
    host: str
    port: int
    protocol: str

    @classmethod
    def from_running(cls, running: RunningHoneypot) -> RuntimeInstance:
        return cls(
            id=running.id,
            profile=running.profile,
            host=running.host,
            port=running.port,
            protocol=running.protocol,
        )

    @classmethod
    def from_record(cls, data: dict[str, Any]) -> RuntimeInstance:
        return cls(
            id=str(data.get("id", "")),
            profile=str(data.get("profile", "")),
            host=str(data.get("host", "")),
            port=int(data.get("port", 0)),
            protocol=str(data.get("protocol", "")),
        )

    def to_record(self) -> dict[str, object]:
        return {
            "id": self.id,
            "profile": self.profile,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
        }


@dataclass(frozen=True)
class RuntimeSnapshot:
    pid: int
    started_at: str
    mode: str
    config_path: str
    instances: tuple[RuntimeInstance, ...]

    def to_record(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "started_at": self.started_at,
            "mode": self.mode,
            "config_path": self.config_path,
            "instances": [instance.to_record() for instance in self.instances],
        }


def write_runtime(path: Path, snapshot: RuntimeSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(snapshot.to_record(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_runtime(path: Path) -> RuntimeSnapshot | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        instances_raw = raw.get("instances", [])
        instances = tuple(
            RuntimeInstance.from_record(item) for item in instances_raw if isinstance(item, dict)
        )
        return RuntimeSnapshot(
            pid=int(raw.get("pid", 0)),
            started_at=str(raw.get("started_at", "")),
            mode=str(raw.get("mode", "")),
            config_path=str(raw.get("config_path", "")),
            instances=instances,
        )
    except (TypeError, ValueError):
        return None


def remove_runtime(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _process(pid: int) -> psutil.Process | None:
    if pid <= 0:
        return None
    try:
        process = psutil.Process(pid)
        if process.status() == psutil.STATUS_ZOMBIE:
            return None
        return process
    except psutil.Error:
        return None


def pid_alive(pid: int) -> bool:
    process = _process(pid)
    if process is None:
        return False
    try:
        return bool(process.is_running())
    except psutil.Error:
        return False


def is_our_daemon(pid: int) -> bool:
    process = _process(pid)
    if process is None:
        return False
    try:
        command_line = " ".join(process.cmdline()).lower()
    except psutil.Error:
        return False
    return "sentineliot" in command_line and "daemon" in command_line


def active_snapshot(path: Path) -> RuntimeSnapshot | None:
    """Retorna o runtime ativo; remove arquivo obsoleto automaticamente."""
    snapshot = read_runtime(path)
    if snapshot is None:
        return None
    if not is_our_daemon(snapshot.pid):
        remove_runtime(path)
        return None
    return snapshot


def new_snapshot(
    pid: int, mode: str, config_path: Path | None, instances: list[RunningHoneypot]
) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        pid=pid,
        started_at=_iso_now(),
        mode=mode,
        config_path=str(config_path) if config_path is not None else "",
        instances=tuple(RuntimeInstance.from_running(item) for item in instances),
    )
