from __future__ import annotations

import json
import os
import pwd
import re
import subprocess
from pathlib import Path
from typing import Any

from .vnc import (
    VNC_SNAPSHOT_PATH,
    VNC_STATE_PATH,
    dependency_status,
    load_vnc_configuration,
    unit_name,
    validate_vnc_settings,
)


SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/remote-access/status.json"
)
DROP_IN_PATH = Path(
    "/etc/ssh/sshd_config.d/99-linuxeasyconfig.conf"
)


def install_openssh() -> str:
    environment = os.environ.copy()
    environment["DEBIAN_FRONTEND"] = "noninteractive"
    _run(["apt-get", "update"], 600, environment)
    _run(
        ["apt-get", "install", "-y", "openssh-server"],
        900,
        environment,
    )
    _run(["systemctl", "enable", "--now", "ssh"], 60)
    refresh_snapshot()
    return "OpenSSH Server was installed and started."


def save_settings(
    *,
    port: int,
    password_authentication: bool,
    public_key_authentication: bool,
    permit_root_login: str,
) -> str:
    if not 1 <= port <= 65535:
        raise ValueError("The SSH port must be between 1 and 65535.")
    if permit_root_login not in {
        "no",
        "prohibit-password",
        "yes",
    }:
        raise ValueError("The root-login policy is invalid.")
    if not password_authentication and not public_key_authentication:
        raise ValueError(
            "At least one authentication method must remain enabled."
        )

    text = (
        "# Managed by Linux Easy Config\n"
        f"Port {port}\n"
        f"PasswordAuthentication {'yes' if password_authentication else 'no'}\n"
        f"PubkeyAuthentication {'yes' if public_key_authentication else 'no'}\n"
        f"PermitRootLogin {permit_root_login}\n"
    )
    DROP_IN_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DROP_IN_PATH.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, 0o644)
    _run(["sshd", "-t", "-f", str(temporary)], 30)
    temporary.replace(DROP_IN_PATH)
    _run(["sshd", "-t"], 30)
    _run(["systemctl", "restart", "ssh"], 60)
    refresh_snapshot()
    return "SSH settings were saved and the service was restarted."


def set_service_enabled(*, enabled: bool) -> str:
    command = (
        ["systemctl", "enable", "--now", "ssh"]
        if enabled
        else ["systemctl", "disable", "--now", "ssh"]
    )
    _run(command, 60)
    refresh_snapshot()
    return (
        "SSH service was enabled and started."
        if enabled
        else "SSH service was stopped and disabled."
    )


def add_authorized_key(*, username: str, key: str) -> str:
    account = pwd.getpwnam(username)
    key = key.strip()
    if not key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
        raise ValueError("Enter a supported OpenSSH public key.")
    home = Path(account.pw_dir)
    ssh_dir = home / ".ssh"
    authorized = ssh_dir / "authorized_keys"
    ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    existing = (
        authorized.read_text(encoding="utf-8", errors="replace").splitlines()
        if authorized.is_file()
        else []
    )
    if key not in existing:
        existing.append(key)
    authorized.write_text("\n".join(existing).rstrip() + "\n", encoding="utf-8")
    os.chown(ssh_dir, account.pw_uid, account.pw_gid)
    os.chown(authorized, account.pw_uid, account.pw_gid)
    os.chmod(ssh_dir, 0o700)
    os.chmod(authorized, 0o600)
    return f"Authorized key added for {username}."


def refresh_snapshot() -> str:
    installed = shutil_which("sshd")
    active = _run_output(["systemctl", "is-active", "ssh"]) == "active"
    settings = _effective_settings() if installed else {}
    sessions = _sessions()
    payload = {
        "installed": installed,
        "active": active,
        "port": int(settings.get("port", "22")),
        "password_authentication": settings.get(
            "passwordauthentication", "no"
        ) == "yes",
        "public_key_authentication": settings.get(
            "pubkeyauthentication", "yes"
        ) == "yes",
        "permit_root_login": settings.get("permitrootlogin", "no"),
        "sessions": sessions,
    }
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(SNAPSHOT_PATH.parent, 0o755)
    temporary = SNAPSHOT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o644)
    temporary.replace(SNAPSHOT_PATH)
    return "Remote-access status was refreshed."



def install_tigervnc() -> str:
    environment = os.environ.copy()
    environment["DEBIAN_FRONTEND"] = "noninteractive"

    _run(
        ["apt-get", "update"],
        600,
        environment,
    )
    _run(
        [
            "apt-get",
            "install",
            "-y",
            "tigervnc-standalone-server",
            "tigervnc-tools",
            "dbus-x11",
        ],
        900,
        environment,
    )

    refresh_vnc_snapshot()

    return (
        "TigerVNC Server and its supporting tools "
        "were installed."
    )


