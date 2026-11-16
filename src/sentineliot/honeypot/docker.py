"""Integracao minima com o Docker CLI para o runtime em container."""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Sequence
from typing import Protocol

from sentineliot.core.errors import HoneypotError

LOGGER = logging.getLogger("sentineliot.honeypot")
DEFAULT_TIMEOUT = 60.0


class DockerBackend(Protocol):
    """Operacoes do Docker usadas pelo gerenciador de iscas em container."""

    def available(self) -> bool: ...

    def ensure_network(self, name: str) -> None: ...

    def create_container(self, args: Sequence[str]) -> None: ...

    def list_managed(self, label: str) -> list[str]: ...

    def remove_container(self, name: str) -> None: ...


class DockerClient:
    """Executa comandos do Docker CLI sem shell, com argumentos em lista."""

    def __init__(self, binary: str = "docker", timeout: float = DEFAULT_TIMEOUT) -> None:
        self.binary = binary
        self.timeout = timeout

    def _execute(
        self, args: Sequence[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        command = [self.binary, *args]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise HoneypotError(f"falha ao executar o Docker: {exc}") from exc
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise HoneypotError(f"docker {' '.join(args)} falhou: {detail}")
        return result

    def available(self) -> bool:
        if shutil.which(self.binary) is None:
            return False
        result = self._execute(["version", "--format", "{{.Server.Version}}"], check=False)
        return result.returncode == 0

    def ensure_network(self, name: str) -> None:
        inspect = self._execute(["network", "inspect", name], check=False)
        if inspect.returncode == 0:
            return
        self._execute(
            ["network", "create", "--internal", "--label", "sentineliot.managed=true", name]
        )

    def create_container(self, args: Sequence[str]) -> None:
        self._execute(["run", *args])

    def list_managed(self, label: str) -> list[str]:
        result = self._execute(
            ["ps", "--filter", f"label={label}", "--format", "{{.Names}}"],
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def remove_container(self, name: str) -> None:
        self._execute(["rm", "--force", name], check=False)
