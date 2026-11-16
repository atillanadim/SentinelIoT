"""Runtime de honeypots em containers Docker isolados.

O agente continua fora do container: ele so cria, observa e remove containers.
A isca escreve o mesmo spool JSONL (via volume) consumido pelo coletor, de modo
que o contrato de eventos e lista de ban permanece identico ao runtime local.
"""

from __future__ import annotations

import logging
import os

from sentineliot.core.config import Config
from sentineliot.core.errors import HoneypotError
from sentineliot.core.paths import RuntimePaths
from sentineliot.honeypot.docker import DockerBackend, DockerClient
from sentineliot.honeypot.profiles import get_profile
from sentineliot.honeypot.servers import RunningHoneypot
from sentineliot.honeypot.state import HoneypotInstance

LOGGER = logging.getLogger("sentineliot.honeypot")
MANAGED_LABEL = "sentineliot.managed=true"
CONTAINER_PREFIX = "sentineliot-"
SPOOL_DIR_IN_CONTAINER = "/spool"
SPOOL_FILE_IN_CONTAINER = "/spool/honeypot.jsonl"
TMPFS_SIZE = "8m"


class DockerHoneypotManager:
    """Aproxima o estado desejado das iscas de containers em execucao."""

    def __init__(
        self,
        config: Config,
        paths: RuntimePaths,
        docker: DockerBackend | None = None,
    ) -> None:
        self.config = config
        self.paths = paths
        self.docker: DockerBackend = docker if docker is not None else DockerClient()
        self._running: dict[str, RunningHoneypot] = {}
        self._specs: dict[str, tuple[str, int, str]] = {}

    def sync(self, instances: list[HoneypotInstance]) -> list[str]:
        errors: list[str] = []
        if not self.docker.available():
            return [
                "runtime docker indisponivel: verifique o CLI 'docker' e o daemon "
                "antes de iniciar o agente"
            ]
        try:
            self.docker.ensure_network(self.config.honeypot.network)
        except HoneypotError as exc:
            return [str(exc)]

        desired = {instance.id: instance for instance in instances}

        keep: set[str] = set()
        for instance_id in list(self._running):
            wanted = desired.get(instance_id)
            if wanted is None or self._specs.get(instance_id) != self._spec(wanted):
                self._remove(instance_id)
            else:
                keep.add(self._container_name(instance_id))

        # Remove containers gerenciados que nao pertencem ao estado atual.
        for name in self.docker.list_managed(MANAGED_LABEL):
            if name not in keep:
                self.docker.remove_container(name)

        for instance_id, instance in desired.items():
            if instance_id in self._running:
                continue
            try:
                self.docker.create_container(self._run_args(instance))
            except HoneypotError as exc:
                errors.append(str(exc))
                LOGGER.error("falha ao iniciar %s: %s", instance_id, exc)
                continue
            profile = get_profile(instance.profile)
            self._running[instance_id] = RunningHoneypot(
                id=instance.id,
                profile=profile.id,
                host=instance.host,
                port=instance.port,
                protocol=profile.protocol,
            )
            self._specs[instance_id] = self._spec(instance)
            LOGGER.info(
                "honeypot %s (%s) em container %s",
                instance_id,
                profile.id,
                self._container_name(instance_id),
            )

        return errors

    def running(self) -> list[RunningHoneypot]:
        return list(self._running.values())

    def running_ids(self) -> set[str]:
        return set(self._running)

    def stop_all(self) -> None:
        for instance_id in list(self._running):
            self._remove(instance_id)
        for name in self.docker.list_managed(MANAGED_LABEL):
            self.docker.remove_container(name)
        self._running.clear()
        self._specs.clear()

    def _remove(self, instance_id: str) -> None:
        self.docker.remove_container(self._container_name(instance_id))
        self._running.pop(instance_id, None)
        self._specs.pop(instance_id, None)

    @staticmethod
    def _container_name(instance_id: str) -> str:
        return f"{CONTAINER_PREFIX}{instance_id}"

    @staticmethod
    def _spec(instance: HoneypotInstance) -> tuple[str, int, str]:
        return (instance.profile, instance.port, instance.host)

    def _container_user(self) -> str:
        configured = self.config.honeypot.container_user.strip()
        if configured:
            return configured
        getuid = getattr(os, "getuid", None)
        getgid = getattr(os, "getgid", None)
        if callable(getuid) and callable(getgid):
            return f"{getuid()}:{getgid()}"
        return ""

    def _run_args(self, instance: HoneypotInstance) -> list[str]:
        honeypot = self.config.honeypot
        args = [
            "--detach",
            "--name",
            self._container_name(instance.id),
            "--label",
            MANAGED_LABEL,
            "--label",
            f"sentineliot.honeypot={instance.id}",
            "--label",
            f"sentineliot.profile={instance.profile}",
            "--network",
            honeypot.network,
            "--publish",
            f"{instance.host}:{instance.port}:{instance.port}",
            "--env",
            f"SENTINELIOT_HONEYPOT_ID={instance.id}",
            "--env",
            f"SENTINELIOT_HONEYPOT_PROFILE={instance.profile}",
            "--env",
            f"SENTINELIOT_HONEYPOT_PORT={instance.port}",
            "--env",
            f"SENTINELIOT_SPOOL_FILE={SPOOL_FILE_IN_CONTAINER}",
            "--volume",
            f"{self.paths.spool_dir}:{SPOOL_DIR_IN_CONTAINER}",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(honeypot.pids_limit),
            "--memory",
            honeypot.memory_limit,
            "--cpus",
            honeypot.cpu_limit,
        ]
        if honeypot.read_only:
            args += ["--read-only", "--tmpfs", f"/tmp:size={TMPFS_SIZE},mode=1777"]
        user = self._container_user()
        if user:
            args += ["--user", user]
        args.append(honeypot.image)
        return args
