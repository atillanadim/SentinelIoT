"""Caminhos de runtime derivados do diretorio de dados."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sentineliot.core.config import Config


@dataclass(frozen=True)
class RuntimePaths:
    data_dir: Path
    spool_dir: Path
    spool_file: Path
    database: Path
    honeypots_state: Path
    runtime_state: Path
    log_dir: Path
    log_file: Path

    @classmethod
    def build(cls, config: Config, data_dir: Path | None = None) -> RuntimePaths:
        env_dir = os.environ.get("SENTINELIOT_DATA_DIR", "").strip()
        selected = data_dir or (Path(env_dir) if env_dir else Path(config.agent.data_dir))
        resolved = selected.expanduser().resolve()
        log_env = os.environ.get("SENTINELIOT_LOG_DIR", "").strip()
        log_dir = Path(log_env).expanduser().resolve() if log_env else resolved.parent / "logs"
        return cls(
            data_dir=resolved,
            spool_dir=resolved / "spool",
            spool_file=resolved / "spool" / "honeypot.jsonl",
            database=resolved / "sentineliot.db",
            honeypots_state=resolved / "honeypots.json",
            runtime_state=resolved / "runtime.json",
            log_dir=log_dir,
            log_file=log_dir / "sentineliot.log",
        )

    def ensure(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
