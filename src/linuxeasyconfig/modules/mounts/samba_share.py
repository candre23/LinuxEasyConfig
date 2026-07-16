from __future__ import annotations

import ipaddress
import json
import pwd
import grp
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STATE_PATH = Path(
    "/etc/linuxeasyconfig/mounts/samba-shares.json"
)

_SHARE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$"
)


@dataclass(frozen=True)
class SambaStatus:
    installed: bool
    service_active: bool
    version: str
    configured_shares: int


@dataclass(frozen=True)
class HostedShare:
    name: str
    path: str
    comment: str
    read_only: bool
    guest_access: bool
    allowed_users: tuple[str, ...]
    allowed_groups: tuple[str, ...]
    local_network_only: bool
    enabled: bool


def samba_status() -> SambaStatus:
    installed = shutil.which("smbd") is not None

    if not installed:
        return SambaStatus(
            installed=False,
            service_active=False,
            version="Not installed",
            configured_shares=0,
        )

    version_result = subprocess.run(
        ["smbd", "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    version = (
        version_result.stdout.strip()
        or "Installed"
    )

    service_result = subprocess.run(
        ["systemctl", "is-active", "smbd"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    return SambaStatus(
        installed=True,
        service_active=(
            service_result.stdout.strip() == "active"
        ),
        version=version,
        configured_shares=len(load_hosted_shares()),
    )


def load_hosted_shares() -> list[HostedShare]:
    if not STATE_PATH.is_file():
        return []

    try:
        value = json.loads(
            STATE_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(value, dict):
        return []

    items = value.get("shares", [])
    if not isinstance(items, list):
        return []

    result: list[HostedShare] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        try:
            result.append(
                HostedShare(
                    name=str(item["name"]),
                    path=str(item["path"]),
                    comment=str(item.get("comment", "")),
                    read_only=bool(
                        item.get("read_only", True)
                    ),
                    guest_access=bool(
                        item.get("guest_access", False)
                    ),
                    allowed_users=tuple(
                        str(value)
                        for value in item.get(
                            "allowed_users",
                            [],
                        )
                    ),
                    allowed_groups=tuple(
                        str(value)
                        for value in item.get(
                            "allowed_groups",
                            [],
                        )
                    ),
                    local_network_only=bool(
                        item.get(
                            "local_network_only",
                            True,
                        )
                    ),
                    enabled=bool(
                        item.get("enabled", True)
                    ),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    return sorted(
        result,
        key=lambda share: share.name.casefold(),
    )


def validate_share_values(
    *,
    name: str,
    path: str,
    comment: str,
    guest_access: bool,
    allowed_users: list[str],
    allowed_groups: list[str],
) -> None:
    cleaned_name = name.strip()

    if not _SHARE_NAME_PATTERN.fullmatch(
        cleaned_name
    ):
        raise ValueError(
            "The share name must begin with a letter "
            "or number and may contain spaces, periods, "
            "underscores, and hyphens."
        )

    if cleaned_name.casefold() in {
        "global",
        "homes",
        "printers",
        "print$",
        "ipc$",
    }:
        raise ValueError(
            "That share name is reserved by Samba."
        )

    folder = Path(path.strip())

    if not folder.is_absolute():
        raise ValueError(
            "The shared folder must use an absolute path."
        )

    if not folder.is_dir():
        raise ValueError(
            "The selected shared folder does not exist."
        )

    if any(
        character in comment
        for character in "\0\n\r"
    ):
        raise ValueError(
            "The description contains invalid characters."
        )

    if guest_access and (
        allowed_users or allowed_groups
    ):
        raise ValueError(
            "Guest shares cannot also restrict access "
            "to named users or groups."
        )

    for username in allowed_users:
        try:
            pwd.getpwnam(username)
        except KeyError as exc:
            raise ValueError(
                f"The local user {username!r} does not exist."
            ) from exc

    for group_name in allowed_groups:
        try:
            grp.getgrnam(group_name)
        except KeyError as exc:
            raise ValueError(
                f"The local group {group_name!r} does not exist."
            ) from exc


def local_users() -> list[str]:
    result: list[str] = []

    for account in pwd.getpwall():
        if (
            account.pw_uid >= 1000
            and account.pw_shell
            not in {
                "/usr/sbin/nologin",
                "/bin/false",
            }
        ):
            result.append(account.pw_name)

    return sorted(set(result), key=str.casefold)


def local_groups() -> list[str]:
    return sorted(
        {
            group.gr_name
            for group in grp.getgrall()
            if group.gr_gid >= 1000
        },
        key=str.casefold,
    )


def detected_local_networks() -> list[str]:
    result = subprocess.run(
        ["ip", "-j", "-4", "route", "show", "scope", "link"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    if result.returncode != 0:
        return []

    try:
        routes = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []

    networks: set[ipaddress.IPv4Network] = set()

    for route in routes:
        if not isinstance(route, dict):
            continue

        destination = str(
            route.get("dst", "")
        ).strip()

        if not destination:
            continue

        try:
            network = ipaddress.ip_network(
                destination,
                strict=False,
            )
        except ValueError:
            continue

        if not isinstance(
            network,
            ipaddress.IPv4Network,
        ):
            continue

        if (
            network.is_loopback
            or network.is_link_local
        ):
            continue

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


def split_names(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]
