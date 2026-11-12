"""Contexto compartilhado pelos comandos da CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sentineliot.cli.output import Console
from sentineliot.core.config import Config, load_config
from sentineliot.core.paths import RuntimePaths


@dataclass(frozen=True)
class CommandContext:
    config: Config
    paths: RuntimePaths
    console: Console


def create_context(
    *,
    config_path: Path | None = None,
    data_dir: Path | None = None,
    no_color: bool = False,
) -> CommandContext:
    config = load_config(config_path)
    paths = RuntimePaths.build(config, data_dir)
    return CommandContext(
        config=config,
        paths=paths,
        console=Console(color=False if no_color else None),
    )
