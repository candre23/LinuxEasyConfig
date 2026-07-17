from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import required_string

from .manager import (
    delete_task,
    install_monitor,
    refresh_status,
    run_task_now,
    save_task,
    set_task_enabled,
)


def _save(arguments: dict[str, Any]) -> str:
    return save_task(
        original_id=str(
            arguments.get("original_id", "")
        ),
        name=required_string(arguments, "name"),
        description=str(
            arguments.get("description", "")
        ),
        command=required_string(arguments, "command"),
        working_directory=str(
            arguments.get("working_directory", "/")
        ),
        run_as_user=str(
            arguments.get("run_as_user", "root")
        ),
        schedule_type=required_string(
            arguments,
            "schedule_type",
        ),
        schedule_value=str(
            arguments.get("schedule_value", "")
        ),
        enabled=bool(
            arguments.get("enabled", True)
        ),
    )


def _delete(arguments: dict[str, Any]) -> str:
    return delete_task(
        task_id=required_string(arguments, "task_id")
    )


def _enable(arguments: dict[str, Any]) -> str:
    return set_task_enabled(
        task_id=required_string(arguments, "task_id"),
        enabled=bool(arguments.get("enabled", True)),
    )


def _run_now(arguments: dict[str, Any]) -> str:
    return run_task_now(
        task_id=required_string(arguments, "task_id")
    )


def _refresh(arguments: dict[str, Any]) -> str:
    del arguments
    return refresh_status()


def _install(arguments: dict[str, Any]) -> str:
    del arguments
    return install_monitor()


PRIVILEGED_TASKS = {
    "task_scheduler.save": _save,
    "task_scheduler.delete": _delete,
    "task_scheduler.enable": _enable,
    "task_scheduler.run_now": _run_now,
    "task_scheduler.refresh": _refresh,
    "task_scheduler.install_monitor": _install,
}
