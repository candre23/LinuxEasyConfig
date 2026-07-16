from __future__ import annotations

import grp
import os
import re
import shutil
from dataclasses import dataclass


_MOUNT_POINT_PATTERN = re.compile(r"^/[^\0\n\r]*$")


@dataclass(frozen=True)
class DependencyStatus:
    protocol: str
    available: bool
    helper: str
    install_command: str


@dataclass(frozen=True)
class NetworkSharePreview:
    protocol: str
    source: str
    mountpoint: str
    filesystem: str
    options: tuple[str, ...]
    fstab_line: str
    credential_path: str | None = None
    credential_text: str | None = None


def dependency_status(protocol: str) -> DependencyStatus:
    normalized = protocol.strip().lower()

    if normalized == "smb":
        helper = "mount.cifs"
        return DependencyStatus(
            protocol="smb",
            available=shutil.which(helper) is not None,
            helper=helper,
            install_command="sudo apt install cifs-utils",
        )

    if normalized == "nfs":
        helper = "mount.nfs"
        return DependencyStatus(
            protocol="nfs",
            available=shutil.which(helper) is not None,
            helper=helper,
            install_command="sudo apt install nfs-common",
        )

    raise ValueError(f"Unsupported network protocol: {protocol}")


def build_smb_preview(
    *,
    server: str,
    share: str,
    mountpoint: str,
    username: str,
    password: str,
    domain: str,
    guest: bool,
    read_only: bool,
    startup_mode: str,
    existing_credential_path: str = "",
    local_group: str = "",
    group_access: str = "read",
) -> NetworkSharePreview:
    server = _clean_host(server)
    share_name, subdirectory = _split_smb_share_path(share)
    mountpoint = _validate_mountpoint(mountpoint)

    source = f"//{server}/{share_name}"
    options = _base_options(
        startup_mode=startup_mode,
        read_only=read_only,
    )

    credential_path: str | None = None
    credential_text: str | None = None

    if guest:
        options.append("guest")
    elif username.strip():
        safe_name = _safe_filename(f"{server}-{share_name}")
        credential_path = (
            f"/etc/linuxeasyconfig/credentials/{safe_name}.cred"
        )
        options.append(f"credentials={credential_path}")

        credential_lines = [
            f"username={username.strip()}",
            f"password={password}",
        ]
        if domain.strip():
            credential_lines.append(f"domain={domain.strip()}")

        credential_text = "\n".join(credential_lines) + "\n"
    elif existing_credential_path:
        credential_path = existing_credential_path
        options.append(f"credentials={credential_path}")
    else:
        options.append("guest")

    if subdirectory:
        options.append(
            f"prefixpath={_escape_mount_option(subdirectory)}"
        )

    if local_group.strip():
        try:
            group = grp.getgrnam(
                local_group.strip()
            )
        except KeyError as exc:
            raise ValueError(
                f"The local group {local_group.strip()} "
                "does not exist."
            ) from exc

        access = group_access.strip().lower()

        if read_only or access == "read":
            file_mode = "0640"
            directory_mode = "0750"
        elif access == "write":
            file_mode = "0660"
            directory_mode = "0770"
        else:
            raise ValueError(
                "The selected local group access policy "
                "is invalid."
            )

        options.extend(
            [
                f"gid={group.gr_gid}",
                "forcegid",
                f"file_mode={file_mode}",
                f"dir_mode={directory_mode}",
            ]
        )

    options.extend(["iocharset=utf8", "vers=3.0"])

    return NetworkSharePreview(
        protocol="smb",
        source=source,
        mountpoint=mountpoint,
        filesystem="cifs",
        options=tuple(options),
        fstab_line=_render_fstab_line(
            source,
            mountpoint,
            "cifs",
            options,
        ),
        credential_path=credential_path,
        credential_text=credential_text,
    )


