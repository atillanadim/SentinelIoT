"""Implementacao dos comandos da CLI e ponte para o runtime."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psutil

from sentineliot import __author__, __version__
from sentineliot.cli.context import CommandContext
from sentineliot.core.agent import AgentRuntime
from sentineliot.core.errors import HoneypotError, SentinelError, StorageError
from sentineliot.core.runtime import active_snapshot, pid_alive, read_runtime, remove_runtime
from sentineliot.events.collector import CollectResult, EventCollector
from sentineliot.events.models import Event, iso_utc, utc_now
from sentineliot.honeypot.profiles import get_profile, list_profiles
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.honeypot.state import (
    HoneypotInstance,
    load_instances,
    save_instances,
    validate_instances,
)
from sentineliot.security.validation import (
    is_allowlisted,
    is_blockable,
    validate_identifier,
    validate_ip,
    validate_port,
)
from sentineliot.storage.database import (
    SUSPECT_STATUSES,
    Database,
    EventRepository,
    StoredEvent,
    SuspectRepository,
)

DAEMON_START_TIMEOUT = 10.0


@contextmanager
def _database(ctx: CommandContext) -> Iterator[Database]:
    ctx.paths.ensure()
    database = Database(ctx.paths.database)
    try:
        yield database
    finally:
        database.close()


def _load_instances(ctx: CommandContext) -> list[HoneypotInstance]:
    ctx.paths.ensure()
    return load_instances(ctx.paths.honeypots_state, ctx.config)


def _display_time(value: str) -> str:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value[:19]
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _details(ctx: CommandContext, pairs: Sequence[tuple[str, str]]) -> None:
    if not pairs:
        return
    width = max(len(key) for key, _ in pairs)
    for key, value in pairs:
        print(f"  {key.ljust(width)} : {value}")


def _tail(path: Path, lines: int = 14) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])


def _collect(ctx: CommandContext, database: Database) -> CollectResult:
    collector = EventCollector(database, ctx.paths.spool_file, ctx.config.allowlist)
    return collector.collect()


def cmd_status(ctx: CommandContext) -> int:
    ctx.console.title("SentinelIoT - status")
    snapshot = active_snapshot(ctx.paths.runtime_state)
    instance_error = ""
    try:
        instances = _load_instances(ctx)
    except HoneypotError as exc:
        instances = []
        instance_error = str(exc)

    with _database(ctx) as database:
        events = EventRepository(database)
        suspects = SuspectRepository(database)
        total_events = events.count()
        last_24h = events.count_since(utc_now() - timedelta(hours=24))
        last_event = events.last_event()
        stats = suspects.stats()
        pending = suspects.pending_count()
        total_suspects = suspects.total()

    if snapshot is not None:
        agent_state = (
            f"em execucao (pid {snapshot.pid}, desde {_display_time(snapshot.started_at)})"
        )
        running_ids = {item.id for item in snapshot.instances}
    else:
        agent_state = "parado"
        running_ids = set()

    _details(
        ctx,
        [
            ("versao", f"{__version__} (autor: {__author__})"),
            ("config", str(ctx.config.source_path or "padroes internos")),
            ("modo", ctx.config.mode),
            ("firewall", f"{ctx.config.firewall.adapter} (nenhuma regra real e aplicada)"),
            ("agente", agent_state),
            ("banco", str(ctx.paths.database)),
            ("eventos", f"{total_events} total | {last_24h} nas ultimas 24h"),
            (
                "IPs observados",
                f"{total_suspects} total | {pending} pendente(s) de decisao",
            ),
            (
                "decisoes",
                " | ".join(f"{key}={value}" for key, value in sorted(stats.items())) or "nenhuma",
            ),
        ],
    )
    if last_event is not None:
        ctx.console.print(
            "  ultimo evento            : "
            f"{_display_time(last_event.timestamp_utc)} | {last_event.source_ip} | "
            f"{last_event.honeypot_id} | {last_event.event_type}"
        )
    if instance_error:
        ctx.console.warn(f"estado de honeypots com problema: {instance_error}")

    ctx.console.print()
    ctx.console.print(ctx.console.paint("  honeypots configurados", "bold"))
    rows = [
        [
            instance.id,
            instance.profile,
            instance.endpoint,
            "ATIVO" if instance.id in running_ids else "parado",
        ]
        for instance in instances
    ]
    ctx.console.table(
        ["id", "perfil", "endpoint", "estado"],
        [[row[0], row[1], row[2], row[3]] for row in rows],
        max_widths=[22, 16, 24, 8],
    )
    if snapshot is None:
        ctx.console.info("use 'start' para iniciar o agente e as iscas em segundo plano")
    return 0


def _spawn_daemon(ctx: CommandContext) -> int:
    ctx.paths.ensure()
    command: list[str] = [sys.executable, "-m", "sentineliot"]
    if ctx.config.source_path is not None:
        command.extend(["--config", str(ctx.config.source_path.resolve())])
    command.extend(
        [
            "--data-dir",
            str(ctx.paths.data_dir),
            "daemon",
        ]
    )
    environment = os.environ.copy()
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "sentineliot").is_dir():
        existing = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = (
            str(source_root) + os.pathsep + existing if existing else str(source_root)
        )

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    with ctx.paths.log_file.open("a", encoding="utf-8") as log_handle:
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                env=environment,
                close_fds=True,
                creationflags=creationflags,
                start_new_session=os.name != "nt",
            )
        except OSError as exc:
            raise SentinelError(f"nao foi possivel iniciar o daemon: {exc}") from exc

    deadline = time.monotonic() + DAEMON_START_TIMEOUT
    snapshot = None
    while time.monotonic() < deadline:
        snapshot = read_runtime(ctx.paths.runtime_state)
        # No Windows o python.exe do venv e um trampolim: o PID do processo
        # lancado difere do PID do interpretador que escreve o runtime.
        if snapshot is not None and pid_alive(snapshot.pid):
            break
        exit_code = process.poll()
        if exit_code is not None:
            detail = _tail(ctx.paths.log_file)
            raise SentinelError(
                "o daemon encerrou durante a inicializacao "
                f"(codigo {exit_code}). Log: {ctx.paths.log_file}\n{detail}"
            )
        time.sleep(0.2)
    else:
        process.terminate()
        detail = _tail(ctx.paths.log_file)
        raise SentinelError(
            "o daemon nao confirmou a inicializacao a tempo. "
            f"Consulte {ctx.paths.log_file}\n{detail}"
        )

    active_pid = snapshot.pid if snapshot is not None else process.pid
    ctx.console.success(f"agente iniciado em segundo plano (pid {active_pid})")
    ctx.console.print(f"  log: {ctx.paths.log_file}")
    if snapshot is not None:
        if snapshot.instances:
            ctx.console.print("  honeypots ativos:")
            for item in snapshot.instances:
                ctx.console.print(
                    f"    - {item.id} ({item.profile}) em {item.host}:{item.port}/{item.protocol}"
                )
        else:
            ctx.console.warn("nenhuma isca ativa; configure com 'honeypots add <perfil>'")
    ctx.console.info("use 'scan' para processar interacoes ou 'bans list' para decidir IPs")
    return 0


def cmd_start(ctx: CommandContext, *, foreground: bool = False) -> int:
    snapshot = active_snapshot(ctx.paths.runtime_state)
    if snapshot is not None:
        ctx.console.info(f"o agente ja esta em execucao (pid {snapshot.pid})")
        return 0
    if foreground:
        ctx.console.info(
            f"iniciando em primeiro plano no modo {ctx.config.mode}; Ctrl+C para parar"
        )
        return AgentRuntime(ctx.config, ctx.paths, console=True).run()
    return _spawn_daemon(ctx)


def cmd_stop(ctx: CommandContext) -> int:
    snapshot = active_snapshot(ctx.paths.runtime_state)
    if snapshot is None:
        ctx.console.warn("o agente nao esta em execucao")
        return 0

    try:
        process = psutil.Process(snapshot.pid)
        process.terminate()
        try:
            process.wait(timeout=10)
        except psutil.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    except psutil.NoSuchProcess:
        pass
    except psutil.Error as exc:
        raise SentinelError(f"falha ao parar o processo {snapshot.pid}: {exc}") from exc
    finally:
        remove_runtime(ctx.paths.runtime_state)

    ctx.console.success(f"agente parado (pid {snapshot.pid})")
    with _database(ctx) as database:
        result = _collect(ctx, database)
    if result.saved_events:
        ctx.console.info(
            f"{result.saved_events} interacao(oes) final(is) coletada(s) apos a parada"
        )
    return 0


def cmd_scan(ctx: CommandContext) -> int:
    ctx.console.title("Varredura passiva das iscas")
    with _database(ctx) as database:
        result = _collect(ctx, database)
        suspects = SuspectRepository(database)
        events = EventRepository(database)
        pending = suspects.pending_count()
        latest = events.list_events(limit=8)

    _details(
        ctx,
        [
            ("linhas lidas", str(result.read_lines)),
            ("eventos novos", str(result.saved_events)),
            ("IPs novos", str(result.new_ips)),
            ("duplicados", str(result.duplicate_events)),
            ("linhas invalidas", str(result.malformed_lines)),
            ("IPs pendentes", str(pending)),
        ],
    )
    if not result.has_activity:
        ctx.console.info("nenhuma interacao nova no spool das iscas")
    ctx.console.print(
        ctx.console.muted("  A varredura nao sonda a rede; ela apenas processa o spool das iscas.")
    )
    if latest:
        ctx.console.print()
        _print_events(ctx, latest)
        ctx.console.info("detalhe: 'events show <id>' | decida: 'bans list'")
    return 0


def cmd_honeypots_available(ctx: CommandContext) -> int:
    ctx.console.title("Honeypots disponiveis")
    rows = [
        [
            profile.id,
            profile.protocol,
            str(profile.default_port),
            profile.display_name,
            profile.description,
        ]
        for profile in list_profiles()
    ]
    ctx.console.table(
        ["perfil", "proto", "porta", "nome", "descricao"],
        rows,
        max_widths=[16, 8, 6, 26, 58],
    )
    ctx.console.print()
    ctx.console.info("adicione com: honeypots add <perfil> [--port N] [--host IP] [--id NOME]")
    return 0


def cmd_honeypots_list(ctx: CommandContext) -> int:
    ctx.console.title("Honeypots configurados")
    try:
        instances = _load_instances(ctx)
    except HoneypotError as exc:
        ctx.console.error(str(exc))
        return 1
    snapshot = active_snapshot(ctx.paths.runtime_state)
    running_ids = {item.id for item in snapshot.instances} if snapshot else set()
    rows = [
        [
            instance.id,
            instance.profile,
            instance.endpoint,
            "ATIVO" if instance.id in running_ids else "parado",
        ]
        for instance in instances
    ]
    ctx.console.table(
        ["id", "perfil", "endpoint", "estado"],
        rows,
        max_widths=[22, 16, 26, 8],
    )
    if snapshot is None:
        ctx.console.info("agente parado; as iscas configuradas sobem com 'start'")
    ctx.console.info("catalogo: 'honeypots available' | remover: 'honeypots remove <id>'")
    return 0


def _next_instance_id(profile_id: str, existing: Sequence[HoneypotInstance]) -> str:
    base = profile_id.replace("_", "-")[:24]
    used = {instance.id for instance in existing}
    for index in range(1, 100):
        candidate = f"{base}-{index:02d}"
        if candidate not in used:
            return validate_identifier(candidate)
    raise SentinelError("nao foi possivel gerar um identificador livre")


def _port_available(host: str, port: int) -> tuple[bool, str]:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    probe = socket.socket(family, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((host, port))
    except OSError as exc:
        return False, str(exc)
    finally:
        probe.close()
    return True, ""


def _wait_for_instance(ctx: CommandContext, instance_id: str, *, present: bool) -> bool:
    poll = ctx.config.agent.poll_interval_seconds
    deadline = time.monotonic() + poll + 3
    while time.monotonic() < deadline:
        snapshot = read_runtime(ctx.paths.runtime_state)
        if snapshot is not None:
            ids = {item.id for item in snapshot.instances}
            if (instance_id in ids) is present:
                return True
        time.sleep(0.25)
    return False


def cmd_honeypots_add(
    ctx: CommandContext,
    *,
    profile_id: str,
    instance_id: str | None,
    port: int | None,
    host: str | None,
) -> int:
    profile = get_profile(profile_id)
    instances = _load_instances(ctx)
    identifier = (
        validate_identifier(instance_id)
        if instance_id
        else _next_instance_id(profile.id, instances)
    )
    selected_host = validate_ip(host) if host else ctx.config.honeypot.publish_host
    selected_port = validate_port(port if port is not None else profile.default_port)
    instance = HoneypotInstance(
        id=identifier,
        profile=profile.id,
        host=selected_host,
        port=selected_port,
    )
    validate_instances([*instances, instance])
    available, reason = _port_available(selected_host, selected_port)
    if not available:
        raise HoneypotError(f"porta {selected_host}:{selected_port} indisponivel: {reason}")
    save_instances(ctx.paths.honeypots_state, [*instances, instance])
    ctx.console.success(
        f"isca adicionada: {instance.id} ({profile.display_name}) em {instance.endpoint}"
    )
    snapshot = active_snapshot(ctx.paths.runtime_state)
    if snapshot is None:
        ctx.console.info("agente parado; a isca sera iniciada no proximo 'start'")
        return 0
    if _wait_for_instance(ctx, instance.id, present=True):
        ctx.console.success("isca aplicada no agente em execucao")
    else:
        ctx.console.warn(
            "a isca foi salva, mas o agente ainda nao confirmou o inicio; "
            f"verifique {ctx.paths.log_file}"
        )
    return 0


def cmd_honeypots_remove(ctx: CommandContext, instance_id: str) -> int:
    instances = _load_instances(ctx)
    target = next((item for item in instances if item.id == instance_id), None)
    if target is None:
        raise HoneypotError(f"isca nao encontrada: {instance_id}")
    remaining = [item for item in instances if item.id != instance_id]
    save_instances(ctx.paths.honeypots_state, remaining)
    ctx.console.success(f"isca removida: {target.id} ({target.endpoint})")
    snapshot = active_snapshot(ctx.paths.runtime_state)
    if snapshot is not None and _wait_for_instance(ctx, target.id, present=False):
        ctx.console.success("isca encerrada no agente em execucao")
    elif snapshot is not None:
        ctx.console.warn(
            "remocao salva, mas o agente ainda nao confirmou o encerramento; "
            f"verifique {ctx.paths.log_file}"
        )
    ctx.console.info("os eventos historicos dessa isca continuam no banco")
    return 0


def _print_events(ctx: CommandContext, events: Sequence[StoredEvent]) -> None:
    rows = [
        [
            event.event_id[:12],
            _display_time(event.timestamp_utc),
            event.source_ip,
            event.honeypot_id,
            event.event_type,
            event.severity,
            event.method or "-",
            event.path or "-",
        ]
        for event in events
    ]
    ctx.console.table(
        ["id", "quando", "ip", "isca", "tipo", "sev", "metodo", "caminho"],
        rows,
        max_widths=[13, 19, 18, 15, 19, 8, 7, 44],
    )


def cmd_events_list(
    ctx: CommandContext,
    *,
    limit: int,
    source_ip: str | None = None,
    event_type: str | None = None,
) -> int:
    if source_ip:
        source_ip = validate_ip(source_ip)
    with _database(ctx) as database:
        events = EventRepository(database).list_events(
            limit=limit, source_ip=source_ip, event_type=event_type
        )
    ctx.console.title("Eventos de interacao")
    _print_events(ctx, events)
    if events:
        ctx.console.info("ver detalhes: 'events show <id>'")
    return 0


def cmd_events_show(ctx: CommandContext, event_id: str) -> int:
    cleaned = event_id.strip()
    if not cleaned:
        raise SentinelError("informe o id do evento")
    with _database(ctx) as database:
        repository = EventRepository(database)
        event = repository.get(cleaned)
        if event is None:
            matches = repository.find_by_prefix(cleaned)
            if len(matches) > 1:
                raise SentinelError(
                    f"prefixo ambiguo ({len(matches)} eventos); use mais caracteres"
                )
            event = matches[0] if matches else None
    if event is None:
        raise SentinelError(f"evento nao encontrado: {cleaned}")
    ctx.console.title(f"Evento {event.event_id}")
    _details(
        ctx,
        [
            ("quando", _display_time(event.timestamp_utc)),
            ("IP de origem", f"{event.source_ip}:{event.source_port or '-'}"),
            ("isca", f"{event.honeypot_id} ({event.profile}/{event.protocol})"),
            ("tipo", event.event_type),
            ("severidade", event.severity),
            ("metodo", event.method or "-"),
            ("caminho", event.path or "-"),
            ("HTTP", str(event.status) if event.status else "-"),
            ("user-agent", event.user_agent or "-"),
            ("detalhe", event.detail or "-"),
        ],
    )
    ctx.console.print(
        ctx.console.muted("  Nenhum corpo, query string, senha ou payload e armazenado.")
    )
    return 0


def cmd_bans_list(ctx: CommandContext, status: str | None = None) -> int:
    if status and status != "all" and status not in SUSPECT_STATUSES:
        raise SentinelError(f"status invalido: {status}. Use all, {', '.join(SUSPECT_STATUSES)}")
    selected = None if status in (None, "all") else status
    with _database(ctx) as database:
        repository = SuspectRepository(database)
        suspects = repository.list(status=selected, limit=200)
        stats = repository.stats()
        pending = repository.pending_count()

    ctx.console.title("Lista de ban - IPs que interagiram com as iscas")
    rows = [
        [
            suspect.source_ip,
            str(suspect.hits),
            suspect.max_severity,
            suspect.status,
            _display_time(suspect.first_seen),
            _display_time(suspect.last_seen),
            suspect.last_path or "-",
        ]
        for suspect in suspects
    ]
    ctx.console.table(
        ["ip", "hits", "sev", "decisao", "primeira vez", "ultima vez", "ultimo caminho"],
        rows,
        max_widths=[18, 5, 7, 12, 19, 19, 40],
    )
    summary = " | ".join(f"{key}={value}" for key, value in sorted(stats.items()))
    if summary:
        ctx.console.print()
        ctx.console.print(f"  resumo: {summary} | pendentes={pending}")
    if pending:
        ctx.console.info("decida um IP: 'bans block <ip>', 'bans allow <ip>' ou 'bans ignore <ip>'")
    return 0


def cmd_bans_show(ctx: CommandContext, source_ip: str) -> int:
    source_ip = validate_ip(source_ip)
    with _database(ctx) as database:
        suspect = SuspectRepository(database).get(source_ip)
        events = EventRepository(database).events_for_ip(source_ip, limit=12)
    if suspect is None:
        raise SentinelError(f"IP sem interacoes registradas: {source_ip}")
    ctx.console.title(f"IP {source_ip}")
    _details(
        ctx,
        [
            ("status", suspect.status),
            ("interacoes", str(suspect.hits)),
            ("severidade maxima", suspect.max_severity),
            ("primeira vez", _display_time(suspect.first_seen)),
            ("ultima vez", _display_time(suspect.last_seen)),
            ("decisao em", _display_time(suspect.decision_at) if suspect.decision_at else "-"),
            ("observacao", suspect.decision_note or "-"),
            ("ultimo evento", suspect.last_event_id),
        ],
    )
    ctx.console.print()
    ctx.console.print(ctx.console.paint("  ultimos eventos", "bold"))
    _print_events(ctx, events)
    return 0


def cmd_ban_decide(
    ctx: CommandContext,
    source_ip: str,
    *,
    status: str,
    note: str = "",
) -> int:
    source_ip = validate_ip(source_ip)
    if status not in SUSPECT_STATUSES:
        raise SentinelError(f"decisao invalida: {status}")
    if status == "blocked":
        blockable, reason = is_blockable(source_ip)
        if not blockable:
            raise SentinelError(f"IP nao pode ser bloqueado: {reason}")
        if is_allowlisted(source_ip, ctx.config.allowlist):
            raise SentinelError(
                "IP esta na allowlist da configuracao; remova-o da allowlist "
                "antes de decidir bloquear"
            )
    with _database(ctx) as database:
        suspect = SuspectRepository(database).decide(
            source_ip, status, note or f"decisao manual: {status}"
        )
    labels = {
        "blocked": "BLOQUEAR",
        "allowed": "PERMITIR",
        "ignored": "IGNORAR",
        "pending": "VOLTAR PARA PENDENTE",
        "allowlisted": "ALLOWLIST",
    }
    ctx.console.success(
        f"{source_ip}: decisao registrada = {labels.get(status, status)} "
        f"({suspect.hits} interacao(oes) observada(s))"
    )
    if status == "blocked":
        ctx.console.warn(
            "nenhuma regra de firewall foi alterada. Esta versao apenas registra a decisao; "
            "a aplicacao real exigira adaptador homologado e modo enforce."
        )
    elif status == "allowed":
        ctx.console.info("o IP continua sendo observado; 'allowed' apenas registra sua decisao")
    elif status == "ignored":
        ctx.console.info("o IP continua no historico, mas marcado como ignorado")
    return 0


def cmd_bans_export(ctx: CommandContext, *, fmt: str, output: Path | None) -> int:
    if fmt not in {"json", "csv"}:
        raise SentinelError("formato invalido: use json ou csv")
    with _database(ctx) as database:
        suspects = SuspectRepository(database).list(limit=1000)
    records = [asdict(suspect) for suspect in suspects]
    if fmt == "json":
        content = json.dumps(
            {
                "generated_at": iso_utc(utc_now()),
                "count": len(records),
                "suspects": records,
            },
            ensure_ascii=False,
            indent=2,
        )
    else:
        buffer = io.StringIO(newline="")
        headers = [
            "source_ip",
            "hits",
            "max_severity",
            "status",
            "first_seen",
            "last_seen",
            "decision_at",
            "decision_note",
            "last_path",
        ]
        writer = csv.DictWriter(
            buffer, fieldnames=headers, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(records)
        content = buffer.getvalue()

    if output is None:
        print(content)
        return 0
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        content + ("" if content.endswith("\n") else "\n"),
        encoding="utf-8",
        newline="",
    )
    ctx.console.success(f"lista exportada para {output} ({len(records)} IP(s))")
    return 0


def cmd_simulate(ctx: CommandContext, *, source_ip: str = "10.10.10.66") -> int:
    source_ip = validate_ip(source_ip)
    ctx.paths.ensure()
    writer = SpoolWriter(ctx.paths.spool_file)
    now = utc_now()
    samples = [
        ("request", "GET", "/", 200, "Mozilla/5.0", "acesso a pagina inicial da camera"),
        ("honeypot_probe", "GET", "/.env", 404, "curl/8.5.0", "sondagem de arquivo sensivel"),
        (
            "credential_attempt",
            "POST",
            "/cgi-bin/sentinel_login.py",
            401,
            "python-requests/2.31",
            "tentativa de login (credenciais nao armazenadas)",
        ),
        (
            "attack_tool",
            "GET",
            "/admin/",
            200,
            "sqlmap/1.8",
            "User-Agent de ferramenta automatizada",
        ),
    ]
    for index, (event_type, method, path, status, user_agent, detail) in enumerate(samples):
        writer.write(
            Event(
                source_ip=source_ip,
                source_port=45_000 + index,
                honeypot_id="camera-01",
                profile="camera-http",
                protocol="http",
                event_type=event_type,
                timestamp_utc=now + timedelta(seconds=index),
                event_id=uuid.uuid4().hex[:20],
                method=method,
                path=path,
                status=status,
                user_agent=user_agent,
                detail=detail,
            )
        )
    with _database(ctx) as database:
        result = _collect(ctx, database)
        pending = SuspectRepository(database).pending_count()
    ctx.console.success(
        f"{len(samples)} interacoes de demonstracao gravadas para {source_ip} "
        f"({result.saved_events} evento(s) novo(s))"
    )
    ctx.console.info(f"veja a lista de ban: 'bans list' ({pending} IP(s) pendente(s))")
    return 0


def cmd_diagnostics(ctx: CommandContext) -> int:
    ctx.console.title("Diagnostico")
    checks: list[list[str]] = []

    checks.append(
        ["python", "ok" if sys.version_info >= (3, 11) else "alerta", sys.version.split()[0]]
    )
    checks.append(
        [
            "configuracao",
            "ok",
            str(ctx.config.source_path or "padroes internos"),
        ]
    )
    ctx.paths.ensure()
    probe = ctx.paths.data_dir / f".probe-{uuid.uuid4().hex[:8]}"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks.append(["diretorio de dados", "ok", str(ctx.paths.data_dir)])
    except OSError as exc:
        checks.append(["diretorio de dados", "falha", str(exc)])

    database_status = "falha"
    database_detail = str(ctx.paths.database)
    try:
        with _database(ctx) as database:
            row = database.connection.execute("PRAGMA quick_check").fetchone()
            database_status = "ok" if row is not None and str(row[0]) == "ok" else "alerta"
            database_detail = f"{ctx.paths.database} | quick_check={row[0] if row else '?'}"
    except StorageError as exc:
        database_detail = str(exc)
    checks.append(["banco sqlite", database_status, database_detail])

    spool_exists = ctx.paths.spool_file.is_file()
    checks.append(
        [
            "spool",
            "ok" if spool_exists else "alerta",
            str(ctx.paths.spool_file)
            + (f" ({ctx.paths.spool_file.stat().st_size} bytes)" if spool_exists else " (vazio)"),
        ]
    )
    snapshot = active_snapshot(ctx.paths.runtime_state)
    checks.append(
        [
            "agente",
            "ok" if snapshot is not None else "alerta",
            f"executando (pid {snapshot.pid})" if snapshot is not None else "parado",
        ]
    )
    checks.append(["perfis de honeypot", "ok", f"{len(list_profiles())} disponiveis"])
    checks.append(
        [
            "allowlist",
            "ok",
            f"{len(ctx.config.allowlist)} entrada(s): {', '.join(ctx.config.allowlist)}",
        ]
    )
    checks.append(
        [
            "modo de resposta",
            "ok" if ctx.config.mode in {"observe", "dry_run"} else "alerta",
            f"{ctx.config.mode} | firewall={ctx.config.firewall.adapter}",
        ]
    )
    ctx.console.table(["checagem", "resultado", "detalhe"], checks, max_widths=[22, 10, 70])
    failed = any(row[1] == "falha" for row in checks)
    return 1 if failed else 0


def cmd_version(ctx: CommandContext) -> int:
    print(f"SentinelIoT {__version__}")
    print(f"autor: {__author__}")
    print("honeypots defensivos para redes IoT")
    return 0


def dispatch(args: argparse.Namespace, ctx: CommandContext) -> int:
    command = getattr(args, "command", None)
    if command == "start":
        return cmd_start(ctx, foreground=bool(getattr(args, "foreground", False)))
    if command == "stop":
        return cmd_stop(ctx)
    if command == "status":
        return cmd_status(ctx)
    if command == "scan":
        return cmd_scan(ctx)
    if command == "daemon":
        return AgentRuntime(
            ctx.config, ctx.paths, console=bool(getattr(args, "foreground", False))
        ).run()
    if command == "version":
        return cmd_version(ctx)
    if command == "simulate":
        return cmd_simulate(ctx, source_ip=str(getattr(args, "ip", "10.10.10.66")))
    if command == "diagnostics":
        return cmd_diagnostics(ctx)

    if command in {"honeypots", "honeypot"}:
        subcommand = getattr(args, "honeypot_command", None) or "list"
        if subcommand == "available":
            return cmd_honeypots_available(ctx)
        if subcommand == "list":
            return cmd_honeypots_list(ctx)
        if subcommand == "add":
            return cmd_honeypots_add(
                ctx,
                profile_id=str(args.profile),
                instance_id=getattr(args, "instance_id", None),
                port=getattr(args, "port", None),
                host=getattr(args, "host", None),
            )
        if subcommand == "remove":
            return cmd_honeypots_remove(ctx, str(args.instance_id))
        raise SentinelError(f"subcomando de honeypots desconhecido: {subcommand}")

    if command == "events":
        subcommand = getattr(args, "events_command", None) or "list"
        if subcommand == "list":
            return cmd_events_list(
                ctx,
                limit=int(getattr(args, "limit", 20)),
                source_ip=getattr(args, "ip", None),
                event_type=getattr(args, "event_type", None),
            )
        if subcommand == "show":
            return cmd_events_show(ctx, str(args.event_id))
        raise SentinelError(f"subcomando de events desconhecido: {subcommand}")

    if command in {"bans", "ban"}:
        subcommand = getattr(args, "bans_command", None) or "list"
        if subcommand == "list":
            return cmd_bans_list(ctx, getattr(args, "status", None))
        if subcommand == "show":
            return cmd_bans_show(ctx, str(args.ip))
        if subcommand == "block":
            return cmd_ban_decide(
                ctx, str(args.ip), status="blocked", note=str(getattr(args, "note", ""))
            )
        if subcommand == "allow":
            return cmd_ban_decide(
                ctx, str(args.ip), status="allowed", note=str(getattr(args, "note", ""))
            )
        if subcommand == "ignore":
            return cmd_ban_decide(
                ctx, str(args.ip), status="ignored", note=str(getattr(args, "note", ""))
            )
        if subcommand == "reset":
            return cmd_ban_decide(
                ctx, str(args.ip), status="pending", note=str(getattr(args, "note", ""))
            )
        if subcommand == "export":
            output = getattr(args, "output", None)
            return cmd_bans_export(
                ctx,
                fmt=str(getattr(args, "format", "json")),
                output=Path(output) if output else None,
            )
        raise SentinelError(f"subcomando de bans desconhecido: {subcommand}")

    raise SentinelError(f"comando desconhecido: {command}")
