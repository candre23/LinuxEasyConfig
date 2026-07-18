from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from linuxeasyconfig.core.config.managed import write_json, write_text
from typing import Any


MODULE_ID = "org.linuxeasyconfig.firewall"
STATE_PATH = Path(
    "/etc/linuxeasyconfig/firewall/docker-rules.json"
)
APPLY_SCRIPT = Path(
    "/usr/local/sbin/lec-docker-firewall-apply"
)
UNIT_PATH = Path(
    "/etc/systemd/system/lec-docker-firewall.service"
)
CHAIN = "LEC-DOCKER"

_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"
)


@dataclass
class DockerFirewallRule:
    container: str
    host_port: int
    container_port: int
    protocol: str
    sources: list[str]
    comment: str
    blocked: bool = False


def load_docker_rules() -> list[DockerFirewallRule]:
    if not STATE_PATH.is_file():
        return []

    try:
        value = json.loads(
            STATE_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(value, list):
        return []

    rules: list[DockerFirewallRule] = []

    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            rules.append(DockerFirewallRule(**item))
        except (TypeError, ValueError):
            continue

    return rules


def allow_docker_service(
    *,
    container: str,
    host_port: int,
    container_port: int,
    protocol: str,
    sources: list[str],
    comment: str,
) -> str:
    _validate_rule(
        container=container,
        host_port=host_port,
        container_port=container_port,
        protocol=protocol,
        sources=sources,
    )

    rules = [
        rule
        for rule in load_docker_rules()
        if not (
            rule.container == container
            and rule.host_port == host_port
            and rule.protocol == protocol
        )
    ]

    rules.append(
        DockerFirewallRule(
            container=container,
            host_port=host_port,
            container_port=container_port,
            protocol=protocol,
            sources=list(sources),
            comment=comment.strip()[:120],
            blocked=False,
        )
    )

    _save_and_apply(rules)

    return (
        f"Docker port {host_port}/{protocol} for "
        f"{container} is limited to the selected local network."
    )



def block_docker_service(
    *,
    container: str,
    host_port: int,
    protocol: str,
) -> str:
    rules = load_docker_rules()
    matched = False

    for rule in rules:
        if (
            rule.container == container
            and rule.host_port == host_port
            and rule.protocol == protocol
        ):
            rule.blocked = True
            matched = True

    if not matched:
        raise ValueError(
            "The selected Docker firewall rule was not found."
        )

    _save_and_apply(rules)

    return (
        f"Docker port {host_port}/{protocol} for "
        f"{container} is now blocked."
    )


def unblock_docker_service(
    *,
    container: str,
    host_port: int,
    protocol: str,
) -> str:
    rules = load_docker_rules()
    matched = False

    for rule in rules:
        if (
            rule.container == container
            and rule.host_port == host_port
            and rule.protocol == protocol
        ):
            rule.blocked = False
            matched = True

    if not matched:
        raise ValueError(
            "The selected Docker firewall rule was not found."
        )

    _save_and_apply(rules)

    return (
        f"Docker port {host_port}/{protocol} for "
        f"{container} is open to the configured local networks."
    )

def remove_docker_service(
    *,
    container: str,
    host_port: int = 0,
    protocol: str = "",
) -> str:
    rules = load_docker_rules()

    updated = [
        rule
        for rule in rules
        if not (
            rule.container == container
            and (
                host_port == 0
                or rule.host_port == host_port
            )
            and (
                not protocol
                or rule.protocol == protocol
            )
        )
    ]

    if len(updated) == len(rules):
        raise ValueError(
            "The selected Docker firewall rule was not found."
        )

    _save_and_apply(updated)

    return (
        f"Docker firewall rules for {container} were removed."
    )


def reapply_docker_rules() -> str:
    rules = load_docker_rules()
    _write_apply_script(rules)
    _install_unit()
    _run(
        [str(APPLY_SCRIPT)],
        timeout=60,
    )
    return "Docker firewall rules were reapplied."


def docker_firewall_backend() -> str:
    if subprocess.run(
        ["bash", "-lc", "command -v iptables"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    ).returncode != 0:
        return "Unavailable"

    result = subprocess.run(
        ["iptables", "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    detail = (
        result.stdout.strip()
        or result.stderr.strip()
    )

    if "nf_tables" in detail:
        return "iptables compatibility over nftables"
    if detail:
        return "iptables"
    return "Unknown"


def _save_and_apply(
    rules: list[DockerFirewallRule],
) -> None:
    STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(STATE_PATH.parent, 0o755)

    write_json(
        module_id=MODULE_ID,
        destination=STATE_PATH,
        value=[asdict(rule) for rule in rules],
        mode=0o644,
    )

    _write_apply_script(rules)
    _install_unit()
    _run(
        [str(APPLY_SCRIPT)],
        timeout=60,
    )


def _write_apply_script(
    rules: list[DockerFirewallRule],
) -> None:
    lines = [
        "#!/bin/sh",
        "set -eu",
        "command -v iptables >/dev/null 2>&1 || exit 0",
        "iptables -N LEC-DOCKER 2>/dev/null || true",
        (
            "iptables -C DOCKER-USER -j LEC-DOCKER "
            "2>/dev/null || "
            "iptables -I DOCKER-USER 1 -j LEC-DOCKER"
        ),
        "iptables -F LEC-DOCKER",
    ]

    # A blocked port must be checked before the general established-
    # connection allowance, otherwise an already-open browser
    # connection can continue to pass after the user clicks Block.
    for rule in rules:
        if rule.blocked:
            lines.append(
                "iptables -A LEC-DOCKER "
                f"-p {rule.protocol} "
                "-m conntrack "
                f"--ctorigdstport {rule.host_port} "
                "-m comment "
                f"--comment 'LEC Docker blocked {rule.container}' "
                "-j DROP"
            )

    lines.append(
        "iptables -A LEC-DOCKER "
        "-m conntrack --ctstate ESTABLISHED,RELATED "
        "-j ACCEPT"
    )

    for rule in rules:
        if rule.blocked:
            continue

        for source in rule.sources:
            lines.append(
                "iptables -A LEC-DOCKER "
                f"-p {rule.protocol} "
                "-m conntrack "
                f"--ctorigdstport {rule.host_port} "
                f"-s {source} "
                "-m comment "
                f"--comment 'LEC Docker {rule.container}' "
                "-j ACCEPT"
            )

        lines.append(
            "iptables -A LEC-DOCKER "
            f"-p {rule.protocol} "
            "-m conntrack "
            f"--ctorigdstport {rule.host_port} "
            "-m comment "
            f"--comment 'LEC Docker block {rule.container}' "
            "-j DROP"
        )

    lines.append("iptables -A LEC-DOCKER -j RETURN")

    APPLY_SCRIPT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    write_text(
        module_id=MODULE_ID,
        destination=APPLY_SCRIPT,
        text="\n".join(lines) + "\n",
        mode=0o755,
    )


def _install_unit() -> None:
    write_text(
        module_id=MODULE_ID,
        destination=UNIT_PATH,
        text=(
            "[Unit]\n"
            "Description=Apply Linux Easy Config Docker firewall rules\n"
            "After=docker.service\n"
            "Requires=docker.service\n\n"
            "[Service]\n"
            "Type=oneshot\n"
            f"ExecStart={APPLY_SCRIPT}\n"
            "RemainAfterExit=yes\n\n"
            "[Install]\n"
            "WantedBy=multi-user.target\n"
        ),
        mode=0o644,
    )

    _run(
        ["systemctl", "daemon-reload"],
        timeout=60,
    )
    _run(
        [
            "systemctl",
            "enable",
            "lec-docker-firewall.service",
        ],
        timeout=60,
    )


def _validate_rule(
    *,
    container: str,
    host_port: int,
    container_port: int,
    protocol: str,
    sources: list[str],
) -> None:
    if not _NAME_PATTERN.fullmatch(container.strip()):
        raise ValueError(
            "The container name is invalid."
        )
    if not 1 <= host_port <= 65535:
        raise ValueError(
            "The published host port is invalid."
        )
    if not 1 <= container_port <= 65535:
        raise ValueError(
            "The container port is invalid."
        )
    if protocol not in {"tcp", "udp"}:
        raise ValueError(
            "The network protocol is invalid."
        )
    if not sources:
        raise ValueError(
            "At least one allowed local network is required."
        )

    for source in sources:
        try:
            network = ipaddress.ip_network(
                source,
                strict=False,
            )
        except ValueError as exc:
            raise ValueError(
                f"{source} is not a valid network."
            ) from exc

        if network.is_unspecified:
            raise ValueError(
                "An unrestricted source is not allowed "
                "for a local-network Docker rule."
            )


def _run(
    command: list[str],
    *,
    timeout: int,
) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode == 0:
        return

    raise RuntimeError(
        result.stderr.strip()
        or result.stdout.strip()
        or f"{' '.join(command)} failed."
    )
