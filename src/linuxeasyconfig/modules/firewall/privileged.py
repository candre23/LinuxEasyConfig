from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    required_string,
)

from .installer import (
    add_rules,
    delete_rule,
    install_firewall,
    reset_firewall,
    set_defaults,
    set_firewall_enabled,
    set_logging,
    refresh_snapshot,
)


def _install(arguments: dict[str, Any]) -> str:
    del arguments
    return install_firewall()


def _set_enabled(arguments: dict[str, Any]) -> str:
    return set_firewall_enabled(
        enabled=bool(arguments.get("enabled", False))
    )


def _set_logging(arguments: dict[str, Any]) -> str:
    return set_logging(
        level=required_string(arguments, "level")
    )


def _set_defaults(arguments: dict[str, Any]) -> str:
    return set_defaults(
        incoming=required_string(
            arguments,
            "incoming",
        ),
        outgoing=required_string(
            arguments,
            "outgoing",
        ),
    )


def _add_rule(arguments: dict[str, Any]) -> str:
    sources = arguments.get("sources")

    if not isinstance(sources, list):
        raise ValueError(
            "Firewall rule sources are missing."
        )

    return add_rules(
        action=required_string(arguments, "action"),
        direction=required_string(
            arguments,
            "direction",
        ),
        sources=[str(value) for value in sources],
        destination=str(
            arguments.get("destination", "")
        ),
        port=str(arguments.get("port", "")),
        protocol=required_string(
            arguments,
            "protocol",
        ),
        profile=str(arguments.get("profile", "")),
        comment=str(arguments.get("comment", "")),
    )


def _delete_rule(arguments: dict[str, Any]) -> str:
    number = arguments.get("number")

    if not isinstance(number, int):
        raise ValueError(
            "The firewall rule number is invalid."
        )

    return delete_rule(number=number)


def _refresh(arguments: dict[str, Any]) -> str:
    del arguments
    return refresh_snapshot()


def _reset(arguments: dict[str, Any]) -> str:
    del arguments
    return reset_firewall()


PRIVILEGED_TASKS = {
    "firewall.install": _install,
    "firewall.set_enabled": _set_enabled,
    "firewall.set_logging": _set_logging,
    "firewall.set_defaults": _set_defaults,
    "firewall.add_rule": _add_rule,
    "firewall.delete_rule": _delete_rule,
    "firewall.reset": _reset,
    "firewall.refresh": _refresh,
}
