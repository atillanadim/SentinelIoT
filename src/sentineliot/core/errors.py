"""Erros esperados da aplicacao, sem stack trace para o usuario final."""

from __future__ import annotations


class SentinelError(Exception):
    """Falha esperada e explicavel para o operador da CLI."""


class ConfigurationError(SentinelError):
    """Configuracao ausente, invalida ou insegura."""


class StorageError(SentinelError):
    """Falha ao abrir ou consultar o banco local."""


class HoneypotError(SentinelError):
    """Falha ao iniciar, parar ou configurar uma isca."""
