"""Teste de fumaca da Fase 0."""

from __future__ import annotations

from sentineliot import __version__


def test_package_imports() -> None:
    assert __version__ == "0.1.0"
