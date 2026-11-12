"""Validacoes estritas usadas pela CLI, pelo collector e pelas iscas."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Sequence

from sentineliot.core.errors import SentinelError

IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

PROTECTED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
)


def parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Converte um IP literal em objeto ipaddress, ou retorna None."""
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def validate_ip(value: str) -> str:
    """Valida e normaliza um IP literal."""
    address = parse_ip(value)
    if address is None:
        raise SentinelError(f"IP invalido: {value!r}")
    return str(address)


def validate_cidr(value: str) -> str:
    """Valida e normaliza um IP ou CIDR da allowlist."""
    candidate = value.strip()
    if not candidate:
        raise SentinelError("CIDR vazio")
    try:
        return str(ipaddress.ip_network(candidate, strict=False))
    except ValueError as exc:
        raise SentinelError(f"IP/CIDR invalido: {value!r}") from exc


def is_allowlisted(source_ip: str, entries: Sequence[str]) -> bool:
    """Retorna True quando o IP pertence a algum IP/CIDR da allowlist."""
    address = parse_ip(source_ip)
    if address is None:
        return False
    for entry in entries:
        try:
            network = ipaddress.ip_network(entry.strip(), strict=False)
        except ValueError:
            continue
        if address.version == network.version and address in network:
            return True
    return False


def is_blockable(source_ip: str) -> tuple[bool, str]:
    """Impede decisoes de bloqueio contra faixas protegidas."""
    address = parse_ip(source_ip)
    if address is None:
        return False, "endereco invalido"
    if address.is_unspecified:
        return False, "endereco indefinido"
    for network in PROTECTED_NETWORKS:
        if address.version == network.version and address in network:
            return False, "faixa protegida (loopback, link-local, multicast ou reservada)"
    return True, ""


def validate_port(port: int) -> int:
    """Valida uma porta TCP utilizavel por uma isca."""
    if not 1 <= port <= 65535:
        raise SentinelError(f"porta invalida: {port} (use 1-65535)")
    return port


def validate_identifier(value: str) -> str:
    """Valida o identificador de uma instancia de honeypot."""
    candidate = value.strip()
    if not IDENTIFIER_RE.fullmatch(candidate):
        raise SentinelError(
            "identificador invalido: use 1-32 caracteres [A-Za-z0-9_-], "
            "comecando por letra ou numero"
        )
    return candidate


def safe_text(value: object, limit: int) -> str:
    """Remove controles e trunca texto antes de persistir."""
    text = str(value) if value is not None else ""
    text = CONTROL_RE.sub(" ", text).strip()
    if len(text) > limit:
        return text[: limit - 1] + "\u2026"
    return text
