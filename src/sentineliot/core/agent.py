"""Runtime do agente: iscas, coleta continua e estado do daemon."""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Callable, Sequence
from pathlib import Path

from sentineliot.core.config import Config
from sentineliot.core.errors import HoneypotError
from sentineliot.core.paths import RuntimePaths
from sentineliot.core.runtime import new_snapshot, remove_runtime, write_runtime
from sentineliot.events.collector import EventCollector
from sentineliot.honeypot.manager import HoneypotManager
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.honeypot.state import load_instances
from sentineliot.storage.database import Database

LOGGER = logging.getLogger("sentineliot.agent")


def configure_logging(log_file: Path, console: bool) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger("sentineliot")
    root.setLevel(logging.INFO)
    root.handlers.clear()
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)


class AgentRuntime:
    def __init__(self, config: Config, paths: RuntimePaths, *, console: bool = False) -> None:
        self.config = config
        self.paths = paths
        self.console = console
        self._stop = threading.Event()

    def run(self) -> int:
        self.paths.ensure()
        configure_logging(self.paths.log_file, self.console)
        database = Database(self.paths.database)
        writer = SpoolWriter(self.paths.spool_file)
        manager = HoneypotManager(writer)
        collector = EventCollector(database, self.paths.spool_file, self.config.allowlist)
        self._install_signal_handlers()

        try:
            instances = load_instances(self.paths.honeypots_state, self.config)
            errors = manager.sync(instances)
            for error in errors:
                LOGGER.error("%s", error)
            if instances and not manager.running():
                raise HoneypotError("nenhuma isca conseguiu iniciar; verifique portas e permissoes")
            if not instances:
                LOGGER.warning("nenhuma isca configurada; apenas coleta sera executada")

            write_runtime(
                self.paths.runtime_state,
                new_snapshot(
                    os.getpid(), self.config.mode, self.config.source_path, manager.running()
                ),
            )
            database.audit(
                "daemon",
                "start",
                "agent",
                "ok",
                f"modo={self.config.mode}; iscas={len(manager.running())}",
            )
            LOGGER.info(
                "agente iniciado modo=%s iscas=%d spool=%s",
                self.config.mode,
                len(manager.running()),
                self.paths.spool_file,
            )
            self._loop(manager, collector, database)
        except KeyboardInterrupt:
            LOGGER.info("interrupcao recebida")
        finally:
            manager.stop_all()
            database.audit("daemon", "stop", "agent", "ok", "encerrado")
            database.close()
            remove_runtime(self.paths.runtime_state)
            LOGGER.info("agente encerrado")
        return 0

    def request_stop(self) -> None:
        self._stop.set()

    def _loop(
        self,
        manager: HoneypotManager,
        collector: EventCollector,
        database: Database,
    ) -> None:
        state_mtime = self._state_mtime()
        while not self._stop.is_set():
            result = collector.collect()
            if result.saved_events:
                LOGGER.info(
                    "coleta: %d evento(s), %d IP(s) novo(s), %d duplicado(s), %d invalido(s)",
                    result.saved_events,
                    result.new_ips,
                    result.duplicate_events,
                    result.malformed_lines,
                )
            current_mtime = self._state_mtime()
            if current_mtime != state_mtime:
                state_mtime = current_mtime
                try:
                    instances = load_instances(self.paths.honeypots_state, self.config)
                except HoneypotError as exc:
                    LOGGER.error("estado de honeypots invalido: %s", exc)
                else:
                    for error in manager.sync(instances):
                        LOGGER.error("%s", error)
                    write_runtime(
                        self.paths.runtime_state,
                        new_snapshot(
                            os.getpid(),
                            self.config.mode,
                            self.config.source_path,
                            manager.running(),
                        ),
                    )
                    LOGGER.info("iscas reconfiguradas: %d ativa(s)", len(manager.running()))
            self._stop.wait(self.config.agent.poll_interval_seconds)
        database.audit("daemon", "stop", "agent", "signal", "pedido de encerramento")

    def _state_mtime(self) -> int:
        try:
            return self.paths.honeypots_state.stat().st_mtime_ns
        except OSError:
            return 0

    def _install_signal_handlers(self) -> None:
        def handler(_signum: int, _frame: object) -> None:
            self._stop.set()

        signals: Sequence[int] = (signal.SIGINT,)
        if hasattr(signal, "SIGTERM"):
            signals = (*signals, signal.SIGTERM)
        for signum in signals:
            try:
                _install(signum, handler)
            except (OSError, ValueError):
                continue


def _install(signum: int, handler: Callable[[int, object], None]) -> None:
    signal.signal(signum, handler)
