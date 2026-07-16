from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from linuxeasyconfig.core.config.audit_log import AuditLog
from linuxeasyconfig.core.config.base import ConfigurationDocument
from linuxeasyconfig.core.config.writer import ConfigurationWriter

from .samba_share import (
    STATE_PATH,
    detected_local_networks,
    load_hosted_shares,
    validate_share_values,
)


MODULE_ID = "org.linuxeasyconfig.mounts"
BACKUP_ROOT = Path("/var/lib/linuxeasyconfig/backups")
AUDIT_PATH = Path("/var/lib/linuxeasyconfig/audit.jsonl")
SMB_CONF_PATH = Path("/etc/samba/smb.conf")
LEC_INCLUDE_PATH = Path("/etc/samba/lec-shares.conf")


class RenderedConfiguration(ConfigurationDocument):
    def __init__(self, text: str) -> None:
        self._text = text

    def render(self) -> str:
        return (
            self._text
            if self._text.endswith("\n")
            else self._text + "\n"
        )


def install_samba_server(
    *,
    configure_firewall: bool,
) -> str:
    _run(
        ["apt-get", "update"],
        timeout=600,
        environment={
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )
    _run(
        [
            "apt-get",
            "install",
            "-y",
            "samba",
        ],
        timeout=900,
        environment={
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )

    _ensure_include_present()

    _run(
        ["systemctl", "enable", "--now", "smbd"],
        timeout=60,
    )

    if configure_firewall:
        _configure_local_firewall()

    return (
        "Samba was installed and its file-sharing "
        "service is running."
    )


def save_hosted_share(
    *,
    original_name: str,
    name: str,
    path: str,
    comment: str,
    read_only: bool,
    guest_access: bool,
    allowed_users: list[str],
    allowed_groups: list[str],
    local_network_only: bool,
    enabled: bool,
) -> str:
    name = name.strip()
    path = path.strip()
    comment = comment.strip()
    allowed_users = _clean_names(allowed_users)
    allowed_groups = _clean_names(allowed_groups)

    validate_share_values(
        name=name,
        path=path,
        comment=comment,
        guest_access=guest_access,
        allowed_users=allowed_users,
        allowed_groups=allowed_groups,
    )

    shares = [
        _share_to_dict(share)
        for share in load_hosted_shares()
    ]

    editing = bool(original_name.strip())
    original_key = original_name.strip().casefold()
    new_key = name.casefold()

    existing_index: int | None = None

    for index, share in enumerate(shares):
        share_key = str(share["name"]).casefold()

        if share_key == original_key and editing:
            existing_index = index
            continue

        if share_key == new_key:
            raise ValueError(
                f"A Samba share named {name!r} already exists."
            )

    item = {
        "name": name,
        "path": path,
        "comment": comment,
        "read_only": bool(read_only),
        "guest_access": bool(guest_access),
        "allowed_users": allowed_users,
        "allowed_groups": allowed_groups,
        "local_network_only": bool(
            local_network_only
        ),
        "enabled": bool(enabled),
    }

    if editing:
        if existing_index is None:
            raise ValueError(
                "The original share could not be found."
            )
        shares[existing_index] = item
    else:
        shares.append(item)

    _write_configuration(shares)

    verb = "Updated" if editing else "Created"
    return f"{verb} Samba share {name!r}."


def remove_hosted_share(
    *,
    name: str,
) -> str:
    key = name.strip().casefold()
    shares = [
        _share_to_dict(share)
        for share in load_hosted_shares()
    ]
    updated = [
        share
        for share in shares
        if str(share["name"]).casefold() != key
    ]

    if len(updated) == len(shares):
        raise ValueError(
            "The selected Samba share could not be found."
        )

    _write_configuration(updated)
    return f"Removed Samba share {name!r}."


def set_samba_password(
    *,
    username: str,
    password: str,
) -> str:
    username = username.strip()

    if not username:
        raise ValueError(
            "Choose a local user."
        )

    if not password:
        raise ValueError(
            "Enter a Samba password."
        )

    if "\n" in password or "\r" in password:
        raise ValueError(
            "The Samba password contains invalid characters."
        )

    result = subprocess.run(
        ["smbpasswd", "-s", "-a", username],
        input=password + "\n" + password + "\n",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "smbpasswd failed."
        )
        raise RuntimeError(message)

    return (
        f"Samba access was enabled for local user "
        f"{username!r}."
    )


def _write_configuration(
    shares: list[dict[str, Any]],
) -> None:
    _ensure_samba_installed()

    include_text = _render_include(shares)
    main_text = SMB_CONF_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )
    new_main_text = _with_include(main_text)

    _validate_combined_configuration(
        main_text=new_main_text,
        include_text=include_text,
    )

    writer = _writer()

    writer.write(
        module_id=MODULE_ID,
        destination=LEC_INCLUDE_PATH,
        document=RenderedConfiguration(include_text),
    )
    os.chmod(LEC_INCLUDE_PATH, 0o644)

    if new_main_text != main_text:
        writer.write(
            module_id=MODULE_ID,
            destination=SMB_CONF_PATH,
            document=RenderedConfiguration(
                new_main_text
            ),
        )
        os.chmod(SMB_CONF_PATH, 0o644)

    state_text = json.dumps(
        {
            "format_version": 1,
            "shares": sorted(
                shares,
                key=lambda item: str(
                    item["name"]
                ).casefold(),
            ),
        },
        indent=2,
    ) + "\n"

    STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(STATE_PATH.parent, 0o755)

    writer.write(
        module_id=MODULE_ID,
        destination=STATE_PATH,
        document=RenderedConfiguration(state_text),
    )
    os.chmod(STATE_PATH, 0o644)

    _run(
        ["testparm", "-s", str(SMB_CONF_PATH)],
        timeout=30,
    )
    _run(
        ["systemctl", "reload", "smbd"],
        timeout=60,
    )


def _ensure_include_present() -> None:
    if not LEC_INCLUDE_PATH.exists():
        LEC_INCLUDE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        LEC_INCLUDE_PATH.write_text(
            "# Managed by Linux Easy Config\n",
            encoding="utf-8",
        )
        os.chmod(LEC_INCLUDE_PATH, 0o644)

    current = SMB_CONF_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )
    updated = _with_include(current)

    _validate_combined_configuration(
        main_text=updated,
        include_text=LEC_INCLUDE_PATH.read_text(
            encoding="utf-8",
            errors="replace",
        ),
    )

    if updated != current:
        _writer().write(
            module_id=MODULE_ID,
            destination=SMB_CONF_PATH,
            document=RenderedConfiguration(updated),
        )
        os.chmod(SMB_CONF_PATH, 0o644)


