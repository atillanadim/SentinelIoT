"""Carregamento e validacao da configuracao YAML."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from sentineliot.core.errors import ConfigurationError, SentinelError
from sentineliot.security.validation import validate_cidr, validate_ip, validate_port

VALID_MODES = ("observe", "dry_run", "enforce")
VALID_ADAPTERS = ("dry_run", "nftables")
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
VALID_HONEYPOT_RUNTIMES = ("local", "docker")
DOCKER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")
DOCKER_MEMORY_RE = re.compile(r"^[0-9]+[bkmgBKMG]?$")
DOCKER_USER_RE = re.compile(r"^[0-9]+(:[0-9]+)?$")

DEFAULT_ALLOWLIST = ("127.0.0.1/32", "::1/128")


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _text(data: Mapping[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    if value is None:
        return default
    return str(value).strip()


def _integer(data: Mapping[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{key} deve ser um numero inteiro") from exc


def _boolean(data: Mapping[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1", "on"}:
            return True
        if lowered in {"false", "no", "0", "off"}:
            return False
    raise ConfigurationError(f"{key} deve ser true ou false")


def _path(data: Mapping[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    return str(value).strip() if value is not None else default


@dataclass(frozen=True)
class AppSettings:
    name: str = "sentineliot"
    environment: str = "lab"
    log_level: str = "INFO"


@dataclass(frozen=True)
class AgentSettings:
    mode: str = "observe"
    poll_interval_seconds: int = 2
    data_dir: str = "./data"


@dataclass(frozen=True)
class HoneypotSettings:
    enabled: bool = True
    profile: str = "camera-http"
    listen_port: int = 8080
    publish_host: str = "127.0.0.1"
    runtime: str = "local"
    image: str = "sentineliot-honeypot:0.1.0"
    network: str = "sentineliot-lab"
    cpu_limit: str = "0.25"
    memory_limit: str = "128m"
    pids_limit: int = 64
    read_only: bool = True
    container_user: str = ""


@dataclass(frozen=True)
class DetectionSettings:
    event_retention_days: int = 90
    rate_window_seconds: int = 60
    max_events_per_source: int = 20


@dataclass(frozen=True)
class FirewallSettings:
    adapter: str = "dry_run"
    enforce_enabled: bool = False
    default_ttl_seconds: int = 900
    max_ttl_seconds: int = 3600
    max_active_blocks: int = 20
    max_new_blocks_per_hour: int = 10


@dataclass(frozen=True)
class NotificationSettings:
    local_enabled: bool = True
    external_enabled: bool = False


@dataclass(frozen=True)
class Config:
    app: AppSettings = field(default_factory=AppSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    honeypot: HoneypotSettings = field(default_factory=HoneypotSettings)
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    firewall: FirewallSettings = field(default_factory=FirewallSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST
    source_path: Path | None = None

    @property
    def mode(self) -> str:
        return self.agent.mode


def _default_path() -> Path | None:
    env_path = os.environ.get("SENTINELIOT_CONFIG", "").strip()
    if env_path:
        return Path(env_path)
    for candidate in (Path("config/config.yaml"), Path("config/config.example.yaml")):
        if candidate.is_file():
            return candidate
    return None


def _read_yaml(path: Path) -> Mapping[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"nao foi possivel ler a configuracao: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML invalido em {path}: {exc}") from exc
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ConfigurationError(f"a raiz da configuracao deve ser um mapa: {path}")
    return raw


def load_config(path: Path | None = None) -> Config:
    """Carrega a configuracao, aplicando defaults seguros e validacao estrita."""
    selected = path if path is not None else _default_path()
    if selected is not None and not selected.is_file():
        raise ConfigurationError(f"arquivo de configuracao nao encontrado: {selected}")

    raw: Mapping[str, Any] = _read_yaml(selected) if selected is not None else {}

    app_raw = _mapping(raw.get("app"))
    agent_raw = _mapping(raw.get("agent"))
    honeypot_raw = _mapping(raw.get("honeypot"))
    detection_raw = _mapping(raw.get("detection"))
    firewall_raw = _mapping(raw.get("firewall"))
    notifications_raw = _mapping(raw.get("notifications"))

    app = AppSettings(
        name=_text(app_raw, "name", "sentineliot"),
        environment=_text(app_raw, "environment", "lab").lower(),
        log_level=_text(app_raw, "log_level", "INFO").upper(),
    )
    agent = AgentSettings(
        mode=_text(agent_raw, "mode", "observe").lower(),
        poll_interval_seconds=_integer(agent_raw, "poll_interval_seconds", 2),
        data_dir=_path(agent_raw, "data_dir", "./data"),
    )
    honeypot = HoneypotSettings(
        enabled=_boolean(honeypot_raw, "enabled", True),
        profile=_text(honeypot_raw, "profile", "camera-http"),
        listen_port=_integer(honeypot_raw, "listen_port", 8080),
        publish_host=_text(honeypot_raw, "publish_host", "127.0.0.1"),
        runtime=_text(honeypot_raw, "runtime", "local").lower(),
        image=_text(honeypot_raw, "image", "sentineliot-honeypot:0.1.0"),
        network=_text(honeypot_raw, "network", "sentineliot-lab"),
        cpu_limit=_text(honeypot_raw, "cpu_limit", "0.25"),
        memory_limit=_text(honeypot_raw, "memory_limit", "128m"),
        pids_limit=_integer(honeypot_raw, "pids_limit", 64),
        read_only=_boolean(honeypot_raw, "read_only", True),
        container_user=_text(honeypot_raw, "container_user", ""),
    )
    detection = DetectionSettings(
        event_retention_days=_integer(detection_raw, "event_retention_days", 90),
        rate_window_seconds=_integer(detection_raw, "rate_window_seconds", 60),
        max_events_per_source=_integer(detection_raw, "max_events_per_source", 20),
    )
    firewall = FirewallSettings(
        adapter=_text(firewall_raw, "adapter", "dry_run").lower(),
        enforce_enabled=_boolean(firewall_raw, "enforce_enabled", False),
        default_ttl_seconds=_integer(firewall_raw, "default_ttl_seconds", 900),
        max_ttl_seconds=_integer(firewall_raw, "max_ttl_seconds", 3600),
        max_active_blocks=_integer(firewall_raw, "max_active_blocks", 20),
        max_new_blocks_per_hour=_integer(firewall_raw, "max_new_blocks_per_hour", 10),
    )
    notifications = NotificationSettings(
        local_enabled=_boolean(notifications_raw, "local_enabled", True),
        external_enabled=_boolean(notifications_raw, "external_enabled", False),
    )

    allowlist_values = _sequence(raw.get("allowlist"))
    allowlist: list[str] = []
    for value in allowlist_values:
        try:
            allowlist.append(validate_cidr(str(value)))
        except SentinelError as exc:
            raise ConfigurationError(str(exc)) from exc
    if not allowlist:
        allowlist = list(DEFAULT_ALLOWLIST)

    config = Config(
        app=app,
        agent=agent,
        honeypot=honeypot,
        detection=detection,
        firewall=firewall,
        notifications=notifications,
        allowlist=tuple(dict.fromkeys(allowlist)),
        source_path=selected,
    )
    try:
        _validate(config)
    except SentinelError as exc:
        if isinstance(exc, ConfigurationError):
            raise
        raise ConfigurationError(str(exc)) from exc
    return config


def _validate(config: Config) -> None:
    if config.app.environment not in {"lab", "production"}:
        raise ConfigurationError("app.environment deve ser 'lab' ou 'production'")
    if config.app.log_level not in VALID_LOG_LEVELS:
        raise ConfigurationError(f"app.log_level invalido: {config.app.log_level}")
    if config.agent.mode not in VALID_MODES:
        raise ConfigurationError(f"agent.mode invalido: {config.agent.mode}")
    if not 1 <= config.agent.poll_interval_seconds <= 60:
        raise ConfigurationError("agent.poll_interval_seconds deve estar entre 1 e 60")

    validate_port(config.honeypot.listen_port)
    validate_ip(config.honeypot.publish_host)
    _validate_honeypot_runtime(config.honeypot)

    if config.detection.event_retention_days < 1:
        raise ConfigurationError("detection.event_retention_days deve ser >= 1")
    if config.detection.rate_window_seconds < 1:
        raise ConfigurationError("detection.rate_window_seconds deve ser >= 1")
    if config.detection.max_events_per_source < 1:
        raise ConfigurationError("detection.max_events_per_source deve ser >= 1")

    if config.firewall.adapter not in VALID_ADAPTERS:
        raise ConfigurationError(f"firewall.adapter invalido: {config.firewall.adapter}")
    if config.firewall.default_ttl_seconds < 60:
        raise ConfigurationError("firewall.default_ttl_seconds deve ser >= 60")
    if config.firewall.max_ttl_seconds < config.firewall.default_ttl_seconds:
        raise ConfigurationError("firewall.max_ttl_seconds deve ser >= default_ttl_seconds")
    if config.firewall.max_active_blocks < 1:
        raise ConfigurationError("firewall.max_active_blocks deve ser >= 1")
    if config.firewall.max_new_blocks_per_hour < 1:
        raise ConfigurationError("firewall.max_new_blocks_per_hour deve ser >= 1")
    if config.agent.mode == "enforce" and not config.firewall.enforce_enabled:
        raise ConfigurationError(
            "agent.mode=enforce exige firewall.enforce_enabled=true; "
            "o padrao seguro e observe ou dry_run"
        )
    if config.firewall.adapter == "nftables" and not config.firewall.enforce_enabled:
        raise ConfigurationError(
            "firewall.adapter=nftables exige firewall.enforce_enabled=true apos homologacao"
        )


def _validate_honeypot_runtime(honeypot: HoneypotSettings) -> None:
    if honeypot.runtime not in VALID_HONEYPOT_RUNTIMES:
        raise ConfigurationError(
            f"honeypot.runtime invalido: {honeypot.runtime}. "
            f"Use {' ou '.join(VALID_HONEYPOT_RUNTIMES)}"
        )
    if honeypot.runtime != "docker":
        return
    if not honeypot.image:
        raise ConfigurationError("honeypot.image e obrigatorio no runtime docker")
    if not DOCKER_NAME_RE.fullmatch(honeypot.network):
        raise ConfigurationError(
            "honeypot.network invalido: use ate 63 caracteres [A-Za-z0-9_.-], "
            "comecando por letra ou numero"
        )
    try:
        cpus = float(honeypot.cpu_limit)
    except ValueError as exc:
        raise ConfigurationError("honeypot.cpu_limit deve ser um numero") from exc
    if cpus <= 0:
        raise ConfigurationError("honeypot.cpu_limit deve ser maior que zero")
    if not DOCKER_MEMORY_RE.fullmatch(honeypot.memory_limit):
        raise ConfigurationError("honeypot.memory_limit invalido: use algo como 128m ou 1g")
    if honeypot.pids_limit < 1:
        raise ConfigurationError("honeypot.pids_limit deve ser >= 1")
    if honeypot.container_user and not DOCKER_USER_RE.fullmatch(honeypot.container_user):
        raise ConfigurationError(
            "honeypot.container_user invalido: use UID ou UID:GID numericos"
        )
