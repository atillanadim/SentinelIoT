"""Testes do estado persistido das iscas."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentineliot.core.config import Config
from sentineliot.core.errors import HoneypotError
from sentineliot.honeypot.profiles import get_profile, list_profiles
from sentineliot.honeypot.state import (
    HoneypotInstance,
    default_instances,
    load_instances,
    save_instances,
    validate_instances,
)


def test_catalog_has_expected_profiles() -> None:
    ids = {profile.id for profile in list_profiles()}
    assert {"camera-http", "router-admin", "ssh-banner", "telnet-iot"} <= ids
    assert get_profile("camera-http").protocol == "http"
    assert get_profile("telnet-iot").protocol == "telnet"


def test_default_instances_follow_config() -> None:
    instances = default_instances(Config())

    assert len(instances) == 1
    assert instances[0].id == "camera-01"
    assert instances[0].profile == "camera-http"
    assert instances[0].endpoint == "127.0.0.1:8080"


def test_state_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "honeypots.json"
    expected = [
        HoneypotInstance(id="camera-01", profile="camera-http", host="127.0.0.1", port=8080),
        HoneypotInstance(id="ssh-01", profile="ssh-banner", host="127.0.0.1", port=2222),
    ]

    save_instances(path, expected)
    loaded = load_instances(path, Config())

    assert loaded == expected


def test_duplicate_id_is_rejected() -> None:
    instances = [
        HoneypotInstance(id="same", profile="camera-http", host="127.0.0.1", port=8080),
        HoneypotInstance(id="same", profile="router-admin", host="127.0.0.1", port=8081),
    ]

    with pytest.raises(HoneypotError, match="duplicado"):
        validate_instances(instances)


def test_duplicate_endpoint_is_rejected() -> None:
    instances = [
        HoneypotInstance(id="one", profile="camera-http", host="127.0.0.1", port=8080),
        HoneypotInstance(id="two", profile="router-admin", host="127.0.0.1", port=8080),
    ]

    with pytest.raises(HoneypotError, match="endpoint duplicado"):
        validate_instances(instances)


def test_invalid_profile_in_state_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "honeypots.json"
    path.write_text(
        '{"version": 1, "instances": ['
        '{"id": "bad", "profile": "unknown", "host": "127.0.0.1", "port": 8080}]}',
        encoding="utf-8",
    )

    with pytest.raises(HoneypotError, match="perfil desconhecido"):
        load_instances(path, Config())


def test_corrupted_state_raises(tmp_path: Path) -> None:
    path = tmp_path / "honeypots.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(HoneypotError, match="estado de honeypots invalido"):
        load_instances(path, Config())
