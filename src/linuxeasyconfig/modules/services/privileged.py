from __future__ import annotations

from pathlib import Path
from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    optional_bool,
    required_string,
)

from .installer import install_service, remove_service


def _install(
    arguments: dict[str, Any],
) -> str:
    return install_service(
        source=Path(
            required_string(arguments, "source")
        ),
        service_name=required_string(
            arguments,
            "service_name",
        ),
        enable_at_startup=optional_bool(
            arguments,
            "enable_at_startup",
            default=False,
        ),
        start_immediately=optional_bool(
            arguments,
            "start_immediately",
            default=False,
        ),
    )


def _remove(
    arguments: dict[str, Any],
) -> str:
    return remove_service(
        service_name=required_string(
            arguments,
            "service_name",
        ),
        stop_service=optional_bool(
            arguments,
            "stop_service",
            default=True,
        ),
        disable_at_startup=optional_bool(
            arguments,
            "disable_at_startup",
            default=True,
        ),
    )


PRIVILEGED_TASKS = {
    "services.install": _install,
    "services.remove": _remove,
}
