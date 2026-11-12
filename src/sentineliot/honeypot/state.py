"""Estado persistido das instancias de honeypot configuradas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentineliot.core.config import Config
from sentineliot.core.errors import HoneypotError
from sentineliot.honeypot.profiles import get_profile
from sentineliot.security.validation import validate_identifier, validate_ip, validate_port

STATE_VERSION = 1


@dataclass(frozen=True)
class HoneypotInstance:
    id: str
    profile: str
    host: str
    port: int

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"

    def to_record(self) -> dict[str, object]:
        return {
            "id": self.id,
            "profile": self.profile,
            "host": self.host,
            "port": self.port,
        }

    @classmethod
    def from_record(cls, data: dict[str, Any]) -> HoneypotInstance:
        instance_id = validate_identifier(str(data.get("id", "")))
        profile = get_profile(str(data.get("profile", "")))
        host = validate_ip(str(data.get("host", "127.0.0.1")))
        try:
            port = validate_port(int(data.get("port", profile.default_port)))
        except (TypeError, ValueError) as exc:
            raise HoneypotError(f"porta invalida para {instance_id}") from exc
        return cls(id=instance_id, profile=profile.id, host=host, port=port)


def default_instances(config: Config) -> list[HoneypotInstance]:
    if not config.honeypot.enabled:
        return []
    profile_id = _map_legacy_profile(config.honeypot.profile)
    profile = get_profile(profile_id)
    instance_id = "camera-01" if profile.id == "camera-http" else f"{profile.id}-01"
    return [
        HoneypotInstance(
            id=validate_identifier(instance_id),
            profile=profile.id,
            host=validate_ip(config.honeypot.publish_host),
            port=validate_port(config.honeypot.listen_port or profile.default_port),
        )
    ]


def _map_legacy_profile(value: str) -> str:
    legacy = {
        "camera_simulator": "camera-http",
        "camera": "camera-http",
        "router": "router-admin",
        "ssh": "ssh-banner",
        "telnet": "telnet-iot",
    }
    return legacy.get(value, value)


def load_instances(path: Path, config: Config) -> list[HoneypotInstance]:
    if not path.is_file():
        instances = default_instances(config)
        save_instances(path, instances)
        return instances
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HoneypotError(f"estado de honeypots invalido em {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise HoneypotError(f"estado de honeypots invalido em {path}: raiz deve ser objeto")
    records = raw.get("instances", [])
    if not isinstance(records, list):
        raise HoneypotError(f"estado de honeypots invalido em {path}: instances deve ser lista")
    instances = [
        HoneypotInstance.from_record(record) for record in records if isinstance(record, dict)
    ]
    validate_instances(instances)
    return instances


def save_instances(path: Path, instances: list[HoneypotInstance]) -> None:
    validate_instances(instances)
    payload = {
        "version": STATE_VERSION,
        "instances": [instance.to_record() for instance in instances],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_instances(instances: list[HoneypotInstance]) -> None:
    ids: set[str] = set()
    endpoints: set[tuple[str, int]] = set()
    for instance in instances:
        if instance.id in ids:
            raise HoneypotError(f"identificador duplicado: {instance.id}")
        ids.add(instance.id)
        endpoint = (instance.host, instance.port)
        if endpoint in endpoints:
            raise HoneypotError(f"endpoint duplicado: {instance.host}:{instance.port}")
        endpoints.add(endpoint)
        get_profile(instance.profile)
