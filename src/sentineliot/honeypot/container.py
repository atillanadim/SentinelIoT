"""Entrypoint da isca executada dentro do container Docker.

O agente cria o container com variaveis de ambiente e um volume para o spool.
Esta entrada reutiliza os mesmos servidores e o mesmo spool do runtime local,
garantindo o mesmo contrato de eventos e lista de ban.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

from sentineliot.core.errors import HoneypotError, SentinelError
from sentineliot.honeypot.profiles import get_profile
from sentineliot.honeypot.servers import build_server
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.honeypot.state import HoneypotInstance
from sentineliot.security.validation import validate_identifier, validate_port

LOGGER = logging.getLogger("sentineliot.container")
BIND_HOST = "0.0.0.0"
REQUIRED_ENV = (
    "SENTINELIOT_HONEYPOT_ID",
    "SENTINELIOT_HONEYPOT_PROFILE",
    "SENTINELIOT_HONEYPOT_PORT",
    "SENTINELIOT_SPOOL_FILE",
)


@dataclass(frozen=True)
class ContainerConfig:
    honeypot_id: str
    profile: str
    port: int
    spool_file: Path


def config_from_env(environ: Mapping[str, str]) -> ContainerConfig:
    values = {key: environ.get(key, "").strip() for key in REQUIRED_ENV}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise HoneypotError("variaveis obrigatorias ausentes: " + ", ".join(sorted(missing)))
    try:
        port = validate_port(int(values["SENTINELIOT_HONEYPOT_PORT"]))
    except (ValueError, SentinelError) as exc:
        raise HoneypotError(
            f"SENTINELIOT_HONEYPOT_PORT invalida: {values['SENTINELIOT_HONEYPOT_PORT']!r}"
        ) from exc
    profile = get_profile(values["SENTINELIOT_HONEYPOT_PROFILE"])
    return ContainerConfig(
        honeypot_id=validate_identifier(values["SENTINELIOT_HONEYPOT_ID"]),
        profile=profile.id,
        port=port,
        spool_file=Path(values["SENTINELIOT_SPOOL_FILE"]),
    )


def main(environ: Mapping[str, str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    source = os.environ if environ is None else environ
    try:
        config = config_from_env(source)
    except SentinelError as exc:
        LOGGER.error("%s", exc)
        return 2

    profile = get_profile(config.profile)
    instance = HoneypotInstance(
        id=config.honeypot_id,
        profile=profile.id,
        host=BIND_HOST,
        port=config.port,
    )
    writer = SpoolWriter(config.spool_file)
    handle = build_server(instance, profile, writer)
    stop = threading.Event()

    def _handler(_signum: int, _frame: FrameType | None) -> None:
        stop.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, _handler)

    try:
        handle.start()
    except HoneypotError as exc:
        LOGGER.error("%s", exc)
        return 1

    LOGGER.info(
        "isca %s (%s) escutando em %s:%d",
        config.honeypot_id,
        profile.id,
        BIND_HOST,
        config.port,
    )
    stop.wait()
    handle.stop()
    LOGGER.info("isca %s encerrada", config.honeypot_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
