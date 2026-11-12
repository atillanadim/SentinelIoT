"""Construcao do parser argparse compartilhado entre CLI e shell."""

from __future__ import annotations

import argparse
from pathlib import Path

from sentineliot import __author__, __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentineliot",
        description=(
            "SentinelIoT - honeypots defensivos e lista de ban para redes IoT. "
            f"Autor: {__author__}."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="arquivo YAML de configuracao (padrao: config/config.yaml ou exemplo)",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="diretorio de dados (padrao: configuracao ou ./data)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="desabilita cores ANSI",
    )
    parser.add_argument("--version", action="version", version=f"SentinelIoT {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    start = subparsers.add_parser("start", help="inicia o agente e as iscas")
    start.add_argument(
        "--foreground",
        action="store_true",
        help="executa no terminal atual em vez de segundo plano",
    )

    subparsers.add_parser("stop", help="para o agente e todas as iscas")
    subparsers.add_parser("status", help="mostra estado do agente, iscas e lista de ban")
    subparsers.add_parser("scan", help="varredura passiva do spool: coleta interacoes novas")

    honeypots = subparsers.add_parser(
        "honeypots",
        aliases=["honeypot"],
        help="lista, adiciona ou remove iscas",
    )
    honeypots_sub = honeypots.add_subparsers(dest="honeypot_command")
    honeypots_sub.add_parser("list", help="mostra iscas configuradas")
    honeypots_sub.add_parser("available", help="mostra perfis de honeypot disponiveis")
    honeypots_add = honeypots_sub.add_parser("add", help="adiciona uma isca")
    honeypots_add.add_argument("profile", help="id do perfil (use 'honeypots available')")
    honeypots_add.add_argument("--id", dest="instance_id", default=None, help="nome da isca")
    honeypots_add.add_argument("--port", type=int, default=None, help="porta TCP")
    honeypots_add.add_argument("--host", default=None, help="IP de escuta")
    honeypots_remove = honeypots_sub.add_parser("remove", help="remove uma isca")
    honeypots_remove.add_argument("instance_id", help="nome da isca")

    events = subparsers.add_parser("events", help="consulta interacoes registradas")
    events_sub = events.add_subparsers(dest="events_command")
    events_list = events_sub.add_parser("list", help="lista eventos")
    events_list.add_argument("--limit", type=int, default=20)
    events_list.add_argument("--ip", default=None)
    events_list.add_argument("--type", dest="event_type", default=None)
    events_show = events_sub.add_parser("show", help="mostra um evento")
    events_show.add_argument("event_id")

    bans = subparsers.add_parser(
        "bans",
        aliases=["ban"],
        help="lista de IPs observados e decisoes",
    )
    bans_sub = bans.add_subparsers(dest="bans_command")
    bans_list = bans_sub.add_parser("list", help="lista IPs observados")
    bans_list.add_argument(
        "--status",
        default=None,
        help="filtra por pending, blocked, allowed, ignored, allowlisted ou all",
    )
    bans_show = bans_sub.add_parser("show", help="detalha um IP e seus eventos")
    bans_show.add_argument("ip")
    for action, description in (
        ("block", "registra decisao de bloquear o IP"),
        ("allow", "registra decisao de permitir o IP"),
        ("ignore", "marca o IP como ignorado"),
        ("reset", "volta o IP para pendente"),
    ):
        decision = bans_sub.add_parser(action, help=description)
        decision.add_argument("ip")
        decision.add_argument("--note", default="", help="observacao do administrador")
    bans_export = bans_sub.add_parser("export", help="exporta a lista de ban")
    bans_export.add_argument("--format", dest="format", choices=["json", "csv"], default="json")
    bans_export.add_argument("--output", default=None, help="arquivo de saida")

    simulate = subparsers.add_parser(
        "simulate", help="gera interacoes de demonstracao (nao sonda a rede)"
    )
    simulate.add_argument("--ip", default="10.10.10.66", help="IP de origem simulado")

    subparsers.add_parser("diagnostics", help="verifica ambiente, banco e agente")
    subparsers.add_parser("version", help="mostra versao e autor")
    subparsers.add_parser("shell", help="abre o shell interativo")

    daemon = subparsers.add_parser("daemon", help=argparse.SUPPRESS)
    daemon.add_argument("--foreground", action="store_true", help=argparse.SUPPRESS)

    return parser
