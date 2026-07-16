from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    required_string,
)

from .docker_rules import (
    allow_docker_service,
    block_docker_service,
    reapply_docker_rules,
    remove_docker_service,
    unblock_docker_service,
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



def _allow_docker_service(
    arguments: dict[str, Any],
) -> str:
    sources = arguments.get("sources")

    if not isinstance(sources, list):
        raise ValueError(
            "Docker firewall rule sources are missing."
        )

    host_port = arguments.get("host_port")
    container_port = arguments.get("container_port")

    if not isinstance(host_port, int):
        raise ValueError(
            "The Docker host port is invalid."
        )
    if not isinstance(container_port, int):
        raise ValueError(
            "The Docker container port is invalid."
        )

    return allow_docker_service(
        container=required_string(
            arguments,
            "container",
        ),
        host_port=host_port,
        container_port=container_port,
        protocol=required_string(
            arguments,
            "protocol",
        ),
        sources=[str(value) for value in sources],
        comment=str(arguments.get("comment", "")),
    )



def _block_docker_service(
    arguments: dict[str, Any],
) -> str:
    host_port = arguments.get("host_port")

    if not isinstance(host_port, int):
        raise ValueError(
            "The Docker host port is invalid."
        )

    return block_docker_service(
        container=required_string(
            arguments,
            "container",
        ),
        host_port=host_port,
        protocol=required_string(
            arguments,
            "protocol",
        ),
    )


def _unblock_docker_service(
    arguments: dict[str, Any],
) -> str:
    host_port = arguments.get("host_port")

    if not isinstance(host_port, int):
        raise ValueError(
            "The Docker host port is invalid."
        )

    return unblock_docker_service(
        container=required_string(
            arguments,
            "container",
        ),
        host_port=host_port,
        protocol=required_string(
            arguments,
            "protocol",
        ),
    )

def _remove_docker_service(
    arguments: dict[str, Any],
) -> str:
    host_port = arguments.get("host_port", 0)

    if not isinstance(host_port, int):
        raise ValueError(
            "The Docker host port is invalid."
        )

    return remove_docker_service(
        container=required_string(
            arguments,
            "container",
        ),
        host_port=host_port,
        protocol=str(
            arguments.get("protocol", "")
        ),
    )


def _reapply_docker_rules(
    arguments: dict[str, Any],
) -> str:
    del arguments
    return reapply_docker_rules()

PRIVILEGED_TASKS = {
    "firewall.allow_docker_service": _allow_docker_service,
    "firewall.block_docker_service": _block_docker_service,
    "firewall.unblock_docker_service": _unblock_docker_service,
    "firewall.remove_docker_service": _remove_docker_service,
    "firewall.reapply_docker_rules": _reapply_docker_rules,
    "firewall.install": _install,
    "firewall.set_enabled": _set_enabled,
    "firewall.set_logging": _set_logging,
    "firewall.set_defaults": _set_defaults,
    "firewall.add_rule": _add_rule,
    "firewall.delete_rule": _delete_rule,
    "firewall.reset": _reset,
    "firewall.refresh": _refresh,
}
