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
DOCKER_MANAGED_CONTAINERS = Path(
    "/etc/linuxeasyconfig/docker/managed-containers.json"
)
DOCKER_STATUS_SNAPSHOT = Path(
    "/var/lib/linuxeasyconfig/docker/status.json"
)
REVERSE_PROXY_ROUTES = Path(
    "/etc/linuxeasyconfig/reverse_proxy/routes.json"
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

    def guacamole_status(self) -> dict[str, Any]:
        managed = _load_json(
            DOCKER_MANAGED_CONTAINERS,
            [],
        )
        records = (
            managed
            if isinstance(managed, list)
            else []
        )

        record: dict[str, Any] | None = None

        for item in records:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name", "")).lower()
            image = str(item.get("image", "")).lower()

            if (
                "guacamole" in name
                or "apache guacamole" in image
            ):
                record = item
                break

        application_name = (
            str(record.get("name", "guacamole"))
            if record is not None
            else "guacamole"
        )

        containers = _docker_container_states(
            application_name
        )

        installed = bool(containers) or record is not None
        web_name = f"{application_name}-web"
        web = containers.get(web_name, {})
        running = str(
            web.get("state", "")
        ).lower() == "running"

        host_address = (
            str(record.get("host_address", ""))
            if record is not None
            else ""
        )
        host_port = (
            int(record.get("host_port", 0))
            if record is not None
            else 0
        )
        protocol = (
            str(
                record.get(
                    "service_protocol",
                    "http",
                )
            )
            if record is not None
            else "http"
        )
        access_scope = (
            str(record.get("access_scope", ""))
            if record is not None
            else ""
        )

        local_url = ""
        network_url = ""

        if host_port:
            if access_scope == "localhost":
                local_url = (
                    f"{protocol}://127.0.0.1:{host_port}"
                )
            elif access_scope == "local_network":
                address = (
                    host_address
                    or _primary_local_address()
                )
                if address:
                    local_url = (
                        f"{protocol}://{address}:{host_port}"
                    )
                    network_url = local_url
            elif access_scope == "all_networks":
                local_url = (
                    f"{protocol}://127.0.0.1:{host_port}"
                )
                address = _primary_local_address()
                if address:
                    network_url = (
                        f"{protocol}://{address}:{host_port}"
                    )

        proxy_url = ""

        routes = _load_json(
            REVERSE_PROXY_ROUTES,
            [],
        )

        if isinstance(routes, list):
            for route in routes:
                if not isinstance(route, dict):
                    continue
                if not bool(route.get("enabled", True)):
                    continue
                if int(route.get("backend_port", 0)) != host_port:
                    continue

                host = str(
                    route.get("public_host", "")
                ).strip()

                if host:
                    proxy_url = f"https://{host}"
                    break

        warnings: list[str] = []

        if installed and not running:
            warnings.append(
                "The Guacamole web container is not running."
            )

        if installed and access_scope == "all_networks":
            warnings.append(
                "Guacamole is published on all network interfaces. "
                "A reverse proxy is recommended for internet access."
            )

        if installed and not proxy_url:
            warnings.append(
                "Guacamole is not currently published through "
                "the Reverse Proxy module."
            )

        if installed:
            warnings.append(
                "The default Guacamole administrator password "
                "must be changed after first login."
            )

        return {
            "installed": installed,
            "running": running,
            "application_name": application_name,
            "containers": containers,
            "access_scope": access_scope,
            "local_url": local_url,
            "network_url": network_url,
            "proxy_url": proxy_url,
            "warnings": warnings,
        }

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


def _load_json(
    path: Path,
    default: Any,
) -> Any:
    if not path.is_file():
        return default

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except (OSError, json.JSONDecodeError):
        return default


def _docker_container_states(
    application_name: str,
) -> dict[str, dict[str, str]]:
    prefix = application_name + "-"
    values: dict[str, dict[str, str]] = {}

    snapshot = _load_json(
        DOCKER_STATUS_SNAPSHOT,
        {},
    )
    containers = (
        snapshot.get("containers", [])
        if isinstance(snapshot, dict)
        else []
    )

    if isinstance(containers, list):
        for item in containers:
            if not isinstance(item, dict):
                continue

            name = str(
                item.get("name", "")
            ).strip()

            if (
                name == application_name
                or name.startswith(prefix)
            ):
                values[name] = {
                    "state": str(
                        item.get("state", "")
                    ),
                    "status": str(
                        item.get("status", "")
                    ),
                }

    if values:
        return values

    if shutil.which("docker") is None:
        return {}

    result = subprocess.run(
        [
            "docker",
            "container",
            "ls",
            "--all",
            "--format",
            (
                "{{json .Names}}\t"
                "{{json .State}}\t"
                "{{json .Status}}"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        return {}

    for raw_line in result.stdout.splitlines():
        fields = raw_line.split("\t")

        if len(fields) != 3:
            continue

        try:
            name = str(json.loads(fields[0]))
            state = str(json.loads(fields[1]))
            status = str(json.loads(fields[2]))
        except json.JSONDecodeError:
            continue

        if (
            name == application_name
            or name.startswith(prefix)
        ):
            values[name] = {
                "state": state,
                "status": status,
            }

    return values


def _primary_local_address() -> str:
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
        values = json.loads(
            result.stdout or "[]"
        )
    except json.JSONDecodeError:
        return ""

    if not isinstance(values, list):
        return ""

    for item in values:
        if not isinstance(item, dict):
            continue

        address = str(
            item.get("prefsrc", "")
        ).strip()

        if address:
            return address

    return ""
