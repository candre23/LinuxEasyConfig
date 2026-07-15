from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from linuxeasyconfig.core.table_actions import TableAction
from linuxeasyconfig.core.table_provider import TableDataProvider


_PSEUDO_FILESYSTEMS = {
    "autofs", "binfmt_misc", "bpf", "cgroup", "cgroup2",
    "configfs", "debugfs", "devpts", "devtmpfs", "efivarfs",
    "fuse", "fuse.gvfsd-fuse", "fuse.portal", "fusectl",
    "hugetlbfs", "mqueue", "overlay", "proc", "pstore",
    "ramfs", "securityfs", "squashfs", "sysfs", "tmpfs",
    "tracefs",
}

_NETWORK_FILESYSTEMS = {
    "9p", "afs", "ceph", "cifs", "davfs", "davfs2",
    "fuse.sshfs", "glusterfs", "nfs", "nfs4", "smb3", "sshfs",
}

_IGNORED_MOUNT_PREFIXES = (
    "/snap/",
    "/run/snapd/",
    "/run/user/",
    "/proc/",
    "/sys/",
)


class MountsTableProvider(TableDataProvider):
    """Read active mounts and persistent fstab entries."""

    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []

    def columns(self):
        return [
            {"id": "mountpoint", "title": "Mount Point", "resize": "stretch"},
            {"id": "source", "title": "Source", "resize": "stretch"},
            {"id": "filesystem", "title": "Type", "alignment": "center"},
            {"id": "kind", "title": "Kind", "alignment": "center"},
            {"id": "status", "title": "Status", "alignment": "center"},
            {"id": "usage", "title": "Used", "alignment": "right"},
            {"id": "persistent", "title": "Persistent", "alignment": "center"},
        ]

    def rows(self):
        return tuple(self._rows)

    def refresh(self) -> None:
        persistent_entries = _read_fstab_entries()
        active_mounts = _read_mountinfo()
        rows: list[dict[str, Any]] = []
        active_mountpoints: set[str] = set()

        for mount in active_mounts:
            mountpoint = mount["mountpoint"]
            filesystem = mount["filesystem"]

            if filesystem in _PSEUDO_FILESYSTEMS:
                continue
            if mountpoint.startswith(_IGNORED_MOUNT_PREFIXES):
                continue

            source = mount["source"]
            options = mount["options"]
            persistent = _matching_fstab_entry(
                source=source,
                mountpoint=mountpoint,
                filesystem=filesystem,
                entries=persistent_entries,
            )
            active_mountpoints.add(os.path.normpath(mountpoint))

            rows.append(
                _build_active_row(
                    source=source,
                    mountpoint=mountpoint,
                    filesystem=filesystem,
                    options=options,
                    persistent=persistent,
                )
            )

        for entry in persistent_entries:
            mountpoint = str(entry["mountpoint"])
            normalized_mountpoint = os.path.normpath(mountpoint)

            if normalized_mountpoint in active_mountpoints:
                continue

            filesystem = str(entry["filesystem"])
            if filesystem in _PSEUDO_FILESYSTEMS:
                continue
            if mountpoint.startswith(_IGNORED_MOUNT_PREFIXES):
                continue

            rows.append(_build_inactive_row(entry))

        rows.sort(
            key=lambda row: (
                row["kind"] != "Network",
                row["status"] != "Mounted",
                str(row["mountpoint"]).casefold(),
            )
        )
        self._rows = rows

    def status_text(self) -> str:
        mounted_count = sum(
            row.get("status") == "Mounted"
            for row in self._rows
        )
        network_count = sum(
            row.get("kind") == "Network"
            for row in self._rows
        )
        return (
            f"{len(self._rows)} configured filesystems "
            f"({mounted_count} mounted, {network_count} network)"
        )

    @property
    def refresh_interval_ms(self) -> int:
        return 5000

    def actions_for_row(
        self,
        row: dict[str, Any] | None,
    ):
        if row is None:
            return ()

        mounted = bool(row.get("mounted", False))
        persistent = bool(row.get("persistent_bool", False))
        network = row.get("kind") == "Network"
        lec_managed = bool(row.get("lec_managed", False))

        return (
            TableAction(
                id="mount",
                label="Mount",
                enabled=not mounted and persistent,
            ),
            TableAction(
                id="unmount",
                label="Unmount",
                enabled=mounted and row.get("mountpoint") != "/",
            ),
            TableAction(
                id="modify",
                label="Modify",
                enabled=network and persistent and lec_managed,
            ),
            TableAction(
                id="remove",
                label="Remove",
                enabled=network and persistent and lec_managed,
            ),
        )


