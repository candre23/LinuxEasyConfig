from __future__ import annotations

from typing import Any

from .manager import install_monitor, refresh_snapshot


def _install(arguments: dict[str, Any]) -> str:
    del arguments
    return install_monitor()


def _refresh(arguments: dict[str, Any]) -> str:
    del arguments
    return refresh_snapshot()


PRIVILEGED_TASKS = {
    "port_usage.install_monitor": _install,
    "port_usage.refresh": _refresh,
}
