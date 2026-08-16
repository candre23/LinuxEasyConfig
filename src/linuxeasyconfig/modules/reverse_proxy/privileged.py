from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    required_string,
)

from .installer import (
    install_reverse_proxy_system,
    reload_reverse_proxy_system,
    service_action,
    unban_address,
)
from .manager import (
    create_or_update_credential,
    create_or_update_rule,
    delete_credential,
    delete_rule,
    read_recent_activity,
    update_protection_settings,
)


def _install(arguments: dict[str, Any]) -> str:
    del arguments
    return install_reverse_proxy_system()


def _service_action(arguments: dict[str, Any]) -> str:
    return service_action(
        service=required_string(arguments, "service"),
        action=required_string(arguments, "action"),
    )


def _reload(arguments: dict[str, Any]) -> str:
    del arguments
    return reload_reverse_proxy_system()


def _unban(arguments: dict[str, Any]) -> str:
    return unban_address(
        address=required_string(arguments, "address")
    )


def _credential_save(arguments: dict[str, Any]) -> str:
    return create_or_update_credential(
        original_username=str(
            arguments.get("original_username", "")
        ),
        username=required_string(arguments, "username"),
        password=str(arguments.get("password", "")),
    )


def _credential_delete(arguments: dict[str, Any]) -> str:
    return delete_credential(
        username=required_string(arguments, "username")
    )


def _rule_save(arguments: dict[str, Any]) -> str:
    data = arguments.get("data")
    if not isinstance(data, dict):
        raise ValueError("Rule data is missing.")

    return create_or_update_rule(
        original_name=str(
            arguments.get("original_name", "")
        ),
        data=data,
    )


def _rule_delete(arguments: dict[str, Any]) -> str:
    return delete_rule(
        name=required_string(arguments, "name")
    )


def _activity_read(arguments: dict[str, Any]) -> str:
    try:
        maximum_lines = int(
            arguments.get("maximum_lines", 300)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "maximum_lines must be an integer."
        ) from exc

    return read_recent_activity(
        maximum_lines=maximum_lines
    )


def _protection_save(arguments: dict[str, Any]) -> str:
    data = arguments.get("data")
    if not isinstance(data, dict):
        raise ValueError(
            "Protection settings are missing."
        )
    return update_protection_settings(data=data)


PRIVILEGED_TASKS = {
    "reverse_proxy.install": _install,
    "reverse_proxy.service_action": _service_action,
    "reverse_proxy.reload": _reload,
    "reverse_proxy.unban": _unban,
    "reverse_proxy.credential_save": _credential_save,
    "reverse_proxy.credential_delete": _credential_delete,
    "reverse_proxy.rule_save": _rule_save,
    "reverse_proxy.rule_delete": _rule_delete,
    "reverse_proxy.activity_read": _activity_read,
    "reverse_proxy.protection_save": _protection_save,
}
