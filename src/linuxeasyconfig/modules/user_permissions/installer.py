from __future__ import annotations

import grp
import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path


_USERNAME_PATTERN = re.compile(
    r"^[a-z_][a-z0-9_-]*[$]?$"
)

_NOLOGIN_SHELL = Path("/usr/sbin/nologin")


def create_service_account(
    *,
    username: str,
    description: str,
    create_home: bool,
    home_directory: str,
) -> str:
    username = _validate_username(username)

    try:
        pwd.getpwnam(username)
    except KeyError:
        pass
    else:
        raise ValueError(
            f"The user {username} already exists."
        )

    command = [
        "useradd",
        "--system",
        "--user-group",
        "--shell",
        str(_NOLOGIN_SHELL),
    ]

    if description.strip():
        command.extend(
            [
                "--comment",
                description.strip(),
            ]
        )

    if create_home:
        home = _validate_home_directory(
            home_directory,
            username,
        )
        command.extend(
            [
                "--create-home",
                "--home-dir",
                str(home),
            ]
        )
    else:
        command.extend(
            [
                "--no-create-home",
                "--home-dir",
                "/nonexistent",
            ]
        )

    command.append(username)
    _run(command, timeout=60)

    return (
        f"Created service account {username}. "
        "Interactive login is disabled."
    )


def set_supplementary_groups(
    *,
    username: str,
    groups: list[str],
) -> str:
    account = _require_user(username)

    if account.pw_uid == 0:
        raise ValueError(
            "LEC will not modify root's group memberships."
        )

    validated_groups = sorted(
        {
            _validate_group(group)
            for group in groups
        }
    )

    command = [
        "usermod",
        "--groups",
        ",".join(validated_groups),
        username,
    ]
    _run(command, timeout=60)

    if validated_groups:
        joined = ", ".join(validated_groups)
        return (
            f"Updated {username}'s supplementary groups: "
            f"{joined}."
        )

    return (
        f"Removed all supplementary group memberships "
        f"from {username}."
    )


def create_group(*, name: str, system_group: bool) -> str:
    name = _validate_group_name(name)

    try:
        grp.getgrnam(name)
    except KeyError:
        pass
    else:
        raise ValueError(f"The group {name} already exists.")

    command = ["groupadd"]
    if system_group:
        command.append("--system")
    command.append(name)
    _run(command, timeout=60)
    return f"Created {'system' if system_group else 'regular'} group {name}."


def rename_group(*, old_name: str, new_name: str) -> str:
    old_name = _validate_group(old_name)
    new_name = _validate_group_name(new_name)

    if old_name == new_name:
        return f"The group is already named {old_name}."

    try:
        grp.getgrnam(new_name)
    except KeyError:
        pass
    else:
        raise ValueError(f"The group {new_name} already exists.")

    _run(["groupmod", "--new-name", new_name, old_name], timeout=60)
    return f"Renamed group {old_name} to {new_name}."


def delete_group(*, name: str) -> str:
    name = _validate_group(name)

    primary_users = [
        entry.pw_name
        for entry in pwd.getpwall()
        if entry.pw_gid == grp.getgrnam(name).gr_gid
    ]

    if primary_users:
        raise ValueError(
            "The group is the primary group for: " + ", ".join(primary_users)
            + ". Change or remove those accounts first."
        )

    _run(["groupdel", name], timeout=60)
    return f"Deleted group {name}."


def apply_folder_access(
    *,
    username: str,
    path: str,
    access_level: str,
    recursive: bool,
    inherit: bool,
    traverse_parents: bool,
) -> str:
    _require_acl_tools()
    _require_user(username)

    target = _validate_directory(path)
    _reject_remote_filesystem(target)
    access_level = access_level.strip().lower()

    if access_level == "read":
        direct_permissions = "r-x"
        recursive_permissions = "r-X"
    elif access_level == "write":
        direct_permissions = "rwx"
        recursive_permissions = "rwX"
    else:
        raise ValueError(
            "The folder access level is invalid."
        )

    if traverse_parents:
        _grant_parent_traversal(
            username=username,
            target=target,
        )

    if recursive:
        _run(
            [
                "setfacl",
                "-R",
                "-m",
                (
                    f"u:{username}:"
                    f"{recursive_permissions}"
                ),
                "--",
                str(target),
            ],
            timeout=300,
        )
    else:
        _run(
            [
                "setfacl",
                "-m",
                (
                    f"u:{username}:"
                    f"{direct_permissions}"
                ),
                "--",
                str(target),
            ],
            timeout=60,
        )

    if inherit:
        _run(
            [
                "setfacl",
                "-m",
                (
                    f"d:u:{username}:"
                    f"{direct_permissions}"
                ),
                "--",
                str(target),
            ],
            timeout=60,
        )

    scope = (
        "the folder and its existing contents"
        if recursive
        else "the folder"
    )
    inheritance = (
        " New items will inherit this access."
        if inherit
        else ""
    )

    return (
        f"Granted {username} {access_level} access to "
        f"{scope} at {target}.{inheritance}"
    )


