from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .presets import DockerPreset, import_preset, load_presets
from .storage import ManagedContainer, load_managed_containers


SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/docker/status.json"
)


@dataclass(frozen=True)
class DockerContainer:
    container_id: str
    name: str
    image: str
    state: str
    status: str
    ports: str


@dataclass(frozen=True)
class DockerStatus:
    installed: bool
    active: bool
    enabled: bool
    version: str
    compose_version: str


class DockerRepository:
    def status(self) -> DockerStatus:
        snapshot = self._snapshot()

        installed = bool(
            snapshot.get(
                "installed",
                shutil.which("docker") is not None,
            )
        )

        return DockerStatus(
            installed=installed,
            active=bool(snapshot.get("active", False)),
            enabled=bool(snapshot.get("enabled", False)),
            version=str(
                snapshot.get(
                    "version",
                    "Not installed"
                    if not installed
                    else "Unknown",
                )
            ),
            compose_version=str(
                snapshot.get(
                    "compose_version",
                    "Unavailable",
                )
            ),
        )

    def containers(self) -> list[DockerContainer]:
        snapshot = self._snapshot()
        values = snapshot.get("containers", [])

        if not isinstance(values, list):
            return []

        containers: list[DockerContainer] = []

        for item in values:
            if not isinstance(item, dict):
                continue

            containers.append(
                DockerContainer(
                    container_id=str(
                        item.get("id", "")
                    ),
                    name=str(
                        item.get("name", "")
                    ),
                    image=str(
                        item.get("image", "")
                    ),
                    state=str(
                        item.get("state", "")
                    ),
                    status=str(
                        item.get("status", "")
                    ),
                    ports=str(
                        item.get("ports", "")
                    ),
                )
            )

        return containers

    def local_networks(self) -> list[str]:
        default_result = subprocess.run(
            [
                "ip",
                "-j",
                "-4",
                "route",
                "show",
                "default",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        route_result = subprocess.run(
            [
                "ip",
                "-j",
                "-4",
                "route",
                "show",
                "scope",
                "link",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        try:
            defaults = json.loads(
                default_result.stdout or "[]"
            )
            routes = json.loads(
                route_result.stdout or "[]"
            )
        except json.JSONDecodeError:
            return []

        devices = {
            str(item.get("dev", ""))
            for item in defaults
            if isinstance(item, dict)
        }
        networks: set[
            ipaddress.IPv4Network
        ] = set()

        for item in routes:
            if not isinstance(item, dict):
                continue
            if (
                devices
                and str(item.get("dev", ""))
                not in devices
            ):
                continue

            destination = str(
                item.get("dst", "")
            )

            try:
                network = ipaddress.ip_network(
                    destination,
                    strict=False,
                )
            except ValueError:
                continue

            if (
                isinstance(
                    network,
                    ipaddress.IPv4Network,
                )
                and not network.is_loopback
                and not network.is_link_local
            ):
                networks.add(network)

        return [
            str(network)
            for network in sorted(
                networks,
                key=lambda value: (
                    int(value.network_address),
                    value.prefixlen,
                ),
            )
        ]

    def caddy_installed(self) -> bool:
        return shutil.which("caddy") is not None

    def presets(self) -> list[DockerPreset]:
        return load_presets()

    def import_preset(self, path: Path) -> Path:
        return import_preset(path)

    def application_exists(self, name: str) -> bool:
        name = name.strip()

        if not name:
            return False

        if any(
            item.name == name
            for item in load_managed_containers()
        ):
            return True

        return (
            Path("/opt/linuxeasyconfig/docker/apps")
            / name
            / "compose.yaml"
        ).is_file()

    def managed_containers(self) -> list[ManagedContainer]:
        return load_managed_containers()

    def primary_local_address(self) -> str:
        result = subprocess.run(
            [
                "ip",
                "-j",
                "-4",
                "route",
                "get",
                "1.1.1.1",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        try:
            values = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            return ""

        if not isinstance(values, list):
            return ""

        for item in values:
            if not isinstance(item, dict):
                continue
            address = str(item.get("prefsrc", "")).strip()
            if address:
                return address

        return ""

    @staticmethod
    def _snapshot() -> dict[str, Any]:
        if not SNAPSHOT_PATH.is_file():
            return {}

        try:
            value = json.loads(
                SNAPSHOT_PATH.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            return {}

        return value if isinstance(value, dict) else {}
