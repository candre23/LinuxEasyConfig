from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import required_string

from .installer import (
    container_action,
    container_logs,
    create_container,
    deploy_preset,
    install_docker,
    refresh_snapshot,
    remove_container,
    record_container_integrations,
    service_action,
)


def _install(arguments: dict[str, Any]) -> str:
    del arguments
    return install_docker()


def _refresh(arguments: dict[str, Any]) -> str:
    del arguments
    return refresh_snapshot()


def _service(arguments: dict[str, Any]) -> str:
    return service_action(
        action=required_string(
            arguments,
            "action",
        )
    )


def _container_action(
    arguments: dict[str, Any],
) -> str:
    return container_action(
        container=required_string(
            arguments,
            "container",
        ),
        action=required_string(
            arguments,
            "action",
        ),
    )


def _remove(arguments: dict[str, Any]) -> str:
    return remove_container(
        container=required_string(
            arguments,
            "container",
        ),
        force=bool(
            arguments.get("force", False)
        ),
        remove_volumes=bool(
            arguments.get(
                "remove_volumes",
                False,
            )
        ),
        remove_image=bool(
            arguments.get(
                "remove_image",
                False,
            )
        ),
        remove_data=bool(
            arguments.get(
                "remove_data",
                False,
            )
        ),
    )


def _create(arguments: dict[str, Any]) -> str:
    host_port = arguments.get("host_port", 0)
    container_port = arguments.get(
        "container_port",
        0,
    )

    if not isinstance(host_port, int):
        raise ValueError(
            "The host port is invalid."
        )
    if not isinstance(
        container_port,
        int,
    ):
        raise ValueError(
            "The container port is invalid."
        )

    return create_container(
        name=required_string(
            arguments,
            "name",
        ),
        image=required_string(
            arguments,
            "image",
        ),
        host_port=host_port,
        container_port=container_port,
        protocol=required_string(
            arguments,
            "protocol",
        ),
        host_path=str(
            arguments.get("host_path", "")
        ),
        container_path=str(
            arguments.get(
                "container_path",
                "",
            )
        ),
        environment_lines=str(
            arguments.get(
                "environment_lines",
                "",
            )
        ),
        restart_policy=required_string(
            arguments,
            "restart_policy",
        ),
        access_scope=required_string(
            arguments,
            "access_scope",
        ),
        bind_address=str(
            arguments.get("bind_address", "")
        ),
        service_protocol=required_string(
            arguments,
            "service_protocol",
        ),
        reverse_proxy_compatible=bool(
            arguments.get(
                "reverse_proxy_compatible",
                False,
            )
        ),
        public_host=str(
            arguments.get("public_host", "")
        ),
    )



def _deploy_preset(
    arguments: dict[str, Any],
) -> str:
    preset = arguments.get("preset")
    values = arguments.get("values")

    if not isinstance(preset, dict):
        raise ValueError(
            "Docker preset data is missing."
        )
    if not isinstance(values, dict):
        raise ValueError(
            "Docker preset values are missing."
        )

    return deploy_preset(
        preset=preset,
        values=values,
    )

def _record_integrations(
    arguments: dict[str, Any],
) -> str:
    return record_container_integrations(
        container=required_string(arguments, "container"),
        firewall_rule_created=bool(
            arguments.get("firewall_rule_created", False)
        ),
        reverse_proxy_rule_created=bool(
            arguments.get("reverse_proxy_rule_created", False)
        ),
        reverse_proxy_rule_name=str(
            arguments.get("reverse_proxy_rule_name", "")
        ),
    )


def _logs(arguments: dict[str, Any]) -> str:
    lines = arguments.get("lines", 200)

    if not isinstance(lines, int):
        raise ValueError(
            "The log line count is invalid."
        )

    return container_logs(
        container=required_string(
            arguments,
            "container",
        ),
        lines=lines,
    )


PRIVILEGED_TASKS = {
    "docker.install": _install,
    "docker.refresh": _refresh,
    "docker.service_action": _service,
    "docker.container_action": _container_action,
    "docker.remove_container": _remove,
    "docker.create_container": _create,
    "docker.deploy_preset": _deploy_preset,
    "docker.record_integrations": _record_integrations,
    "docker.container_logs": _logs,
}