def _build_active_row(
    *,
    source: str,
    mountpoint: str,
    filesystem: str,
    options: tuple[str, ...],
    persistent: dict[str, Any] | None,
) -> dict[str, Any]:
    kind = (
        "Network"
        if _is_network_mount(source, filesystem)
        else "Local"
    )

    used_text = (
        "Not queried"
        if kind == "Network"
        else "Unavailable"
    )
    used_sort = -1.0
    total_bytes = used_bytes = free_bytes = None
    percent = None

    # statvfs/disk_usage can block indefinitely when a remote server
    # disappears. Never probe network filesystems during background
    # table refreshes; doing so could prevent LEC from closing cleanly.
    if kind == "Local":
        try:
            usage = shutil.disk_usage(mountpoint)
            total_bytes = usage.total
            used_bytes = usage.used
            free_bytes = usage.free
            percent = (
                (usage.used / usage.total) * 100
                if usage.total
                else 0.0
            )
            used_text = (
                f"{_format_bytes(usage.used)} / "
                f"{_format_bytes(usage.total)} "
                f"({percent:.1f}%)"
            )
            used_sort = percent
        except (OSError, PermissionError):
            pass

    persistent_bool = persistent is not None

    return {
        "_id": f"{source}\0{mountpoint}",
        "mountpoint": mountpoint,
        "source": source,
        "filesystem": filesystem,
        "kind": kind,
        "status": "Mounted",
        "status_sort": 1,
        "usage": used_text,
        "usage_sort": used_sort,
        "persistent": "Yes" if persistent_bool else "No",
        "persistent_bool": persistent_bool,
        "persistent_sort": 1 if persistent_bool else 0,
        "options": ", ".join(
            persistent.get("options", options)
            if persistent
            else options
        ),
        "option_list": tuple(
            persistent.get("options", options)
            if persistent
            else options
        ),
        "read_only": "ro" in options,
        "mounted": True,
        "lec_managed": bool(
            persistent and persistent.get("lec_managed", False)
        ),
        "credential_path": (
            persistent.get("credential_path", "")
            if persistent
            else ""
        ),
        "total_bytes": total_bytes,
        "used_bytes": used_bytes,
        "free_bytes": free_bytes,
        "percent": percent,
    }


def _build_inactive_row(
    entry: dict[str, Any],
) -> dict[str, Any]:
    source = str(entry["source"])
    mountpoint = str(entry["mountpoint"])
    filesystem = str(entry["filesystem"])
    options = tuple(entry.get("options", ()))
    kind = "Network" if _is_network_mount(source, filesystem) else "Local"

    return {
        "_id": f"{source}\0{mountpoint}",
        "mountpoint": mountpoint,
        "source": source,
        "filesystem": filesystem,
        "kind": kind,
        "status": "Not mounted",
        "status_sort": 0,
        "usage": "Not mounted",
        "usage_sort": -1.0,
        "persistent": "Yes",
        "persistent_bool": True,
        "persistent_sort": 1,
        "options": ", ".join(options),
        "option_list": options,
        "read_only": "ro" in options,
        "mounted": False,
        "lec_managed": bool(entry.get("lec_managed", False)),
        "credential_path": str(entry.get("credential_path", "")),
        "total_bytes": None,
        "used_bytes": None,
        "free_bytes": None,
        "percent": None,
    }


def _read_mountinfo() -> list[dict[str, Any]]:
    mounts: list[dict[str, Any]] = []

    try:
        lines = Path("/proc/self/mountinfo").read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return mounts

    for line in lines:
        left, separator, right = line.partition(" - ")
        if not separator:
            continue

        left_fields = left.split()
        right_fields = right.split()
        if len(left_fields) < 6 or len(right_fields) < 2:
            continue

        mountpoint = _unescape_mount_field(left_fields[4])
        mount_options = left_fields[5].split(",")
        filesystem = right_fields[0]
        source = _unescape_mount_field(right_fields[1])
        super_options = (
            right_fields[2].split(",")
            if len(right_fields) >= 3
            else []
        )

        mounts.append(
            {
                "mountpoint": mountpoint,
                "source": source,
                "filesystem": filesystem,
                "options": tuple(
                    dict.fromkeys(mount_options + super_options)
                ),
            }
        )

    return mounts


def _read_fstab_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    try:
        lines = Path("/etc/fstab").read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return entries

    lec_marker = False

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            lec_marker = False
            continue

        if line.startswith("#"):
            if line == "# Created by Linux Easy Config":
                lec_marker = True
            continue

        fields = line.split()
        if len(fields) < 3:
            lec_marker = False
            continue

        options = tuple(
            fields[3].split(",")
            if len(fields) >= 4
            else ()
        )
        credential_path = ""

        for option in options:
            if option.startswith("credentials="):
                credential_path = option.partition("=")[2]
                break

        entries.append(
            {
                "source": _unescape_fstab_field(fields[0]),
                "mountpoint": _unescape_fstab_field(fields[1]),
                "filesystem": fields[2],
                "options": options,
                "lec_managed": lec_marker,
                "credential_path": credential_path,
            }
        )
        lec_marker = False

    return entries


def _matching_fstab_entry(
    *,
    source: str,
    mountpoint: str,
    filesystem: str,
    entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    normalized_mountpoint = os.path.normpath(mountpoint)

    for entry in entries:
        if os.path.normpath(str(entry["mountpoint"])) == normalized_mountpoint:
            return entry

        if (
            entry["source"] == source
            and entry["filesystem"] in {filesystem, "auto"}
        ):
            return entry

    return None


def _is_network_mount(source: str, filesystem: str) -> bool:
    fs = filesystem.casefold()
    if fs in _NETWORK_FILESYSTEMS:
        return True
    if fs.startswith(("fuse.sshfs", "nfs")):
        return True
    return source.startswith("//") or ":" in source


def _unescape_mount_field(value: str) -> str:
    replacements = {
        "\\040": " ",
        "\\011": "\t",
        "\\012": "\n",
        "\\134": "\\",
    }
    for escaped, replacement in replacements.items():
        value = value.replace(escaped, replacement)
    return value


def _unescape_fstab_field(value: str) -> str:
    return _unescape_mount_field(value)


def _format_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    amount = float(max(value, 0))

    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return (
                f"{amount:.0f} {unit}"
                if unit == "B"
                else f"{amount:.1f} {unit}"
            )
        amount /= 1024

    return f"{amount:.1f} PB"
