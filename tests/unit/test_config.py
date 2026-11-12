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