def build_nfs_preview(
    *,
    server: str,
    export_path: str,
    mountpoint: str,
    nfs_version: str,
    read_only: bool,
    startup_mode: str,
) -> NetworkSharePreview:
    server = _clean_host(server)
    export_path = export_path.strip()

    if not export_path.startswith("/"):
        raise ValueError(
            "The NFS exported path must begin with /."
        )

    if any(character in export_path for character in "\0\n\r"):
        raise ValueError(
            "The NFS exported path contains invalid characters."
        )

    mountpoint = _validate_mountpoint(mountpoint)

    options = _base_options(
        startup_mode=startup_mode,
        read_only=read_only,
    )

    version = nfs_version.strip()
    if version and version.lower() != "automatic":
        options.append(f"nfsvers={version}")

    source = f"{server}:{export_path}"

    return NetworkSharePreview(
        protocol="nfs",
        source=source,
        mountpoint=mountpoint,
        filesystem="nfs",
        options=tuple(options),
        fstab_line=_render_fstab_line(
            source,
            mountpoint,
            "nfs",
            options,
        ),
    )


def suggested_mountpoint(
    *,
    protocol: str,
    server: str,
    remote_name: str,
) -> str:
    del protocol
    server_name = _safe_filename(server) or "server"
    remote = _safe_filename(
        remote_name.strip().strip("/")
    ) or "share"
    return f"/mnt/{server_name}-{remote}"


def _base_options(
    *,
    startup_mode: str,
    read_only: bool,
) -> list[str]:
    mode = startup_mode.strip().lower()

    options = [
        "ro" if read_only else "rw",
        "_netdev",
        "nofail",
    ]

    if mode == "manual":
        options.append("noauto")
    elif mode == "startup":
        pass
    elif mode == "on-demand":
        options.extend(
            [
                "x-systemd.automount",
                "x-systemd.idle-timeout=60",
                "x-systemd.device-timeout=10s",
            ]
        )
    else:
        raise ValueError(f"Unknown startup mode: {startup_mode}")

    return options


def _render_fstab_line(
    source: str,
    mountpoint: str,
    filesystem: str,
    options: list[str],
) -> str:
    return (
        f"{_escape_fstab(source)} "
        f"{_escape_fstab(mountpoint)} "
        f"{filesystem} "
        f"{','.join(options)} "
        "0 0"
    )


def _escape_fstab(value: str) -> str:
    return (
        value.replace("\\", "\\134")
        .replace(" ", "\\040")
        .replace("\t", "\\011")
    )


def _escape_mount_option(value: str) -> str:
    return (
        value.replace("\\", "\\134")
        .replace(",", "\\054")
        .replace(" ", "\\040")
        .replace("\t", "\\011")
    )


def _clean_host(value: str) -> str:
    host = value.strip()

    if host.startswith("//"):
        host = host[2:]

    host = host.rstrip("/")

    if not host:
        raise ValueError("Enter a server name or IP address.")

    if any(character in host for character in "\0\n\r\t "):
        raise ValueError(
            "The server name contains invalid characters."
        )

    return host


def _split_smb_share_path(value: str) -> tuple[str, str]:
    cleaned = value.strip().strip("/")

    if not cleaned:
        raise ValueError("Enter the SMB share name.")

    if any(character in cleaned for character in "\0\n\r"):
        raise ValueError(
            "The SMB share path contains invalid characters."
        )

    components = [
        component
        for component in cleaned.split("/")
        if component
    ]

    share_name = components[0]
    subdirectory = "/".join(components[1:])
    return share_name, subdirectory


def _validate_mountpoint(value: str) -> str:
    mountpoint = os.path.normpath(value.strip())

    if not _MOUNT_POINT_PATTERN.fullmatch(mountpoint):
        raise ValueError(
            "The local mount point must be an absolute path."
        )

    if mountpoint == "/":
        raise ValueError(
            "The root directory cannot be used as a network mount point."
        )

    return mountpoint


def _safe_filename(value: str) -> str:
    text = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "-",
        value.strip(),
    )
    return text.strip("-.").lower()
