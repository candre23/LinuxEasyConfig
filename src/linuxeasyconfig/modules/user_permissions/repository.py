from __future__ import annotations

import grp
import os
import pwd
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


_NOLOGIN_SHELLS = {
    "/usr/sbin/nologin",
    "/sbin/nologin",
    "/bin/false",
    "/usr/bin/false",
}


@dataclass(frozen=True)
class UserAccount:
    name: str
    uid: int
    gid: int
    primary_group: str
    home: str
    shell: str
    description: str
    account_type: str
    supplementary_groups: tuple[str, ...]

    @property
    def login_allowed(self) -> bool:
        return self.shell not in _NOLOGIN_SHELLS


@dataclass(frozen=True)
class LocalGroup:
    name: str
    gid: int
    group_type: str
    members: tuple[str, ...]
    primary_users: tuple[str, ...]


@dataclass(frozen=True)
class FolderAccess:
    access_permissions: str
    default_permissions: str


@dataclass(frozen=True)
class FilesystemInfo:
    filesystem: str
    source: str
    is_remote: bool


class UserPermissionsRepository:
    """Read local Unix users, groups, and ACL information."""

    def __init__(self) -> None:
        self._uid_min = _read_numeric_setting("UID_MIN", 1000)
        self._gid_min = _read_numeric_setting("GID_MIN", 1000)

    def accounts(self) -> list[UserAccount]:
        supplementary: dict[str, set[str]] = {}

        for group in grp.getgrall():
            for member in group.gr_mem:
                supplementary.setdefault(
                    member,
                    set(),
                ).add(group.gr_name)

        accounts: list[UserAccount] = []

        for entry in pwd.getpwall():
            try:
                primary_group = grp.getgrgid(
                    entry.pw_gid
                ).gr_name
            except KeyError:
                primary_group = str(entry.pw_gid)

            groups = sorted(
                supplementary.get(
                    entry.pw_name,
                    set(),
                )
            )

            accounts.append(
                UserAccount(
                    name=entry.pw_name,
                    uid=entry.pw_uid,
                    gid=entry.pw_gid,
                    primary_group=primary_group,
                    home=entry.pw_dir,
                    shell=entry.pw_shell,
                    description=entry.pw_gecos,
                    account_type=self._account_type(
                        entry.pw_name,
                        entry.pw_uid,
                    ),
                    supplementary_groups=tuple(groups),
                )
            )

        accounts.sort(
            key=lambda account: (
                account.account_type != "Human",
                account.name.casefold(),
            )
        )
        return accounts

    def groups(self) -> list[str]:
        return [group.name for group in self.local_groups()]

    def local_groups(self) -> list[LocalGroup]:
        primary_users: dict[int, list[str]] = {}

        for account in pwd.getpwall():
            primary_users.setdefault(account.pw_gid, []).append(account.pw_name)

        groups: list[LocalGroup] = []

        for entry in grp.getgrall():
            groups.append(
                LocalGroup(
                    name=entry.gr_name,
                    gid=entry.gr_gid,
                    group_type=(
                        "Regular" if entry.gr_gid >= self._gid_min else "System"
                    ),
                    members=tuple(sorted(entry.gr_mem, key=str.casefold)),
                    primary_users=tuple(
                        sorted(primary_users.get(entry.gr_gid, []), key=str.casefold)
                    ),
                )
            )

        groups.sort(
            key=lambda group: (
                group.group_type != "Regular",
                group.name.casefold(),
            )
        )
        return groups

    def filesystem_info(self, path: str) -> FilesystemInfo:
        target = Path(path)

        if not target.exists():
            return FilesystemInfo("", "", False)

        try:
            result = subprocess.run(
                [
                    "findmnt",
                    "--noheadings",
                    "--output",
                    "FSTYPE,SOURCE",
                    "--target",
                    str(target),
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return FilesystemInfo("", "", False)

        if result.returncode != 0:
            return FilesystemInfo("", "", False)

        fields = result.stdout.strip().split(None, 1)
        filesystem = fields[0].strip().lower() if fields else ""
        source = fields[1].strip() if len(fields) > 1 else ""
        network_types = {
            "9p", "afs", "ceph", "cifs", "davfs", "davfs2",
            "fuse.sshfs", "glusterfs", "nfs", "nfs4", "smb3", "sshfs",
        }
        remote = (
            filesystem in network_types
            or filesystem.startswith(("fuse.sshfs", "nfs"))
            or source.startswith("//")
            or ":" in source
        )
        return FilesystemInfo(filesystem, source, remote)

    def account(
        self,
        username: str,
    ) -> UserAccount | None:
        return next(
            (
                account
                for account in self.accounts()
                if account.name == username
            ),
            None,
        )

    def acl_tools_available(self) -> bool:
        return (
            shutil.which("getfacl") is not None
            and shutil.which("setfacl") is not None
        )

    def folder_access(
        self,
        *,
        path: str,
        username: str,
    ) -> FolderAccess:
        target = Path(path)

        if (
            not target.is_dir()
            or not self.acl_tools_available()
            or self.filesystem_info(path).is_remote
        ):
            return FolderAccess("", "")

        result = subprocess.run(
            [
                "getfacl",
                "-cp",
                "--",
                str(target),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if result.returncode != 0:
            return FolderAccess("", "")

        access = ""
        default = ""

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()

            if line.startswith(
                f"user:{username}:"
            ):
                access = line.rpartition(":")[2]
            elif line.startswith(
                f"default:user:{username}:"
            ):
                default = line.rpartition(":")[2]

        return FolderAccess(
            access_permissions=access,
            default_permissions=default,
        )

    def _account_type(
        self,
        name: str,
        uid: int,
    ) -> str:
        if uid == 0:
            return "Root"

        if uid >= self._uid_min and name != "nobody":
            return "Human"

        return "Service"


def _read_numeric_setting(setting: str, default: int) -> int:
    try:
        lines = Path("/etc/login.defs").read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return default

    for raw_line in lines:
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        fields = line.split()

        if len(fields) >= 2 and fields[0] == setting:
            try:
                return int(fields[1])
            except ValueError:
                return default

    return default
