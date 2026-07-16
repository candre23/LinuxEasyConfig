from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .vnc import load_vnc_snapshot


SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/remote-access/status.json"
)


class RemoteAccessRepository:
    def snapshot(self) -> dict[str, Any]:
        if not SNAPSHOT_PATH.is_file():
            return {
                "installed": shutil.which("sshd") is not None,
                "active": False,
                "port": 22,
                "password_authentication": False,
                "public_key_authentication": True,
                "permit_root_login": "no",
                "sessions": [],
            }

        try:
            value = json.loads(
                SNAPSHOT_PATH.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}

        return value if isinstance(value, dict) else {}


    def vnc_snapshot(self) -> dict[str, Any]:
        return load_vnc_snapshot()

    def local_networks(self) -> list[str]:
        defaults = _route_json(
            ["ip", "-j", "-4", "route", "show", "default"]
        )
        links = _route_json(
            ["ip", "-j", "-4", "route", "show", "scope", "link"]
        )
        devices = {
            str(item.get("dev", "")).strip()
            for item in defaults
            if isinstance(item, dict)
        }
        networks: set[ipaddress.IPv4Network] = set()

        for item in links:
            if not isinstance(item, dict):
                continue
            if devices and str(item.get("dev", "")) not in devices:
                continue
            destination = str(item.get("dst", "")).strip()
            try:
                network = ipaddress.ip_network(
                    destination,
                    strict=False,
                )
            except ValueError:
                continue
            if (
                isinstance(network, ipaddress.IPv4Network)
                and not network.is_loopback
                and not network.is_link_local
            ):
                networks.add(network)

        return [
            str(value)
            for value in sorted(
                networks,
                key=lambda value: (
                    int(value.network_address),
                    value.prefixlen,
                ),
            )
        ]


def _route_json(command: list[str]) -> list[Any]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    try:
        value = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []
