"""Banner ASCII exibido ao abrir o shell do SentinelIoT."""

from __future__ import annotations

BANNER = r"""
   _____ ______ _   _ _______ _____ _   _ ______ _      _____  ____ _______
  / ____|  ____| \ | |__   __|_   _| \ | |  ____| |    |_   _|/ __ \__   __|
 | (___ | |__  |  \| |  | |    | | |  \| | |__  | |      | | | |  | | | |
  \___ \|  __| | . ` |  | |    | | | . ` |  __| | |      | | | |  | | | |
  ____) | |____| |\  |  | |   _| |_| |\  | |____| |____ _| |_| |__| | | |
 |_____/|______|_| \_|  |_|  |_____|_| \_|______|______|_____|\____/  |_|
"""


def render_banner(version: str, author: str) -> str:
    subtitle = f"  honeypots defensivos para redes IoT   |   autor: {author}   |   v{version}"
    rule = "  " + "-" * 74
    hint = "  Digite 'help' para ver os comandos. Use apenas em laboratorio autorizado."
    return "\n".join((BANNER.rstrip("\n"), "", subtitle, rule, hint))
