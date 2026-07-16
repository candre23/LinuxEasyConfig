from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    required_string,
)

from .disk_health import refresh_disk_health_snapshot
from .installer import (
    enable_smart,
    install_disk_health_tools,
    start_self_test,
)


def _install_tools(
    arguments: dict[str, Any],
) -> str:
    del arguments
    return install_disk_health_tools()


def _refresh(
    arguments: dict[str, Any],
) -> str:
    del arguments
    return refresh_disk_health_snapshot()


def _enable_smart(
    arguments: dict[str, Any],
) -> str:
    return enable_smart(
        device=required_string(
            arguments,
            "device",
        )
    )


def _start_self_test(
    arguments: dict[str, Any],
) -> str:
    return start_self_test(
        device=required_string(
            arguments,
            "device",
        ),
        test_type=required_string(
            arguments,
            "test_type",
        ),
    )


PRIVILEGED_TASKS = {
    "hardware_monitor.install_disk_health_tools": (
        _install_tools
    ),
    "hardware_monitor.refresh_disk_health": (
        _refresh
    ),
    "hardware_monitor.enable_smart": (
        _enable_smart
    ),
    "hardware_monitor.start_self_test": (
        _start_self_test
    ),
}
