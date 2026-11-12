"""Shell interativo com banner ASCII e os mesmos comandos da CLI."""

from __future__ import annotations

import argparse
import cmd
import os
import shlex
import sys

from sentineliot import __author__, __version__
from sentineliot.cli.banner import render_banner
from sentineliot.cli.commands import dispatch
from sentineliot.cli.context import CommandContext
from sentineliot.cli.parser import build_parser
from sentineliot.core.errors import SentinelError

HELP_TEXT = """Comandos disponiveis:
  status                      estado do agente, iscas e lista de ban
  start [--foreground]        inicia o agente e as iscas
  stop                        para o agente e as iscas
  scan                        varredura passiva do spool (interacoes novas)
  honeypots available         mostra os perfis de honeypot disponiveis
  honeypots list              mostra as iscas configuradas
  honeypots add <perfil>      adiciona uma isca (--port, --host, --id)
  honeypots remove <id>       remove uma isca
  events [list]               lista interacoes (--limit, --ip, --type)
  events show <id>            detalha uma interacao
  bans [list]                 lista IPs que interagiram (--status)
  bans show <ip>              detalha um IP e seus eventos
  bans block <ip>             registra decisao de bloquear (sem alterar firewall)
  bans allow <ip>             registra decisao de permitir
  bans ignore <ip>            marca como ignorado
  bans reset <ip>             volta para pendente
  bans export [--format]      exporta a lista em json ou csv
  simulate                    grava interacoes de demonstracao
  diagnostics                 checa ambiente, banco, spool e agente
  version                     versao e autor
  banner                      mostra o banner novamente
  clear                       limpa a tela
  help [comando]              mostra esta ajuda ou a ajuda de um comando
  exit | quit                 encerra o shell

Observacao: bloqueios sao apenas decisoes registradas nesta versao.
"""


class SentinelShell(cmd.Cmd):
    prompt = "sentineliot> "

    def __init__(self, context: CommandContext, parser: argparse.ArgumentParser) -> None:
        super().__init__()
        self.context = context
        self.parser = parser

    def cmdloop_with_banner(self) -> int:
        console = self.context.console
        console.print(console.paint(render_banner(__version__, __author__), "cyan"))
        console.print()
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            console.print()
            console.info("interrompido")
        return 0

    def emptyline(self) -> bool:
        return False

    def do_help(self, arg: str) -> None:
        if not arg.strip():
            print(HELP_TEXT)
            return
        tokens = shlex.split(arg)
        try:
            self.parser.parse_args([*tokens, "--help"])
        except SystemExit:
            return

    def do_banner(self, arg: str) -> None:
        _ = arg
        self.context.console.print(
            self.context.console.paint(render_banner(__version__, __author__), "cyan")
        )

    def do_clear(self, arg: str) -> None:
        _ = arg
        os.system("cls" if os.name == "nt" else "clear")

    def do_exit(self, arg: str) -> bool:
        _ = arg
        self.context.console.info("ate logo")
        return True

    def do_quit(self, arg: str) -> bool:
        return self.do_exit(arg)

    def do_EOF(self, arg: str) -> bool:
        _ = arg
        print()
        self.context.console.info("ate logo")
        return True

    def default(self, line: str) -> None:
        tokens = line.strip().split()
        if not tokens:
            return
        blocked = {"shell", "daemon"}
        if tokens[0] in blocked:
            self.context.console.warn(f"'{tokens[0]}' nao pode ser executado dentro do shell")
            return
        try:
            args = self.parser.parse_args(shlex.split(line))
        except SystemExit:
            return
        try:
            exit_code = dispatch(args, self.context)
            if exit_code != 0:
                self.context.console.print(
                    self.context.console.muted(f"  (codigo de saida {exit_code})")
                )
        except SentinelError as exc:
            self.context.console.error(str(exc))
        except KeyboardInterrupt:
            print()
            self.context.console.info("interrompido")
        except Exception as exc:  # pragma: no cover - protege o shell de falhas inesperadas
            self.context.console.error(f"falha inesperada: {exc}")
            self.context.console.print(
                self.context.console.muted("  detalhes tecnicos podem estar no log do agente")
            )
        self.lastcmd = ""


def run_shell(context: CommandContext) -> int:
    shell = SentinelShell(context, build_parser())
    return shell.cmdloop_with_banner()


def is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()