def save_vnc_settings(
    *,
    username: str,
    display: int,
    geometry: str,
    depth: int,
    startup_command: str,
    password: str,
    enabled: bool,
) -> str:
    validate_vnc_settings(
        username=username,
        display=display,
        geometry=geometry,
        depth=depth,
        startup_command=startup_command,
    )

    account = pwd.getpwnam(username)
    previous = load_vnc_configuration()

    if previous is not None:
        previous_unit = unit_name(
            previous.username
        )
        _run(
            [
                "systemctl",
                "disable",
                "--now",
                previous_unit,
            ],
            60,
        )

    home = Path(account.pw_dir)
    vnc_dir = home / ".vnc"
    vnc_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chown(
        vnc_dir,
        account.pw_uid,
        account.pw_gid,
    )
    os.chmod(vnc_dir, 0o700)

    if password:
        _write_vnc_password(
            account=account,
            password=password,
            destination=vnc_dir / "passwd",
        )
    elif not (vnc_dir / "passwd").is_file():
        raise ValueError(
            "Set a VNC password before enabling "
            "the first VNC session."
        )

    xstartup = vnc_dir / "xstartup"
    xstartup.write_text(
        "#!/bin/sh\n"
        "unset SESSION_MANAGER\n"
        "unset DBUS_SESSION_BUS_ADDRESS\n"
        f"exec {startup_command.strip()}\n",
        encoding="utf-8",
    )
    os.chown(
        xstartup,
        account.pw_uid,
        account.pw_gid,
    )
    os.chmod(xstartup, 0o700)

    unit = _render_vnc_unit(
        username=username,
        home=str(home),
        display=display,
        geometry=geometry.strip(),
        depth=depth,
    )
    unit_path = (
        Path("/etc/systemd/system")
        / unit_name(username)
    )
    unit_path.write_text(
        unit,
        encoding="utf-8",
    )
    os.chmod(unit_path, 0o644)

    VNC_STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(
        VNC_STATE_PATH.parent,
        0o755,
    )
    state = {
        "username": username,
        "display": display,
        "geometry": geometry.strip(),
        "depth": depth,
        "startup_command": (
            startup_command.strip()
        ),
        "enabled": bool(enabled),
    }
    temporary = VNC_STATE_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o644)
    temporary.replace(VNC_STATE_PATH)
    os.chmod(VNC_STATE_PATH, 0o644)

    _run(
        ["systemctl", "daemon-reload"],
        60,
    )

    if enabled:
        _run(
            [
                "systemctl",
                "enable",
                "--now",
                unit_name(username),
            ],
            90,
        )

    refresh_vnc_snapshot()

    return (
        f"TigerVNC was configured for {username} "
        f"on display :{display} (TCP port "
        f"{5900 + display})."
    )


def set_vnc_service_enabled(
    *,
    enabled: bool,
) -> str:
    configuration = load_vnc_configuration()

    if configuration is None:
        raise ValueError(
            "Configure a VNC session first."
        )

    command = [
        "systemctl",
        (
            "enable"
            if enabled
            else "disable"
        ),
        "--now",
        unit_name(configuration.username),
    ]
    _run(command, 90)

    state = json.loads(
        VNC_STATE_PATH.read_text(
            encoding="utf-8"
        )
    )
    state["enabled"] = bool(enabled)
    VNC_STATE_PATH.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(VNC_STATE_PATH, 0o644)

    refresh_vnc_snapshot()

    return (
        "TigerVNC was enabled and started."
        if enabled
        else "TigerVNC was stopped and disabled."
    )


