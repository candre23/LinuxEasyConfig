from __future__ import annotations

import datetime as dt
import ipaddress
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/port-usage/status.json"
)
FIREWALL_SNAPSHOT = Path(
    "/var/lib/linuxeasyconfig/firewall/status.json"
)
DOCKER_FIREWALL_RULES = Path(
    "/etc/linuxeasyconfig/firewall/docker-rules.json"
)
REVERSE_PROXY_RULES = Path(
    "/etc/linuxeasyconfig/reverse_proxy/routes.json"
)

_PROCESS_PATTERN = re.compile(
    r'\("(?P<name>[^"]+)",pid=(?P<pid>\d+)'
)


def collect_snapshot() -> dict[str, Any]:
    listeners = _listening_sockets()
    docker_mappings = _docker_mappings()
    firewall = _firewall_state()
    proxy_rules = _load_json(REVERSE_PROXY_RULES, [])
    docker_rules = _load_json(DOCKER_FIREWALL_RULES, [])

    rows: list[dict[str, Any]] = []

    for listener in listeners:
        row = dict(listener)
        _apply_process_details(row)
        _apply_docker_details(row, docker_mappings)
        _apply_firewall_details(
            row,
            firewall,
            docker_rules,
        )
        _apply_proxy_details(row, proxy_rules)
        _apply_exposure_summary(row)
        rows.append(row)

    rows.sort(
        key=lambda item: (
            int(item.get("port", 0)),
            str(item.get("protocol", "")),
            str(item.get("bind_address", "")),
        )
    )

    return {
        "generated_at": dt.datetime.now(
            dt.timezone.utc
        ).isoformat(),
        "rows": rows,
        "summary": _summary(rows),
        "collector": {
            "ss_available": shutil.which("ss") is not None,
            "docker_available": shutil.which("docker") is not None,
            "firewall_snapshot_available": FIREWALL_SNAPSHOT.is_file(),
            "reverse_proxy_rules_available": REVERSE_PROXY_RULES.is_file(),
        },
    }


def write_snapshot() -> dict[str, Any]:
    value = collect_snapshot()
    SNAPSHOT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    SNAPSHOT_PATH.parent.chmod(0o755)
    temporary = SNAPSHOT_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.chmod(0o644)
    temporary.replace(SNAPSHOT_PATH)
    SNAPSHOT_PATH.chmod(0o644)
    return value


