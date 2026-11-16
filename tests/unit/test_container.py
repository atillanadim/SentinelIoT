"""Testes do entrypoint de container e da selecao de runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentineliot.core.config import Config, HoneypotSettings
from sentineliot.core.errors import HoneypotError
from sentineliot.core.paths import RuntimePaths
from sentineliot.honeypot.container import config_from_env
from sentineliot.honeypot.docker_manager import DockerHoneypotManager
from sentineliot.honeypot.manager import HoneypotManager, create_honeypot_runtime
from sentineliot.honeypot.spool import SpoolWriter

VALID_ENV = {
    "SENTINELIOT_HONEYPOT_ID": "camera-01",
    "SENTINELIOT_HONEYPOT_PROFILE": "camera-http",
    "SENTINELIOT_HONEYPOT_PORT": "8080",
    "SENTINELIOT_SPOOL_FILE": "/spool/honeypot.jsonl",
}


def test_config_from_env_valid() -> None:
    config = config_from_env(VALID_ENV)

    assert config.honeypot_id == "camera-01"
    assert config.profile == "camera-http"
    assert config.port == 8080
    assert config.spool_file == Path("/spool/honeypot.jsonl")


@pytest.mark.parametrize("missing", sorted(VALID_ENV))
def test_config_from_env_requires_all_variables(missing: str) -> None:
    environ = {key: value for key, value in VALID_ENV.items() if key != missing}

    with pytest.raises(HoneypotError, match="ausentes"):
        config_from_env(environ)


def test_config_from_env_rejects_invalid_port() -> None:
    environ = {**VALID_ENV, "SENTINELIOT_HONEYPOT_PORT": "70000"}

    with pytest.raises(HoneypotError):
        config_from_env(environ)


def test_config_from_env_rejects_unknown_profile() -> None:
    environ = {**VALID_ENV, "SENTINELIOT_HONEYPOT_PROFILE": "nope"}

    with pytest.raises(HoneypotError, match="perfil desconhecido"):
        config_from_env(environ)


def test_create_runtime_selects_backend(tmp_path: Path) -> None:
    writer = SpoolWriter(tmp_path / "data" / "spool" / "honeypot.jsonl")

    local_config = Config(honeypot=HoneypotSettings(runtime="local"))
    local_paths = RuntimePaths.build(local_config, tmp_path / "local")
    assert isinstance(create_honeypot_runtime(local_config, local_paths, writer), HoneypotManager)

    docker_config = Config(honeypot=HoneypotSettings(runtime="docker"))
    docker_paths = RuntimePaths.build(docker_config, tmp_path / "docker")
    assert isinstance(
        create_honeypot_runtime(docker_config, docker_paths, writer),
        DockerHoneypotManager,
    )