def refresh_vnc_snapshot() -> str:
    configuration = load_vnc_configuration()
    installed = dependency_status()[
        "tigervncserver"
    ]

    active = False
    enabled = False
    detail = ""

    if configuration is not None:
        service = unit_name(
            configuration.username
        )
        active = (
            _run_output(
                [
                    "systemctl",
                    "is-active",
                    service,
                ]
            )
            == "active"
        )
        enabled = (
            _run_output(
                [
                    "systemctl",
                    "is-enabled",
                    service,
                ]
            )
            == "enabled"
        )

        detail_result = subprocess.run(
            [
                "systemctl",
                "status",
                service,
                "--no-pager",
                "--lines=12",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        detail = (
            detail_result.stdout.strip()
            or detail_result.stderr.strip()
        )

    payload = {
        "installed": installed,
        "configured": (
            configuration is not None
        ),
        "active": active,
        "enabled": enabled,
        "configuration": (
            {
                "username": (
                    configuration.username
                ),
                "display": (
                    configuration.display
                ),
                "port": configuration.port,
                "geometry": (
                    configuration.geometry
                ),
                "depth": configuration.depth,
                "startup_command": (
                    configuration.startup_command
                ),
            }
            if configuration is not None
            else None
        ),
        "detail": detail,
    }

    VNC_SNAPSHOT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(
        VNC_SNAPSHOT_PATH.parent,
        0o755,
    )
    temporary = (
        VNC_SNAPSHOT_PATH.with_suffix(".tmp")
    )
    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o644)
    temporary.replace(VNC_SNAPSHOT_PATH)
    os.chmod(VNC_SNAPSHOT_PATH, 0o644)

    return "TigerVNC status was refreshed."


def _write_vnc_password(
    *,
    account: pwd.struct_passwd,
    password: str,
    destination: Path,
) -> None:
    if len(password) < 6:
        raise ValueError(
            "The VNC password must contain at least "
            "six characters."
        )

    if any(
        character in password
        for character in "\0\n\r"
    ):
        raise ValueError(
            "The VNC password contains invalid characters."
        )

    result = subprocess.run(
        ["tigervncpasswd", "-f"],
        input=(password + "\n").encode("utf-8"),
        capture_output=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        message = (
            result.stderr.decode(
                "utf-8",
                errors="replace",
            ).strip()
            or "tigervncpasswd failed."
        )
        raise RuntimeError(message)

    destination.write_bytes(result.stdout)
    os.chown(
        destination,
        account.pw_uid,
        account.pw_gid,
    )
    os.chmod(destination, 0o600)


def _render_vnc_unit(
    *,
    username: str,
    home: str,
    display: int,
    geometry: str,
    depth: int,
) -> str:
    return (
        "[Unit]\n"
        "Description=LEC TigerVNC session for "
        f"{username}\n"
        "After=network.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"User={username}\n"
        f"WorkingDirectory={home}\n"
        f"Environment=HOME={home}\n"
        "ExecStart=/usr/bin/tigervncserver "
        f":{display} -fg "
        f"-geometry {geometry} "
        f"-depth {depth} "
        "-localhost no "
        "-SecurityTypes VncAuth,TLSVnc\n"
        "ExecStop=/usr/bin/tigervncserver "
        f"-kill :{display}\n"
        "Restart=on-failure\n"
        "RestartSec=5\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )

def _effective_settings() -> dict[str, str]:
    result = subprocess.run(
        ["sshd", "-T"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    settings: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key and value:
            settings[key] = value.strip()
    return settings


def _sessions() -> list[dict[str, str]]:
    rows = _sessions_from_logind()

    if rows:
        return rows

    return _sessions_from_who()


def _sessions_from_logind() -> list[dict[str, str]]:
    result = subprocess.run(
        [
            "loginctl",
            "list-sessions",
            "--no-legend",
            "--no-pager",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    if result.returncode != 0:
        return []

    rows: list[dict[str, str]] = []

    for line in result.stdout.splitlines():
        fields = line.split()

        if not fields:
            continue

        session_id = fields[0]

        details = subprocess.run(
            [
                "loginctl",
                "show-session",
                session_id,
                "--no-pager",
                "--property=Name",
                "--property=TTY",
                "--property=Remote",
                "--property=RemoteHost",
                "--property=Timestamp",
                "--property=Service",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if details.returncode != 0:
            continue

        values: dict[str, str] = {}

        for raw_line in details.stdout.splitlines():
            key, separator, value = raw_line.partition("=")

            if separator:
                values[key] = value.strip()

        if values.get("Remote", "").casefold() != "yes":
            continue

        service = values.get("Service", "").casefold()
        tty = values.get("TTY", "")

        if service not in {"sshd", "ssh"} and not tty.startswith("pts/"):
            continue

        rows.append(
            {
                "user": values.get("Name", "Unknown"),
                "terminal": tty or "No terminal",
                "login": values.get("Timestamp", "Unknown"),
                "address": values.get("RemoteHost", "Unknown"),
            }
        )

    return rows


def _sessions_from_who() -> list[dict[str, str]]:
    result = subprocess.run(
        ["who", "--ips"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    if result.returncode != 0:
        result = subprocess.run(
            ["who"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    rows: list[dict[str, str]] = []

    for line in result.stdout.splitlines():
        fields = line.split()

        if len(fields) < 4:
            continue

        terminal = fields[1]

        if not terminal.startswith(("pts/", "tty")):
            continue

        address = ""

        if fields[-1].startswith("(") and fields[-1].endswith(")"):
            address = fields[-1].strip("()")
        elif len(fields) >= 5:
            address = fields[-1]

        if not address or address in {":0", ":1"}:
            continue

        rows.append(
            {
                "user": fields[0],
                "terminal": terminal,
                "login": " ".join(fields[2:4]),
                "address": address,
            }
        )

    return rows


def _run_output(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    return result.stdout.strip()


def shutil_which(name: str) -> bool:
    import shutil
    return shutil.which(name) is not None


def _run(
    command: list[str],
    timeout: int,
    environment: dict[str, str] | None = None,
) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=environment,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"{command[0]} failed."
        )
