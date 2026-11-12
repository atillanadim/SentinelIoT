"""Classificacao de interacoes HTTP em tipos de evento explicaveis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote_plus

ATTACK_TOOL_RE = re.compile(
    r"(sqlmap|nikto|hydra|medusa|nmap|masscan|gobuster|ffuf|dirb|dirbuster|"
    r"wpscan|nuclei|zaproxy|acunetix|openvas|nessus|whatweb|nuclei|zgrab|"
    r"python-requests|curl/|wget/|libwww-perl|masscan)",
    re.IGNORECASE,
)
INJECTION_RE = re.compile(
    r"(union\s+select|or\s+1\s*=\s*1|'\s*or\s*'|sleep\s*\(|benchmark\s*\(|"
    r"information_schema|\.\./|<\s*script|;\s*(cat|id|whoami|wget|curl)\b)",
    re.IGNORECASE,
)
SENSITIVE_PATH_RE = re.compile(
    r"(/admin|/camera|/api|/cgi-bin|/\.env|/\.git|/phpmyadmin|/server-status|"
    r"/wp-admin|/wp-login|/manager|/console|/login|/setup|/config)",
    re.IGNORECASE,
)
LOGIN_PATH_RE = re.compile(r"(login|signin|auth|token|session|cgi-bin)", re.IGNORECASE)


@dataclass(frozen=True)
class Signal:
    event_type: str
    detail: str


def classify_http(
    *,
    target: str,
    method: str,
    user_agent: str,
    status: int,
    is_post: bool,
) -> list[Signal]:
    """Gera um ou mais sinais para uma requisicao HTTP recebida."""
    path = target.split("?", 1)[0]
    decoded = unquote_plus(target)
    signals: list[Signal] = []

    if ATTACK_TOOL_RE.search(user_agent):
        signals.append(Signal("attack_tool", "User-Agent de ferramenta automatizada"))
    if INJECTION_RE.search(decoded):
        signals.append(Signal("injection_attempt", "padrao de injecao na URL"))
    if is_post and LOGIN_PATH_RE.search(decoded):
        signals.append(
            Signal("credential_attempt", "tentativa de login (credenciais nao armazenadas)")
        )
    if SENSITIVE_PATH_RE.search(path) and not any(
        signal.event_type == "credential_attempt" for signal in signals
    ):
        signals.append(Signal("honeypot_probe", "acesso a caminho sensivel da isca"))
    if status in {401, 403} and not any(
        signal.event_type == "credential_attempt" for signal in signals
    ):
        signals.append(Signal("auth_failure", f"HTTP {status} na isca"))
    if not signals:
        signals.append(Signal("request", "requisicao HTTP observada"))
    return signals
