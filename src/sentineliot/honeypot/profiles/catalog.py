"""Catalogo de perfis de honeypot disponiveis."""

from __future__ import annotations

from dataclasses import dataclass

from sentineliot.core.errors import HoneypotError


@dataclass(frozen=True)
class HoneypotProfile:
    id: str
    display_name: str
    protocol: str
    default_port: int
    description: str
    banner: str = ""


PROFILES: tuple[HoneypotProfile, ...] = (
    HoneypotProfile(
        id="camera-http",
        display_name="Camera IP simulada",
        protocol="http",
        default_port=8080,
        description="Painel, login, configuracao e API de uma camera IP generica.",
    ),
    HoneypotProfile(
        id="router-admin",
        display_name="Painel de roteador",
        protocol="http",
        default_port=8081,
        description="Tela de login e area administrativa de um roteador domestico.",
    ),
    HoneypotProfile(
        id="ssh-banner",
        display_name="SSH corporativo",
        protocol="ssh",
        default_port=2222,
        description="Banner SSH falso; registra conexao e tentativa de handshake.",
        banner="SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6",
    ),
    HoneypotProfile(
        id="telnet-iot",
        display_name="Telnet de dispositivo IoT",
        protocol="telnet",
        default_port=2323,
        description="Prompt de login Telnet falso; nao armazena credenciais.",
        banner="\r\nSentinelOS v1.0 (build 2024)\r\nlogin: ",
    ),
)

PROFILES_BY_ID: dict[str, HoneypotProfile] = {profile.id: profile for profile in PROFILES}


def get_profile(profile_id: str) -> HoneypotProfile:
    profile = PROFILES_BY_ID.get(profile_id)
    if profile is None:
        available = ", ".join(profile.id for profile in PROFILES)
        raise HoneypotError(f"perfil desconhecido: {profile_id}. Disponiveis: {available}")
    return profile


def list_profiles() -> tuple[HoneypotProfile, ...]:
    return PROFILES
