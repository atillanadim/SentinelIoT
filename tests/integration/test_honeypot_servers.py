"""Testes de integracao dos servidores-isca locais."""

from __future__ import annotations

import json
import socket
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

import pytest

from sentineliot.core.errors import HoneypotError
from sentineliot.events.models import Event
from sentineliot.honeypot.manager import HoneypotManager
from sentineliot.honeypot.profiles import get_profile
from sentineliot.honeypot.servers import HTTPHoneypot, TCPHoneypot
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.honeypot.state import HoneypotInstance


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_for(predicate: Callable[[], bool], timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _records(spool: Path) -> list[Event]:
    if not spool.is_file():
        return []
    events: list[Event] = []
    for line in spool.read_text(encoding="utf-8").splitlines():
        if line.strip():
            event = Event.from_record(json.loads(line))
            if event is not None:
                events.append(event)
    return events


def _recv_until(sock: socket.socket, marker: bytes, limit: int = 8192) -> bytes:
    data = b""
    while marker not in data and len(data) < limit:
        data += sock.recv(1024)
    return data


@pytest.fixture
def spool(tmp_path: Path) -> Path:
    return tmp_path / "spool" / "honeypot.jsonl"


def test_http_honeypot_records_attack_tool(spool: Path) -> None:
    port = _free_port()
    instance = HoneypotInstance(
        id="camera-test", profile="camera-http", host="127.0.0.1", port=port
    )
    handle = HTTPHoneypot(instance, get_profile("camera-http"), SpoolWriter(spool))
    handle.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/admin/",
            headers={"User-Agent": "sqlmap/1.8"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.status == 200
            assert b"SentinelCam" in response.read()
    finally:
        handle.stop()

    events = _records(spool)
    types = {event.event_type for event in events}
    assert "attack_tool" in types
    assert "honeypot_probe" in types
    assert all(event.source_ip == "127.0.0.1" for event in events)
    assert all(event.path == "/admin/" for event in events)
    assert any(event.user_agent == "sqlmap/1.8" for event in events)


def test_http_honeypot_rejects_occupied_port(spool: Path) -> None:
    port = _free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", port))
        blocker.listen(1)
        instance = HoneypotInstance(
            id="camera-test", profile="camera-http", host="127.0.0.1", port=port
        )
        handle = HTTPHoneypot(instance, get_profile("camera-http"), SpoolWriter(spool))

        with pytest.raises(HoneypotError, match="nao foi possivel abrir"):
            handle.start()


def test_telnet_honeypot_records_login_without_password(spool: Path) -> None:
    port = _free_port()
    instance = HoneypotInstance(
        id="telnet-test", profile="telnet-iot", host="127.0.0.1", port=port
    )
    handle = TCPHoneypot(instance, get_profile("telnet-iot"), SpoolWriter(spool))
    handle.start()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            client.settimeout(5)
            banner = _recv_until(client, b"login:")
            assert b"login:" in banner
            client.sendall(b"admin\n")
            prompt = _recv_until(client, b"Password:")
            assert b"Password:" in prompt
            client.sendall(b"segredo-nao-armazenado\n")
            answer = _recv_until(client, b"Login incorrect")
            assert b"Login incorrect" in answer
    finally:
        handle.stop()

    events = _records(spool)
    assert len(events) == 1
    assert events[0].event_type == "credential_attempt"
    assert events[0].protocol == "telnet"
    assert "segredo-nao-armazenado" not in events[0].detail


def test_ssh_honeypot_records_handshake(spool: Path) -> None:
    port = _free_port()
    instance = HoneypotInstance(
        id="ssh-test", profile="ssh-banner", host="127.0.0.1", port=port
    )
    handle = TCPHoneypot(instance, get_profile("ssh-banner"), SpoolWriter(spool))
    handle.start()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            client.settimeout(5)
            banner = _recv_until(client, b"SSH-2.0")
            assert banner.startswith(b"SSH-2.0-OpenSSH")
            client.sendall(b"SSH-2.0-TestClient\r\n")
            assert _wait_for(lambda: len(_records(spool)) == 1)
    finally:
        handle.stop()

    events = _records(spool)
    assert len(events) == 1
    assert events[0].event_type == "connection"
    assert events[0].protocol == "ssh"


def test_manager_starts_and_stops_instances(spool: Path) -> None:
    port = _free_port()
    instance = HoneypotInstance(
        id="router-test", profile="router-admin", host="127.0.0.1", port=port
    )
    manager = HoneypotManager(SpoolWriter(spool))
    try:
        assert manager.sync([instance]) == []
        assert manager.running_ids() == {"router-test"}

        assert manager.sync([]) == []
        assert manager.running_ids() == set()
    finally:
        manager.stop_all()
