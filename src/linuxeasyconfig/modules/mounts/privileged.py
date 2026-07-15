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
