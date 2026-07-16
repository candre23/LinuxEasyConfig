from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    optional_bool,
    optional_string,
    required_string,
)

from .installer import (
    install_local_folder_mount,
    install_network_share,
    mount_entry,
    remove_mount_entry,
    unmount_entry,
    update_local_folder_mount,
    update_network_share,
)


from .samba_installer import (
    install_samba_server,
    remove_hosted_share,
    save_hosted_share,
    set_samba_password,
)


def _install_samba_server(
    arguments: dict[str, Any],
) -> str:
    return install_samba_server(
        configure_firewall=optional_bool(
            arguments,
            "configure_firewall",
            default=True,
        )
    )


def _save_hosted_share(
    arguments: dict[str, Any],
) -> str:
    users = arguments.get("allowed_users", [])
    groups = arguments.get("allowed_groups", [])

    if not isinstance(users, list):
        raise ValueError(
            "Allowed users must be a list."
        )
    if not isinstance(groups, list):
        raise ValueError(
            "Allowed groups must be a list."
        )

    return save_hosted_share(
        original_name=optional_string(
            arguments,
            "original_name",
        ),
        name=required_string(
            arguments,
            "name",
        ),
        path=required_string(
            arguments,
            "path",
        ),
        comment=optional_string(
            arguments,
            "comment",
        ),
        read_only=optional_bool(
            arguments,
            "read_only",
            default=True,
        ),
        guest_access=optional_bool(
            arguments,
            "guest_access",
            default=False,
        ),
        allowed_users=[
            str(value) for value in users
        ],
        allowed_groups=[
            str(value) for value in groups
        ],
        local_network_only=optional_bool(
            arguments,
            "local_network_only",
            default=True,
        ),
        enabled=optional_bool(
            arguments,
            "enabled",
            default=True,
        ),
    )


def _remove_hosted_share(
    arguments: dict[str, Any],
) -> str:
    return remove_hosted_share(
        name=required_string(
            arguments,
            "name",
        )
    )


def _set_samba_password(
    arguments: dict[str, Any],
) -> str:
    return set_samba_password(
        username=required_string(
            arguments,
            "username",
        ),
        password=optional_string(
            arguments,
            "password",
            strip=False,
        ),
    )


def _install_network_share(
    arguments: dict[str, Any],
) -> str:
    return install_network_share(
        protocol=required_string(
            arguments,
            "protocol",
        ),
        source=required_string(
            arguments,
            "source",
        ),
        mountpoint=required_string(
            arguments,
            "mountpoint",
        ),
        filesystem=required_string(
            arguments,
            "filesystem",
        ),
        fstab_line=required_string(
            arguments,
            "fstab_line",
        ),
        credential_path=optional_string(
            arguments,
            "credential_path",
        ),
        credential_text=optional_string(
            arguments,
            "credential_text",
            strip=False,
        ),
        mount_now=optional_bool(
            arguments,
            "mount_now",
            default=True,
        ),
    )


def _update_network_share(
    arguments: dict[str, Any],
) -> str:
    return update_network_share(
        protocol=required_string(
            arguments,
            "protocol",
        ),
        source=required_string(
            arguments,
            "source",
        ),
        mountpoint=required_string(
            arguments,
            "mountpoint",
        ),
        filesystem=required_string(
            arguments,
            "filesystem",
        ),
        fstab_line=required_string(
            arguments,
            "fstab_line",
        ),
        credential_path=optional_string(
            arguments,
            "credential_path",
        ),
        credential_text=optional_string(
            arguments,
            "credential_text",
            strip=False,
        ),
        mount_now=optional_bool(
            arguments,
            "mount_now",
            default=True,
        ),
        original_source=required_string(
            arguments,
            "original_source",
        ),
        original_mountpoint=required_string(
            arguments,
            "original_mountpoint",
        ),
    )


def _install_local_folder(
    arguments: dict[str, Any],
) -> str:
    return install_local_folder_mount(
        source=required_string(
            arguments,
            "source",
        ),
        mountpoint=required_string(
            arguments,
            "mountpoint",
        ),
        fstab_line=required_string(
            arguments,
            "fstab_line",
        ),
        mount_now=optional_bool(
            arguments,
            "mount_now",
            default=True,
        ),
    )


def _update_local_folder(
    arguments: dict[str, Any],
) -> str:
    return update_local_folder_mount(
        source=required_string(
            arguments,
            "source",
        ),
        mountpoint=required_string(
            arguments,
            "mountpoint",
        ),
        fstab_line=required_string(
            arguments,
            "fstab_line",
        ),
        mount_now=optional_bool(
            arguments,
            "mount_now",
            default=True,
        ),
        original_source=required_string(
            arguments,
            "original_source",
        ),
        original_mountpoint=required_string(
            arguments,
            "original_mountpoint",
        ),
    )


def _mount(
    arguments: dict[str, Any],
) -> str:
    return mount_entry(
        mountpoint=required_string(
            arguments,
            "mountpoint",
        )
    )


def _unmount(
    arguments: dict[str, Any],
) -> str:
    return unmount_entry(
        mountpoint=required_string(
            arguments,
            "mountpoint",
        )
    )


def _remove_entry(
    arguments: dict[str, Any],
) -> str:
    return remove_mount_entry(
        source=required_string(
            arguments,
            "source",
        ),
        mountpoint=required_string(
            arguments,
            "mountpoint",
        ),
        credential_path=optional_string(
            arguments,
            "credential_path",
        ),
        unmount_first=optional_bool(
            arguments,
            "unmount_first",
            default=True,
        ),
    )


PRIVILEGED_TASKS = {
    "mounts.install_samba_server": (
        _install_samba_server
    ),
    "mounts.save_hosted_share": (
        _save_hosted_share
    ),
    "mounts.remove_hosted_share": (
        _remove_hosted_share
    ),
    "mounts.set_samba_password": (
        _set_samba_password
    ),
    "mounts.install_network_share": (
        _install_network_share
    ),
    "mounts.install_local_folder": (
        _install_local_folder
    ),
    "mounts.update_local_folder": (
        _update_local_folder
    ),
    "mounts.update_network_share": (
        _update_network_share
    ),
    "mounts.mount": _mount,
    "mounts.unmount": _unmount,
    "mounts.remove_entry": _remove_entry,
}
