from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .docker_rules import (
    DockerFirewallRule,
    docker_firewall_backend,
    load_docker_rules,
)


SNAPSHOT_PATH = Path("/var/lib/linuxeasyconfig/firewall/status.json")


@dataclass(frozen=True)
class FirewallRule:
    number: int
    destination: str
    action: str
    source: str


@dataclass(frozen=True)
class FirewallStatus:
    installed: bool
    active: bool
    logging: str
    default_incoming: str
    default_outgoing: str
    default_routed: str
    version: str
    detail: str


class FirewallRepository:
    def status(self) -> FirewallStatus:
        installed = shutil.which("ufw") is not None
        if not installed:
            return FirewallStatus(
                False, False, "Unavailable", "Unavailable",
                "Unavailable", "Unavailable", "Not installed",
                "UFW is not installed.",
            )

        version_result = subprocess.run(
            ["ufw", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        version = (
            version_result.stdout.strip().splitlines()[0]
            if version_result.stdout.strip()
            else "Installed"
        )
        snapshot = self._snapshot()

        return FirewallStatus(
            installed=True,
            active=bool(snapshot.get("active", False)),
            logging=str(snapshot.get("logging", "Unknown")),
            default_incoming=str(
                snapshot.get("default_incoming", "Unknown")
            ),
            default_outgoing=str(
                snapshot.get("default_outgoing", "Unknown")
            ),
            default_routed=str(
                snapshot.get("default_routed", "Unknown")
            ),
            version=version,
            detail=str(
                snapshot.get(
                    "detail",
                    "Firewall status has not yet been refreshed.",
                )
            ),
        )

    def rules(self) -> list[FirewallRule]:
        snapshot = self._snapshot()
        values = snapshot.get("rules", [])
        if not isinstance(values, list):
            return []

        result: list[FirewallRule] = []
        for item in values:
            if not isinstance(item, dict):
                continue
            try:
                result.append(
                    FirewallRule(
                        number=int(item["number"]),
                        destination=str(item["destination"]),
                        action=str(item["action"]),
                        source=str(item["source"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def application_profiles(self) -> list[str]:
        snapshot = self._snapshot()
        values = snapshot.get("application_profiles", [])
        if not isinstance(values, list):
            return []
        return [str(value) for value in values if str(value).strip()]

    def local_networks(self) -> list[str]:
        """
        Return the directly connected IPv4 networks used by the
        interface or interfaces carrying the default route.

        This avoids treating every private IPv4 range as local.
        """
        default_result = subprocess.run(
            ["ip", "-j", "-4", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        route_result = subprocess.run(
            ["ip", "-j", "-4", "route", "show", "scope", "link"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if (
            default_result.returncode != 0
            or route_result.returncode != 0
        ):
            return []

        try:
            default_routes = json.loads(default_result.stdout or "[]")
            connected_routes = json.loads(route_result.stdout or "[]")
        except json.JSONDecodeError:
            return []

        default_devices = {
            str(route.get("dev", "")).strip()
            for route in default_routes
            if isinstance(route, dict)
            and str(route.get("dev", "")).strip()
        }

        networks: set[ipaddress.IPv4Network] = set()

        for route in connected_routes:
            if not isinstance(route, dict):
                continue

            device = str(route.get("dev", "")).strip()
            destination = str(route.get("dst", "")).strip()

            if default_devices and device not in default_devices:
                continue
            if not destination or destination == "default":
                continue

            try:
                network = ipaddress.ip_network(
                    destination,
                    strict=False,
                )
            except ValueError:
                continue

            if not isinstance(network, ipaddress.IPv4Network):
                continue
            if network.is_loopback or network.is_link_local:
                continue

            networks.add(network)

        return [
            str(network)
            for network in sorted(
                networks,
                key=lambda item: (
                    int(item.network_address),
                    item.prefixlen,
                ),
            )
        ]

    def docker_rules(self) -> list[DockerFirewallRule]:
        return load_docker_rules()

    def docker_firewall_backend(self) -> str:
        return docker_firewall_backend()

    def recent_log_lines(
        self,
        *,
        maximum_lines: int = 300,
    ) -> list[str]:
        result = subprocess.run(
            [
                "journalctl",
                "-k",
                "--no-pager",
                "--lines",
                str(maximum_lines),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [
            line
            for line in result.stdout.splitlines()
            if "[UFW " in line
        ]

    @staticmethod
    def _snapshot() -> dict[str, object]:
        if not SNAPSHOT_PATH.exists():
            return {}
        try:
            value = json.loads(
                SNAPSHOT_PATH.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}
