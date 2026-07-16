from __future__ import annotations

import json
import os
import pwd
import subprocess
from pathlib import Path
from typing import Any


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
    result = subprocess.run(
        ["who", "--ips"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    rows: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[1].startswith("pts/"):
            rows.append({
                "user": fields[0],
                "terminal": fields[1],
                "login": " ".join(fields[2:4]),
                "address": fields[-1].strip("()"),
            })
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
