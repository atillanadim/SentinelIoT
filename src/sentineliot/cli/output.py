"""Saida de terminal simples, sem dependencias externas."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence

RESET = "\033[0m"
STYLES = {
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "dim": "\033[2m",
    "bold": "\033[1m",
}


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True
    return "WT_SESSION" in os.environ or "TERM" in os.environ


def _truncate(value: str, width: int) -> str:
    text = value.replace("\n", " ").replace("\r", " ")
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "\u2026"
    return text[: width - 1] + "\u2026"


class Console:
    def __init__(self, color: bool | None = None) -> None:
        self.color = _supports_color() if color is None else color

    def paint(self, text: str, style: str) -> str:
        if not self.color or style not in STYLES:
            return text
        return f"{STYLES[style]}{text}{RESET}"

    def print(self, text: str = "") -> None:
        print(text)

    def title(self, text: str) -> None:
        print()
        print(self.paint(text, "cyan"))

    def success(self, text: str) -> None:
        print(self.paint(f"[ok] {text}", "green"))

    def info(self, text: str) -> None:
        print(self.paint(f"[i] {text}", "blue"))

    def warn(self, text: str) -> None:
        print(self.paint(f"[aviso] {text}", "yellow"))

    def error(self, text: str) -> None:
        print(self.paint(f"[erro] {text}", "red"))

    def muted(self, text: str) -> str:
        return self.paint(text, "dim")

    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        max_widths: Sequence[int] | None = None,
    ) -> None:
        if not rows:
            print(self.muted("  (nenhum registro)"))
            return
        columns = len(headers)
        if max_widths is None:
            max_widths = [40] * columns
        widths = [len(header) for header in headers]
        normalized: list[list[str]] = []
        for row in rows:
            cells = [str(value) for value in row]
            if len(cells) < columns:
                cells.extend([""] * (columns - len(cells)))
            cells = cells[:columns]
            for index, cell in enumerate(cells):
                widths[index] = max(widths[index], len(cell))
            normalized.append(cells)
        for index in range(columns):
            widths[index] = min(widths[index], max_widths[index])

        header_line = "  ".join(
            _truncate(header, widths[index]).ljust(widths[index])
            for index, header in enumerate(headers)
        )
        print(self.paint(header_line, "bold"))
        print(self.paint("  ".join("-" * width for width in widths), "dim"))
        for row in normalized:
            print(
                "  ".join(
                    _truncate(cell, widths[index]).ljust(widths[index])
                    for index, cell in enumerate(row)
                )
            )