def _render_include(
    shares: list[dict[str, Any]],
) -> str:
    lines = [
        "# Managed by Linux Easy Config",
        "# Do not edit this file manually.",
        "",
    ]
    local_networks = detected_local_networks()

    for share in sorted(
        shares,
        key=lambda item: str(
            item["name"]
        ).casefold(),
    ):
        if not bool(share.get("enabled", True)):
            continue

        name = str(share["name"])
        lines.append(f"[{name}]")
        lines.append(
            f"    path = {share['path']}"
        )

        comment = str(
            share.get("comment", "")
        ).strip()
        if comment:
            lines.append(
                f"    comment = {comment}"
            )

        read_only = bool(
            share.get("read_only", True)
        )
        guest = bool(
            share.get("guest_access", False)
        )
        users = [
            str(value)
            for value in share.get(
                "allowed_users",
                [],
            )
        ]
        groups = [
            str(value)
            for value in share.get(
                "allowed_groups",
                [],
            )
        ]

        lines.append(
            "    browseable = yes"
        )
        lines.append(
            "    read only = "
            + ("yes" if read_only else "no")
        )
        lines.append(
            "    guest ok = "
            + ("yes" if guest else "no")
        )

        if guest:
            lines.append(
                "    guest only = yes"
            )
        elif users or groups:
            valid_users = users + [
                f"@{group}"
                for group in groups
            ]
            lines.append(
                "    valid users = "
                + " ".join(valid_users)
            )

        if bool(
            share.get(
                "local_network_only",
                True,
            )
        ):
            if not local_networks:
                raise ValueError(
                    "LEC could not detect the local network. "
                    "Disable local-network restriction or "
                    "connect this computer to the intended "
                    "network before saving."
                )
            lines.append(
                "    hosts allow = "
                + " ".join(local_networks)
                + " 127.0.0.1"
            )
            lines.append(
                "    hosts deny = 0.0.0.0/0"
            )

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _with_include(current: str) -> str:
    include_line = (
        f"include = {LEC_INCLUDE_PATH}"
    )

    if any(
        line.strip() == include_line
        for line in current.splitlines()
    ):
        return current

    text = current
    if text and not text.endswith("\n"):
        text += "\n"
    if text and not text.endswith("\n\n"):
        text += "\n"

    return (
        text
        + "# Linux Easy Config hosted shares\n"
        + include_line
        + "\n"
    )


def _validate_combined_configuration(
    *,
    main_text: str,
    include_text: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="lec-samba-"
    ) as temporary_directory:
        root = Path(temporary_directory)
        temporary_include = (
            root / "lec-shares.conf"
        )
        temporary_main = root / "smb.conf"

        temporary_include.write_text(
            include_text,
            encoding="utf-8",
        )

        temporary_main.write_text(
            main_text.replace(
                str(LEC_INCLUDE_PATH),
                str(temporary_include),
            ),
            encoding="utf-8",
        )

        _run(
            [
                "testparm",
                "-s",
                str(temporary_main),
            ],
            timeout=30,
        )


def _configure_local_firewall() -> None:
    if subprocess.run(
        ["which", "ufw"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    ).returncode != 0:
        return

    networks = detected_local_networks()

    for network in networks:
        _run(
            [
                "ufw",
                "allow",
                "from",
                network,
                "to",
                "any",
                "app",
                "Samba",
            ],
            timeout=60,
            allow_failure=True,
        )


def _ensure_samba_installed() -> None:
    if not SMB_CONF_PATH.is_file():
        raise RuntimeError(
            "Samba is not installed. Install the "
            "Samba server before creating shares."
        )


def _share_to_dict(share: Any) -> dict[str, Any]:
    return {
        "name": share.name,
        "path": share.path,
        "comment": share.comment,
        "read_only": share.read_only,
        "guest_access": share.guest_access,
        "allowed_users": list(
            share.allowed_users
        ),
        "allowed_groups": list(
            share.allowed_groups
        ),
        "local_network_only": (
            share.local_network_only
        ),
        "enabled": share.enabled,
    }


def _clean_names(
    values: list[str],
) -> list[str]:
    return sorted(
        {
            value.strip()
            for value in values
            if value.strip()
        },
        key=str.casefold,
    )


def _writer() -> ConfigurationWriter:
    return ConfigurationWriter(
        backup_root=BACKUP_ROOT,
        audit_log=AuditLog(AUDIT_PATH),
    )


def _run(
    command: list[str],
    *,
    timeout: int,
    environment: dict[str, str] | None = None,
    allow_failure: bool = False,
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

    if result.returncode == 0 or allow_failure:
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
