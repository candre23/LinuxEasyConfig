from __future__ import annotations

import json
import os
import pwd
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VNC_STATE_PATH = Path(
    "/etc/linuxeasyconfig/remote-access/vnc.json"
)
VNC_SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/remote-access/vnc-status.json"
)

_GEOMETRY_PATTERN = re.compile(
    r"^(?P<width>\d{3,5})x(?P<height>\d{3,5})$"
)


@dataclass(frozen=True)
class VNCConfiguration:
    username: str
    display: int
    port: int
    geometry: str
    depth: int
    startup_command: str
    enabled: bool


def dependency_status() -> dict[str, bool]:
    return {
        "tigervncserver": (
            shutil.which("tigervncserver") is not None
        ),
        "tigervncpasswd": (
            shutil.which("tigervncpasswd") is not None
        ),
    }


def load_vnc_configuration() -> VNCConfiguration | None:
    if not VNC_STATE_PATH.is_file():
        return None

    try:
        value = json.loads(
            VNC_STATE_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(value, dict):
        return None

    try:
        display = int(value.get("display", 1))
        return VNCConfiguration(
            username=str(value["username"]),
            display=display,
            port=5900 + display,
            geometry=str(value.get("geometry", "1920x1080")),
            depth=int(value.get("depth", 24)),
            startup_command=str(
                value.get(
                    "startup_command",
                    (
                        "dbus-run-session -- "
                        "gnome-session --session=ubuntu"
                    ),
                )
            ),
            enabled=bool(value.get("enabled", False)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def load_vnc_snapshot() -> dict[str, Any]:
    if not VNC_SNAPSHOT_PATH.is_file():
        configuration = load_vnc_configuration()
        return {
            "installed": dependency_status()[
                "tigervncserver"
            ],
            "configured": configuration is not None,
            "active": False,
            "configuration": (
                configuration.__dict__
                if configuration is not None
                else None
            ),
        }

    try:
        value = json.loads(
            VNC_SNAPSHOT_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        return {}

    return value if isinstance(value, dict) else {}


def available_users() -> list[str]:
    return sorted(
        {
            account.pw_name
            for account in pwd.getpwall()
            if (
                account.pw_uid >= 1000
                and Path(account.pw_dir).is_dir()
                and account.pw_shell
                not in {
                    "/usr/sbin/nologin",
                    "/bin/false",
                }
            )
        },
        key=str.casefold,
    )


def validate_vnc_settings(
    *,
    username: str,
    display: int,
    geometry: str,
    depth: int,
    startup_command: str,
) -> None:
    try:
        pwd.getpwnam(username)
    except KeyError as exc:
        raise ValueError(
            "The selected Linux user does not exist."
        ) from exc

    if not 1 <= display <= 99:
        raise ValueError(
            "The VNC display number must be between 1 and 99."
        )

    match = _GEOMETRY_PATTERN.fullmatch(
        geometry.strip()
    )
    if match is None:
        raise ValueError(
            "The resolution must use WIDTHxHEIGHT, "
            "for example 1920x1080."
        )

    width = int(match.group("width"))
    height = int(match.group("height"))

    if width < 640 or height < 480:
        raise ValueError(
            "The VNC resolution must be at least 640x480."
        )

    if depth not in {16, 24, 32}:
        raise ValueError(
            "The selected color depth is invalid."
        )

    command = startup_command.strip()

    if not command:
        raise ValueError(
            "Enter a desktop startup command."
        )

    if any(
        character in command
        for character in "\0\n\r"
    ):
        raise ValueError(
            "The startup command contains invalid characters."
        )


def unit_name(username: str) -> str:
    safe = re.sub(
        r"[^A-Za-z0-9_.@-]+",
        "-",
        username,
    )
    return f"lec-vnc-{safe}.service"
