"""Testes de carregamento e validacao da configuracao."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentineliot.core.config import Config, load_config
from sentineliot.core.errors import ConfigurationError


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_defaults_are_safe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENTINELIOT_CONFIG", raising=False)

    config = load_config()

    assert isinstance(config, Config)
    assert config.mode == "observe"
    assert config.firewall.adapter == "dry_run"
    assert config.firewall.enforce_enabled is False
    assert "127.0.0.1/32" in config.allowlist


def test_loads_values_and_normalizes_allowlist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SENTINELIOT_CONFIG", raising=False)
    path = _write(
        tmp_path / "lab.yaml",
        """
app:
  environment: lab
agent:
  mode: dry_run
  poll_interval_seconds: 3
  data_dir: ./dados
honeypot:
  publish_host: 127.0.0.1
  listen_port: 8082
allowlist:
  - 10.0.0.0/8
  - 10.1.2.3
""",
    )

    config = load_config(path)

    assert config.mode == "dry_run"
    assert config.agent.poll_interval_seconds == 3
    assert config.honeypot.listen_port == 8082
    assert config.allowlist == ("10.0.0.0/8", "10.1.2.3/32")
    assert config.source_path == path


def test_missing_config_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="nao encontrado"):
        load_config(tmp_path / "missing.yaml")


def test_invalid_mode_raises(tmp_path: Path) -> None:
    path = _write(tmp_path / "bad.yaml", "agent:\n  mode: aggressive\n")
    with pytest.raises(ConfigurationError, match="agent.mode"):
        load_config(path)


def test_enforce_requires_explicit_flag(tmp_path: Path) -> None:
    path = _write(tmp_path / "bad.yaml", "agent:\n  mode: enforce\n")
    with pytest.raises(ConfigurationError, match="enforce_enabled"):
        load_config(path)


def test_nftables_requires_explicit_flag(tmp_path: Path) -> None:
    path = _write(tmp_path / "bad.yaml", "firewall:\n  adapter: nftables\n")
    with pytest.raises(ConfigurationError, match="nftables"):
        load_config(path)


def test_invalid_allowlist_raises(tmp_path: Path) -> None:
    path = _write(tmp_path / "bad.yaml", "allowlist:\n  - not-a-network\n")
    with pytest.raises(ConfigurationError, match="IP/CIDR invalido"):
        load_config(path)


def test_docker_runtime_is_parsed(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "docker.yaml",
        """
honeypot:
  runtime: docker
  image: sentineliot-honeypot:test
  network: sentineliot-lab
  cpu_limit: "0.5"
  memory_limit: 256m
  pids_limit: 32
  read_only: true
  container_user: "1000:1000"
""",
    )

    config = load_config(path)

    assert config.honeypot.runtime == "docker"
    assert config.honeypot.image == "sentineliot-honeypot:test"
    assert config.honeypot.memory_limit == "256m"
    assert config.honeypot.pids_limit == 32
    assert config.honeypot.container_user == "1000:1000"


def test_invalid_runtime_raises(tmp_path: Path) -> None:
    path = _write(tmp_path / "bad.yaml", "honeypot:\n  runtime: kubernetes\n")
    with pytest.raises(ConfigurationError, match="honeypot.runtime"):
        load_config(path)


@pytest.mark.parametrize(
    ("snippet", "match"),
    [
        ("runtime: docker\n  cpu_limit: zero", "cpu_limit"),
        ("runtime: docker\n  memory_limit: many", "memory_limit"),
        ("runtime: docker\n  pids_limit: 0", "pids_limit"),
        ("runtime: docker\n  network: 'bad network'", "network"),
        ("runtime: docker\n  container_user: root", "container_user"),
    ],
)
def test_invalid_docker_settings_raise(tmp_path: Path, snippet: str, match: str) -> None:
    path = _write(tmp_path / "bad.yaml", f"honeypot:\n  {snippet}\n")
    with pytest.raises(ConfigurationError, match=match):
        load_config(path)
