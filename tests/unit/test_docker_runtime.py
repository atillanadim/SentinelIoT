"""Testes do runtime de honeypots em container (sem Docker real)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from sentineliot.core.config import Config, HoneypotSettings
from sentineliot.core.errors import HoneypotError
from sentineliot.core.paths import RuntimePaths
from sentineliot.honeypot.docker_manager import DockerHoneypotManager
from sentineliot.honeypot.state import HoneypotInstance


class FakeDocker:
    def __init__(self, available: bool = True, managed: Sequence[str] = ()) -> None:
        self._available = available
        self.networks: list[str] = []
        self.created: list[list[str]] = []
        self.removed: list[str] = []
        self.managed: list[str] = list(managed)

    def available(self) -> bool:
        return self._available

    def ensure_network(self, name: str) -> None:
        self.networks.append(name)

    def create_container(self, args: Sequence[str]) -> None:
        self.created.append(list(args))

    def list_managed(self, label: str) -> list[str]:
        return list(self.managed)

    def remove_container(self, name: str) -> None:
        self.removed.append(name)
        if name in self.managed:
            self.managed.remove(name)


def _manager(
    tmp_path: Path, fake: FakeDocker, **overrides: object
) -> DockerHoneypotManager:
    settings = HoneypotSettings(runtime="docker", **overrides)  # type: ignore[arg-type]
    config = Config(honeypot=settings)
    paths = RuntimePaths.build(config, tmp_path / "data")
    return DockerHoneypotManager(config, paths, docker=fake)


def _instance(instance_id: str = "camera-01", port: int = 8080) -> HoneypotInstance:
    return HoneypotInstance(
        id=instance_id, profile="camera-http", host="192.168.57.10", port=port
    )


def test_sync_starts_isolated_container(tmp_path: Path) -> None:
    fake = FakeDocker()
    manager = _manager(tmp_path, fake)

    assert manager.sync([_instance()]) == []

    assert fake.networks == ["sentineliot-lab"]
    assert len(fake.created) == 1
    args = fake.created[0]
    assert args[0] == "--detach"
    assert "--read-only" in args
    assert "--cap-drop" in args and "ALL" in args
    assert "no-new-privileges" in args
    assert "--pids-limit" in args
    assert "--memory" in args and "128m" in args
    assert "--cpus" in args and "0.25" in args
    assert "--network" in args and "sentineliot-lab" in args
    assert "--publish" in args and "192.168.57.10:8080:8080" in args
    assert "/var/run/docker.sock" not in " ".join(args)
    assert "--privileged" not in args
    assert args[-1] == "sentineliot-honeypot:0.1.0"
    running = manager.running()
    assert [item.id for item in running] == ["camera-01"]
    assert running[0].protocol == "http"


def test_sync_is_idempotent(tmp_path: Path) -> None:
    fake = FakeDocker()
    manager = _manager(tmp_path, fake)

    manager.sync([_instance()])
    manager.sync([_instance()])

    assert len(fake.created) == 1
    assert fake.removed == []


def test_sync_removes_orphan_containers(tmp_path: Path) -> None:
    fake = FakeDocker(managed=["sentineliot-old"])
    manager = _manager(tmp_path, fake)

    manager.sync([_instance()])

    assert "sentineliot-old" in fake.removed


def test_sync_recreates_when_spec_changes(tmp_path: Path) -> None:
    fake = FakeDocker()
    manager = _manager(tmp_path, fake)

    manager.sync([_instance(port=8080)])
    manager.sync([_instance(port=9090)])

    assert "sentineliot-camera-01" in fake.removed
    assert len(fake.created) == 2


def test_stop_all_removes_tracked_and_orphans(tmp_path: Path) -> None:
    fake = FakeDocker()
    manager = _manager(tmp_path, fake)
    manager.sync([_instance()])
    fake.managed.append("sentineliot-orphan")

    manager.stop_all()

    assert "sentineliot-camera-01" in fake.removed
    assert "sentineliot-orphan" in fake.removed
    assert manager.running() == []


def test_unavailable_docker_reports_error(tmp_path: Path) -> None:
    fake = FakeDocker(available=False)
    manager = _manager(tmp_path, fake)

    errors = manager.sync([_instance()])

    assert len(errors) == 1
    assert "indisponivel" in errors[0]
    assert fake.created == []


def test_container_user_override_is_applied(tmp_path: Path) -> None:
    fake = FakeDocker()
    manager = _manager(tmp_path, fake, container_user="4242:4242")

    manager.sync([_instance()])

    args = fake.created[0]
    assert "--user" in args
    assert "4242:4242" in args


def test_network_failure_is_reported(tmp_path: Path) -> None:
    class FailingNetwork(FakeDocker):
        def ensure_network(self, name: str) -> None:
            raise HoneypotError("sem permissao para criar rede")

    manager = _manager(tmp_path, FailingNetwork())

    errors = manager.sync([_instance()])

    assert errors == ["sem permissao para criar rede"]
    assert manager.running() == []


def test_sync_without_instances_keeps_nothing(tmp_path: Path) -> None:
    fake = FakeDocker()
    manager = _manager(tmp_path, fake)

    assert manager.sync([]) == []
    assert manager.running() == []