def _listening_sockets() -> list[dict[str, Any]]:
    if shutil.which("ss") is None:
        raise RuntimeError(
            "The ss utility is not installed."
        )

    result = subprocess.run(
        ["ss", "-H", "-lntup"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Could not list listening ports."
        )

    rows: list[dict[str, Any]] = []

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        fields = line.split(None, 6)

        if len(fields) < 6:
            continue

        protocol = fields[0].lower()
        state = fields[1]
        local = fields[4]
        process_text = fields[6] if len(fields) > 6 else ""
        bind_address, port = _split_endpoint(local)

        if port <= 0:
            continue

        processes = [
            {
                "name": match.group("name"),
                "pid": int(match.group("pid")),
            }
            for match in _PROCESS_PATTERN.finditer(process_text)
        ]

        process_name = (
            ", ".join(
                sorted(
                    {
                        item["name"]
                        for item in processes
                    }
                )
            )
            if processes
            else "Unknown"
        )
        pids = sorted(
            {
                int(item["pid"])
                for item in processes
            }
        )

        rows.append(
            {
                "protocol": protocol,
                "state": state,
                "bind_address": bind_address,
                "port": port,
                "process_name": process_name,
                "pids": pids,
                "service_name": "",
                "command": "",
                "user": "",
                "application": process_name,
                "scope": _bind_scope(bind_address),
                "container_name": "",
                "container_port": 0,
                "docker_mapping": "",
                "firewall_status": "Unknown",
                "firewall_detail": "",
                "proxy_hostnames": [],
                "proxy_paths": [],
                "public_ports": [],
                "proxy_detail": "",
                "overall_exposure": "",
            }
        )

    return rows


def _split_endpoint(value: str) -> tuple[str, int]:
    value = value.strip()

    if value.startswith("[") and "]:" in value:
        address, _, port_text = value[1:].partition("]:")
    else:
        address, separator, port_text = value.rpartition(":")

        if not separator:
            return value, 0

    address = address.strip() or "*"
    port_text = port_text.strip()

    try:
        return address, int(port_text)
    except ValueError:
        return address, 0


def _bind_scope(address: str) -> str:
    normalized = address.split("%", 1)[0]

    if normalized in {"127.0.0.1", "::1"}:
        return "Localhost only"

    if normalized in {"0.0.0.0", "::", "*"}:
        return "All interfaces"

    try:
        parsed = ipaddress.ip_address(normalized)
    except ValueError:
        return "Specific interface"

    if parsed.is_loopback:
        return "Localhost only"
    if parsed.is_link_local:
        return "Link-local"
    if parsed.is_private:
        return "Local network interface"
    return "Public interface"


def _apply_process_details(row: dict[str, Any]) -> None:
    pids = row.get("pids", [])

    if not isinstance(pids, list) or not pids:
        return

    pid = int(pids[0])
    proc = Path("/proc") / str(pid)

    try:
        row["command"] = (
            (proc / "cmdline")
            .read_bytes()
            .replace(b"\x00", b" ")
            .decode("utf-8", errors="replace")
            .strip()
        )
    except OSError:
        pass

    try:
        row["user"] = str(
            (proc / "status")
            .read_text(
                encoding="utf-8",
                errors="replace",
            )
            .split("Uid:", 1)[1]
            .splitlines()[0]
            .split()[0]
        )
    except (OSError, IndexError):
        pass

    service = _systemd_service_for_pid(pid)

    if service:
        row["service_name"] = service
        row["application"] = service
    elif row.get("process_name"):
        row["application"] = row["process_name"]


def _systemd_service_for_pid(pid: int) -> str:
    result = subprocess.run(
        [
            "systemctl",
            "status",
            str(pid),
            "--no-pager",
            "--lines",
            "0",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    text = result.stdout.strip()

    for line in text.splitlines():
        stripped = line.strip()

        if ".service" not in stripped:
            continue

        match = re.search(
            r"([A-Za-z0-9_.@-]+\.service)",
            stripped,
        )

        if match:
            return match.group(1)

    return ""


def _docker_mappings() -> list[dict[str, Any]]:
    if shutil.which("docker") is None:
        return []

    ids_result = subprocess.run(
        ["docker", "ps", "-aq"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    ids = [
        value.strip()
        for value in ids_result.stdout.splitlines()
        if value.strip()
    ]

    if not ids:
        return []

    inspect_result = subprocess.run(
        ["docker", "inspect", *ids],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if inspect_result.returncode != 0:
        return []

    try:
        containers = json.loads(
            inspect_result.stdout or "[]"
        )
    except json.JSONDecodeError:
        return []

    mappings: list[dict[str, Any]] = []

    for container in containers:
        if not isinstance(container, dict):
            continue

        name = str(
            container.get("Name", "")
        ).lstrip("/")
        ports = (
            container.get("NetworkSettings", {})
            .get("Ports", {})
        )

        if not isinstance(ports, dict):
            continue

        for container_endpoint, bindings in ports.items():
            container_port, _, protocol = str(
                container_endpoint
            ).partition("/")

            try:
                container_port_number = int(
                    container_port
                )
            except ValueError:
                continue

            if not isinstance(bindings, list):
                continue

            for binding in bindings:
                if not isinstance(binding, dict):
                    continue

                try:
                    host_port = int(
                        binding.get("HostPort", 0)
                    )
                except (TypeError, ValueError):
                    continue

                if host_port <= 0:
                    continue

                mappings.append(
                    {
                        "container_name": name,
                        "protocol": protocol or "tcp",
                        "host_address": str(
                            binding.get(
                                "HostIp",
                                "",
                            )
                        ),
                        "host_port": host_port,
                        "container_port": container_port_number,
                    }
                )

    return mappings


def _apply_docker_details(
    row: dict[str, Any],
    mappings: list[dict[str, Any]],
) -> None:
    matches = [
        item
        for item in mappings
        if int(item.get("host_port", 0))
        == int(row.get("port", 0))
        and str(item.get("protocol", "tcp"))
        == str(row.get("protocol", "tcp"))
        and _addresses_overlap(
            str(item.get("host_address", "")),
            str(row.get("bind_address", "")),
        )
    ]

    if not matches:
        return

    item = matches[0]
    row["container_name"] = str(
        item.get("container_name", "")
    )
    row["container_port"] = int(
        item.get("container_port", 0)
    )
    row["application"] = (
        f"Docker: {row['container_name']}"
    )
    row["docker_mapping"] = (
        f"container {row['container_port']}/"
        f"{row['protocol']} → host {row['port']}"
    )


def _addresses_overlap(first: str, second: str) -> bool:
    aliases = {"", "0.0.0.0", "::", "*"}

    if first in aliases or second in aliases:
        return True

    return (
        first.split("%", 1)[0]
        == second.split("%", 1)[0]
    )


def _firewall_state() -> dict[str, Any]:
    return _load_json(
        FIREWALL_SNAPSHOT,
        {},
    )


def _apply_firewall_details(
    row: dict[str, Any],
    firewall: dict[str, Any],
    docker_rules: Any,
) -> None:
    scope = str(row.get("scope", ""))

    if scope == "Localhost only":
        row["firewall_status"] = "Not applicable"
        row["firewall_detail"] = (
            "The service only listens on localhost."
        )
        return

    protocol = str(row.get("protocol", "tcp"))
    port = int(row.get("port", 0))
    container = str(
        row.get("container_name", "")
    )

    if container and isinstance(docker_rules, list):
        matching = [
            item
            for item in docker_rules
            if isinstance(item, dict)
            and int(item.get("host_port", 0)) == port
            and str(item.get("protocol", "tcp"))
            == protocol
        ]

        if matching:
            sources = matching[0].get("sources", [])

            if isinstance(sources, list) and sources:
                row["firewall_status"] = "LAN allowed"
                row["firewall_detail"] = (
                    "Managed Docker firewall rule: "
                    + ", ".join(str(value) for value in sources)
                )
                return

    active = bool(firewall.get("active", False))

    if not active:
        row["firewall_status"] = "Firewall inactive"
        row["firewall_detail"] = (
            "The host firewall is not active."
        )
        return

    rules = firewall.get("rules", [])

    if not isinstance(rules, list):
        rules = []

    matched_allow: list[str] = []
    matched_block: list[str] = []

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        destination = str(
            rule.get("destination", "")
        )
        action = str(
            rule.get("action", "")
        ).upper()
        source = str(
            rule.get("source", "")
        )

        if not _rule_matches_port(
            destination,
            port,
            protocol,
        ):
            continue

        detail = f"{action} from {source}"

        if "DENY" in action or "REJECT" in action:
            matched_block.append(detail)
        elif "ALLOW" in action:
            matched_allow.append(detail)

    if matched_block:
        row["firewall_status"] = "Blocked"
        row["firewall_detail"] = "; ".join(
            matched_block
        )
    elif matched_allow:
        broad = any(
            "Anywhere" in item
            or "0.0.0.0/0" in item
            or "::/0" in item
            for item in matched_allow
        )
        row["firewall_status"] = (
            "All sources allowed"
            if broad
            else "LAN allowed"
        )
        row["firewall_detail"] = "; ".join(
            matched_allow
        )
    else:
        row["firewall_status"] = "Unmanaged/unknown"
        row["firewall_detail"] = (
            "No matching managed firewall rule was found."
        )


def _rule_matches_port(
    destination: str,
    port: int,
    protocol: str,
) -> bool:
    value = destination.lower()

    patterns = {
        str(port),
        f"{port}/{protocol}",
        f"{port} ({protocol})",
    }

    return any(
        pattern in value
        for pattern in patterns
    )


def _apply_proxy_details(
    row: dict[str, Any],
    rules: Any,
) -> None:
    if not isinstance(rules, list):
        return

    port = int(row.get("port", 0))
    address = str(
        row.get("bind_address", "")
    )

    hostnames: list[str] = []
    paths: list[str] = []
    details: list[str] = []
    public_ports: set[int] = set()

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        if not bool(rule.get("enabled", True)):
            continue

        try:
            backend_port = int(
                rule.get("backend_port", 0)
            )
        except (TypeError, ValueError):
            continue

        if backend_port != port:
            continue

        backend_host = str(
            rule.get("backend_host", "")
        )

        if not _proxy_backend_matches(
            address,
            backend_host,
        ):
            continue

        hostname = str(
            rule.get("public_host", "")
        ).strip()
        route_type = str(
            rule.get("route_type", "host")
        )
        path = str(
            rule.get("path", "")
        ).strip()

        if hostname:
            hostnames.append(hostname)

        if path:
            paths.append(path)

        public_ports.add(443)
        details.append(
            (
                f"https://{hostname}{path}"
                if hostname
                else f"HTTPS route{path}"
            )
            + f" → {backend_host}:{backend_port}"
            + (
                " (path stripped)"
                if bool(rule.get("strip_path", False))
                and path
                else ""
            )
            + (
                " (login required)"
                if bool(rule.get("require_login", False))
                else ""
            )
        )

    row["proxy_hostnames"] = sorted(
        set(hostnames)
    )
    row["proxy_paths"] = sorted(
        set(paths)
    )
    row["public_ports"] = sorted(
        public_ports
    )
    row["proxy_detail"] = "; ".join(details)


def _proxy_backend_matches(
    bind_address: str,
    backend_host: str,
) -> bool:
    local_aliases = {
        "127.0.0.1",
        "::1",
        "localhost",
    }
    wildcard_aliases = {
        "0.0.0.0",
        "::",
        "*",
    }

    first = bind_address.split("%", 1)[0]
    second = backend_host.split("%", 1)[0]

    if first == second:
        return True
    if first in wildcard_aliases:
        return True
    if first in local_aliases and second in local_aliases:
        return True
    return False


def _apply_exposure_summary(
    row: dict[str, Any],
) -> None:
    if row.get("proxy_hostnames"):
        row["overall_exposure"] = (
            "Internet accessible through Caddy"
        )
        return

    scope = str(row.get("scope", ""))
    firewall = str(
        row.get("firewall_status", "")
    )

    if scope == "Localhost only":
        row["overall_exposure"] = (
            "Local machine only"
        )
    elif firewall == "Blocked":
        row["overall_exposure"] = (
            "Blocked by firewall"
        )
    elif firewall == "LAN allowed":
        row["overall_exposure"] = (
            "LAN accessible"
        )
    elif firewall in {
        "All sources allowed",
        "Firewall inactive",
    }:
        row["overall_exposure"] = (
            "Potentially directly exposed"
        )
    else:
        row["overall_exposure"] = (
            "Exposure uncertain"
        )


def _summary(
    rows: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "listening_sockets": len(rows),
        "localhost_only": sum(
            1
            for row in rows
            if row.get("scope") == "Localhost only"
        ),
        "lan_accessible": sum(
            1
            for row in rows
            if row.get("overall_exposure")
            == "LAN accessible"
        ),
        "caddy_exposed": sum(
            1
            for row in rows
            if row.get("proxy_hostnames")
        ),
        "potentially_direct": sum(
            1
            for row in rows
            if row.get("overall_exposure")
            == "Potentially directly exposed"
        ),
        "uncertain": sum(
            1
            for row in rows
            if row.get("overall_exposure")
            == "Exposure uncertain"
        ),
    }


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
