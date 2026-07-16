from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    optional_bool,
    required_string,
)

from .installer import (
    add_authorized_key,
    install_openssh,
    refresh_snapshot,
    save_settings,
    set_service_enabled,
    install_tigervnc,
    refresh_vnc_snapshot,
    save_vnc_settings,
    set_vnc_service_enabled,
)


def _install(arguments: dict[str, Any]) -> str:
    del arguments
    return install_openssh()


def _refresh(arguments: dict[str, Any]) -> str:
    del arguments
    return refresh_snapshot()


def _set_service(arguments: dict[str, Any]) -> str:
    return set_service_enabled(
        enabled=optional_bool(
            arguments,
            "enabled",
            default=True,
        )
    )


def _save_settings(arguments: dict[str, Any]) -> str:
    port = arguments.get("port")
    if not isinstance(port, int):
        raise ValueError("The SSH port is invalid.")

    return save_settings(
        port=port,
        password_authentication=optional_bool(
            arguments,
            "password_authentication",
            default=False,
        ),
        public_key_authentication=optional_bool(
            arguments,
            "public_key_authentication",
            default=True,
        ),
        permit_root_login=required_string(
            arguments,
            "permit_root_login",
        ),
    )


def _add_key(arguments: dict[str, Any]) -> str:
    return add_authorized_key(
        username=required_string(
            arguments,
            "username",
        ),
        key=required_string(
            arguments,
            "key",
            strip=False,
        ),
    )



def _install_vnc(arguments: dict[str, Any]) -> str:
    del arguments
    return install_tigervnc()


def _refresh_vnc(arguments: dict[str, Any]) -> str:
    del arguments
    return refresh_vnc_snapshot()


def _save_vnc(arguments: dict[str, Any]) -> str:
    display = arguments.get("display")
    depth = arguments.get("depth")

    if not isinstance(display, int):
        raise ValueError(
            "The VNC display number is invalid."
        )
    if not isinstance(depth, int):
        raise ValueError(
            "The VNC color depth is invalid."
        )

    return save_vnc_settings(
        username=required_string(
            arguments,
            "username",
        ),
        display=display,
        geometry=required_string(
            arguments,
            "geometry",
        ),
        depth=depth,
        startup_command=required_string(
            arguments,
            "startup_command",
        ),
        password=str(
            arguments.get("password", "")
        ),
        enabled=optional_bool(
            arguments,
            "enabled",
            default=True,
        ),
    )


def _set_vnc_service(
    arguments: dict[str, Any],
) -> str:
    return set_vnc_service_enabled(
        enabled=optional_bool(
            arguments,
            "enabled",
            default=True,
        )
    )

PRIVILEGED_TASKS = {
    "remote_access.install_vnc": _install_vnc,
    "remote_access.refresh_vnc": _refresh_vnc,
    "remote_access.save_vnc": _save_vnc,
    "remote_access.set_vnc_service": _set_vnc_service,
    "remote_access.install": _install,
    "remote_access.refresh": _refresh,
    "remote_access.set_service": _set_service,
    "remote_access.save_settings": _save_settings,
    "remote_access.add_authorized_key": _add_key,
}
