from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
from pathlib import Path


_ALLOWED_ACTIONS = {
    "allow": "allow",
    "deny": "deny",
    "reject": "reject",
    "limit": "limit",
}
_ALLOWED_PROTOCOLS = {
    "tcp",
    "udp",
    "any",
}
_ALLOWED_DIRECTIONS = {
    "incoming",
    "outgoing",
}
SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/firewall/status.json"
)

_RULE_PATTERN = re.compile(
    r"^\[\s*(?P<number>\d+)\]\s+"
    r"(?P<to>.+?)\s{2,}"
    r"(?P<action>ALLOW|DENY|REJECT|LIMIT)"
    r"(?:\s+IN|\s+OUT)?\s{2,}"
    r"(?P<from>.+?)\s*$"
)

_PORT_PATTERN = re.compile(
    r"^(?:\d{1,5})(?::\d{1,5})?(?:,\d{1,5}(?::\d{1,5})?)*$"
)


def install_firewall() -> str:
    _run(
        ["apt-get", "update"],
        timeout=600,
        environment={
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )
    _run(
        ["apt-get", "install", "-y", "ufw"],
        timeout=900,
        environment={
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )
    refresh_snapshot()
    return "Ubuntu Firewall was installed successfully."


def set_firewall_enabled(
    *,
    enabled: bool,
) -> str:
    if enabled:
        _run(
            ["ufw", "--force", "enable"],
            timeout=60,
        )
        refresh_snapshot()
        return "The firewall is now enabled."

    _run(
        ["ufw", "disable"],
        timeout=60,
    )
    refresh_snapshot()
    return "The firewall is now disabled."


def set_logging(
    *,
    level: str,
) -> str:
    normalized = level.strip().lower()

    if normalized not in {
        "off",
        "low",
        "medium",
        "high",
        "full",
    }:
        raise ValueError(
            "The selected logging level is invalid."
        )

    _run(
        ["ufw", "logging", normalized],
        timeout=30,
    )
    refresh_snapshot()
    return f"Firewall logging was set to {normalized}."


def set_defaults(
    *,
    incoming: str,
    outgoing: str,
) -> str:
    incoming = incoming.strip().lower()
    outgoing = outgoing.strip().lower()

    if incoming not in {"allow", "deny", "reject"}:
        raise ValueError(
            "The incoming default is invalid."
        )
    if outgoing not in {"allow", "deny", "reject"}:
        raise ValueError(
            "The outgoing default is invalid."
        )

    _run(
        ["ufw", "default", incoming, "incoming"],
        timeout=30,
    )
    _run(
        ["ufw", "default", outgoing, "outgoing"],
        timeout=30,
    )

    refresh_snapshot()
    return "The default firewall behavior was updated."


def add_rules(
    *,
    action: str,
    direction: str,
    sources: list[str],
    destination: str,
    port: str,
    protocol: str,
    profile: str,
    comment: str,
) -> str:
    if not sources:
        raise ValueError(
            "At least one source is required."
        )

    for source in sources:
        _add_rule(
            action=action,
            direction=direction,
            source=source,
            destination=destination,
            port=port,
            protocol=protocol,
            profile=profile,
            comment=comment,
        )

    refresh_snapshot()
    count = len(sources)
    return (
        f"{count} firewall rule"
        f"{'s were' if count != 1 else ' was'} added."
    )


def _add_rule(
    *,
    action: str,
    direction: str,
    source: str,
    destination: str,
    port: str,
    protocol: str,
    profile: str,
    comment: str,
) -> None:
    action = action.strip().lower()
    direction = direction.strip().lower()
    protocol = protocol.strip().lower()
    source = source.strip()
    destination = destination.strip()
    port = port.strip()
    profile = profile.strip()
    comment = comment.strip()

    if action not in _ALLOWED_ACTIONS:
        raise ValueError(
            "The selected firewall action is invalid."
        )
    if direction not in _ALLOWED_DIRECTIONS:
        raise ValueError(
            "The selected direction is invalid."
        )
    if protocol not in _ALLOWED_PROTOCOLS:
        raise ValueError(
            "The selected network protocol is invalid."
        )

    command = [
        "ufw",
        _ALLOWED_ACTIONS[action],
    ]

    if direction == "outgoing":
        command.append("out")

    if source and source.lower() != "anywhere":
        _validate_network(source)
        command.extend(["from", source])
    else:
        command.extend(["from", "any"])

    if destination and destination.lower() != "this computer":
        _validate_network(destination)
        command.extend(["to", destination])
    else:
        command.extend(["to", "any"])

    if profile:
        command.extend(["app", profile])
    elif port:
        _validate_ports(port)

        if protocol == "any":
            command.extend(["port", port])
        else:
            command.extend(
                [
                    "port",
                    port,
                    "proto",
                    protocol,
                ]
            )
    else:
        raise ValueError(
            "Choose an application profile or enter a port."
        )

    if comment:
        if len(comment) > 120:
            raise ValueError(
                "Rule descriptions must be 120 characters "
                "or fewer."
            )
        if any(
            character in comment
            for character in "\0\n\r"
        ):
            raise ValueError(
                "The rule description contains invalid "
                "characters."
            )
        command.extend(["comment", comment])

    _run(command, timeout=60)


def delete_rule(
    *,
    number: int,
) -> str:
    if number < 1:
        raise ValueError(
            "The selected firewall rule is invalid."
        )

    _run(
        [
            "ufw",
            "--force",
            "delete",
            str(number),
        ],
        timeout=60,
    )
    refresh_snapshot()
    return f"Firewall rule {number} was removed."


def reset_firewall() -> str:
    _run(
        ["ufw", "--force", "reset"],
        timeout=60,
    )
    refresh_snapshot()
    return (
        "All custom firewall rules were removed and "
        "the firewall was disabled."
    )


def refresh_snapshot() -> str:
    status_result = subprocess.run(
        ["ufw", "status", "verbose"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    status_text = (
        status_result.stdout.strip()
        or status_result.stderr.strip()
    )

    active = False
    logging = "Unknown"
    incoming = "Unknown"
    outgoing = "Unknown"
    routed = "Unknown"

    for raw_line in status_text.splitlines():
        line = raw_line.strip()
        if line.startswith("Status:"):
            active = (
                line.partition(":")[2].strip().lower()
                == "active"
            )
        elif line.startswith("Logging:"):
            logging = line.partition(":")[2].strip()
        elif line.startswith("Default:"):
            defaults = line.partition(":")[2].strip()
            for component in defaults.split(","):
                value = component.strip()
                if value.endswith("(incoming)"):
                    incoming = value.removesuffix(
                        "(incoming)"
                    ).strip()
                elif value.endswith("(outgoing)"):
                    outgoing = value.removesuffix(
                        "(outgoing)"
                    ).strip()
                elif value.endswith("(routed)"):
                    routed = value.removesuffix(
                        "(routed)"
                    ).strip()

    numbered = subprocess.run(
        ["ufw", "status", "numbered"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    rules: list[dict[str, object]] = []

    for raw_line in numbered.stdout.splitlines():
        match = _RULE_PATTERN.match(raw_line.strip())
        if match is None:
            continue
        rules.append(
            {
                "number": int(match.group("number")),
                "destination": match.group("to").strip(),
                "action": match.group("action").strip(),
                "source": match.group("from").strip(),
            }
        )

    profiles_result = subprocess.run(
        ["ufw", "app", "list"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    profiles: list[str] = []
    found_header = False

    for raw_line in profiles_result.stdout.splitlines():
        line = raw_line.strip()
        if line == "Available applications:":
            found_header = True
            continue
        if found_header and line:
            profiles.append(line)

    payload = {
        "active": active,
        "logging": logging,
        "default_incoming": incoming,
        "default_outgoing": outgoing,
        "default_routed": routed,
        "detail": status_text,
        "rules": rules,
        "application_profiles": sorted(
            profiles,
            key=str.casefold,
        ),
    }

    SNAPSHOT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(SNAPSHOT_PATH.parent, 0o755)

    temporary = SNAPSHOT_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o644)
    temporary.replace(SNAPSHOT_PATH)
    os.chmod(SNAPSHOT_PATH, 0o644)

    return "Firewall status was refreshed."


def _validate_network(value: str) -> None:
    try:
        ipaddress.ip_network(
            value,
            strict=False,
        )
        return
    except ValueError:
        pass

    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}",
        value,
    ):
        raise ValueError(
            f"{value} is not a valid address or network."
        )


def _validate_ports(value: str) -> None:
    if not _PORT_PATTERN.fullmatch(value):
        raise ValueError(
            "Ports must be a number, a range such as "
            "8000:8010, or a comma-separated list."
        )

    for component in value.split(","):
        endpoints = component.split(":")

        for endpoint in endpoints:
            port = int(endpoint)
            if not 1 <= port <= 65535:
                raise ValueError(
                    "Ports must be between 1 and 65535."
                )

        if (
            len(endpoints) == 2
            and int(endpoints[0]) > int(endpoints[1])
        ):
            raise ValueError(
                "The beginning of a port range cannot "
                "be greater than its end."
            )


def _run(
    command: list[str],
    *,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> None:
    process_environment = os.environ.copy()

    if environment:
        process_environment.update(environment)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=process_environment,
    )

    if result.returncode == 0:
        return

    message = (
        result.stderr.strip()
        or result.stdout.strip()
        or (
            f"{command[0]} exited with code "
            f"{result.returncode}"
        )
    )

    raise RuntimeError(
        f"{' '.join(command)} failed:\n\n{message}"
    )