def remove_folder_access(
    *,
    username: str,
    path: str,
    recursive: bool,
    remove_default: bool,
) -> str:
    _require_acl_tools()
    _require_user(username)
    target = _validate_directory(path)
    _reject_remote_filesystem(target)

    command = [
        "setfacl",
    ]

    if recursive:
        command.append("-R")

    command.extend(
        [
            "-x",
            f"u:{username}",
            "--",
            str(target),
        ]
    )
    _run(command, timeout=300 if recursive else 60)

    if remove_default:
        _run(
            [
                "setfacl",
                "-x",
                f"d:u:{username}",
                "--",
                str(target),
            ],
            timeout=60,
            allow_missing_acl=True,
        )

    return (
        f"Removed {username}'s explicit ACL access from "
        f"{target}."
    )


def _grant_parent_traversal(
    *,
    username: str,
    target: Path,
) -> None:
    parents = list(target.parents)

    for parent in reversed(parents):
        if parent == Path("/"):
            continue

        existing = _named_user_permissions(
            path=parent,
            username=username,
        )

        if "x" in existing:
            continue

        permissions = _union_permissions(
            existing,
            "--x",
        )

        _run(
            [
                "setfacl",
                "-m",
                f"u:{username}:{permissions}",
                "--",
                str(parent),
            ],
            timeout=60,
        )


def _named_user_permissions(
    *,
    path: Path,
    username: str,
) -> str:
    result = subprocess.run(
        [
            "getfacl",
            "-cp",
            "--",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        return ""

    prefix = f"user:{username}:"

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()

        if line.startswith(prefix):
            return line.rpartition(":")[2]

    return ""


def _union_permissions(
    first: str,
    second: str,
) -> str:
    permissions = {
        character
        for character in first + second
        if character in {"r", "w", "x"}
    }

    return "".join(
        character
        if character in permissions
        else "-"
        for character in "rwx"
    )


def _require_acl_tools() -> None:
    missing = [
        command
        for command in (
            "getfacl",
            "setfacl",
        )
        if shutil.which(command) is None
    ]

    if missing:
        raise RuntimeError(
            "ACL tools are not installed. Run: "
            "sudo apt install acl"
        )


def _validate_username(
    value: str,
) -> str:
    username = value.strip()

    if not _USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Usernames must begin with a lowercase letter "
            "or underscore and contain only lowercase letters, "
            "numbers, underscores, and hyphens."
        )

    return username


def _validate_group_name(value: str) -> str:
    name = value.strip()

    if not _USERNAME_PATTERN.fullmatch(name):
        raise ValueError(
            "Group names must begin with a lowercase letter or underscore "
            "and contain only lowercase letters, numbers, underscores, and hyphens."
        )

    return name


def _validate_group(
    value: str,
) -> str:
    name = _validate_group_name(value)

    if not name:
        raise ValueError(
            "A selected group name is invalid."
        )

    try:
        grp.getgrnam(name)
    except KeyError as exc:
        raise ValueError(
            f"The group {name} does not exist."
        ) from exc

    return name


def _require_user(
    username: str,
):
    username = _validate_username(username)

    try:
        return pwd.getpwnam(username)
    except KeyError as exc:
        raise ValueError(
            f"The user {username} does not exist."
        ) from exc


def _validate_home_directory(
    value: str,
    username: str,
) -> Path:
    text = value.strip()

    if not text:
        text = f"/var/lib/{username}"

    path = Path(
        os.path.normpath(text)
    )

    if (
        not path.is_absolute()
        or path == Path("/")
    ):
        raise ValueError(
            "The home directory must be an absolute path "
            "other than /."
        )

    return path


def _validate_directory(
    value: str,
) -> Path:
    path = Path(
        os.path.normpath(value.strip())
    )

    if not path.is_absolute():
        raise ValueError(
            "Select a folder using an absolute path."
        )

    if not path.is_dir():
        raise ValueError(
            "The selected folder does not exist."
        )

    return path


def _reject_remote_filesystem(path: Path) -> None:
    result = subprocess.run(
        [
            "findmnt",
            "--noheadings",
            "--output",
            "FSTYPE,SOURCE",
            "--target",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    if result.returncode != 0:
        return

    fields = result.stdout.strip().split(None, 1)
    filesystem = fields[0].lower() if fields else ""
    source = fields[1] if len(fields) > 1 else ""
    network_types = {
        "9p", "afs", "ceph", "cifs", "davfs", "davfs2",
        "fuse.sshfs", "glusterfs", "nfs", "nfs4", "smb3", "sshfs",
    }

    if (
        filesystem in network_types
        or filesystem.startswith(("fuse.sshfs", "nfs"))
        or source.startswith("//")
        or ":" in source
    ):
        raise ValueError(
            "LEC will not apply local ACL changes to a remote filesystem. "
            "Use a local group together with the network mount's ownership "
            "and mode options instead."
        )


def _run(
    command: list[str],
    *,
    timeout: int,
    allow_missing_acl: bool = False,
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

    message = (
        result.stderr.strip()
        or result.stdout.strip()
        or (
            f"{command[0]} exited with code "
            f"{result.returncode}"
        )
    )

    if (
        allow_missing_acl
        and "No such attribute" in message
    ):
        return

    raise RuntimeError(
        f"{' '.join(command)} failed:\n\n{message}"
    )
