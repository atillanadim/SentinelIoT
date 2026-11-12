"""Ponto de entrada da CLI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from sentineliot import __author__, __version__
from sentineliot.cli.banner import render_banner
from sentineliot.cli.commands import dispatch
from sentineliot.cli.context import create_context
from sentineliot.cli.output import Console
from sentineliot.cli.parser import build_parser
from sentineliot.cli.shell import is_interactive, run_shell
from sentineliot.core.errors import SentinelError


def _config_path(args: argparse.Namespace) -> Path | None:
    value = getattr(args, "config", None)
    if value is None:
        return None
    return Path(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    console = Console(color=False if getattr(args, "no_color", False) else None)
    data_dir_raw = getattr(args, "data_dir", None)
    data_dir = Path(data_dir_raw) if data_dir_raw else None

    try:
        context = create_context(
            config_path=_config_path(args),
            data_dir=data_dir,
            no_color=bool(getattr(args, "no_color", False)),
        )
    except SentinelError as exc:
        console.error(str(exc))
        return 1

    command = getattr(args, "command", None)
    if command in (None, "shell"):
        if command == "shell" or is_interactive():
            return run_shell(context)
        console.print(console.paint(render_banner(__version__, __author__), "cyan"))
        console.print()
        parser.print_help()
        console.print()
        console.info("use 'sentineliot shell' em um terminal interativo")
        return 0

    try:
        return dispatch(args, context)
    except SentinelError as exc:
        context.console.error(str(exc))
        return 1
    except KeyboardInterrupt:
        print()
        context.console.info("interrompido")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
