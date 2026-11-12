"""Ciclo de vida das iscas em memoria."""

from __future__ import annotations

import logging

from sentineliot.core.errors import HoneypotError
from sentineliot.honeypot.profiles import get_profile
from sentineliot.honeypot.servers import RunningHoneypot, ServerHandle, build_server
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.honeypot.state import HoneypotInstance

LOGGER = logging.getLogger("sentineliot.honeypot")


class HoneypotManager:
    def __init__(self, writer: SpoolWriter) -> None:
        self.writer = writer
        self._servers: dict[str, ServerHandle] = {}

    def sync(self, instances: list[HoneypotInstance]) -> list[str]:
        """Aproxima o estado em memoria da lista persistida de instancias."""
        errors: list[str] = []
        desired = {instance.id: instance for instance in instances}

        for instance_id in list(self._servers):
            current = self._servers[instance_id].instance
            wanted = desired.get(instance_id)
            if wanted is None or wanted != current:
                try:
                    self._servers[instance_id].stop()
                except OSError as exc:
                    errors.append(f"falha ao parar {instance_id}: {exc}")
                del self._servers[instance_id]

        for instance_id, instance in desired.items():
            if instance_id in self._servers:
                continue
            profile = get_profile(instance.profile)
            handle = build_server(instance, profile, self.writer)
            try:
                handle.start()
            except HoneypotError as exc:
                errors.append(str(exc))
                LOGGER.error("falha ao iniciar %s: %s", instance_id, exc)
                continue
            self._servers[instance_id] = handle

        return errors

    def running(self) -> list[RunningHoneypot]:
        return [handle.running for handle in self._servers.values()]

    def running_ids(self) -> set[str]:
        return set(self._servers)

    def stop_all(self) -> None:
        for handle in list(self._servers.values()):
            try:
                handle.stop()
            except OSError as exc:
                LOGGER.warning("falha ao parar honeypot: %s", exc)
        self._servers.clear()
