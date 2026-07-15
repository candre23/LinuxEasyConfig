from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import pkgutil
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import linuxeasyconfig.modules as modules_package


PrivilegedHandler = Callable[[dict[str, Any]], str]
Registry = dict[str, PrivilegedHandler]


class PrivilegedHelperError(RuntimeError):
    """Raised when a privileged helper request is invalid."""


def discover_privileged_tasks() -> Registry:
    """
    Discover optional privileged.py providers from installed LEC modules.

    A module may expose a mapping named PRIVILEGED_TASKS:

        PRIVILEGED_TASKS = {
            "module.task_name": handler,
        }

    Each handler receives the task argument dictionary and returns a
    user-facing result message.
    """

    registry: Registry = {}

    for module_info in pkgutil.iter_modules(
        modules_package.__path__
    ):
        if not module_info.ispkg:
            continue

        provider_name = (
            f"{modules_package.__name__}."
            f"{module_info.name}.privileged"
        )

        if importlib.util.find_spec(provider_name) is None:
            continue

        provider = importlib.import_module(provider_name)
        declared = getattr(
            provider,
            "PRIVILEGED_TASKS",
            None,
        )

        if declared is None:
            continue

        if not isinstance(declared, Mapping):
            raise PrivilegedHelperError(
                f"{provider_name}.PRIVILEGED_TASKS "
                "must be a mapping."
            )

        for task_id, handler in declared.items():
            if (
                not isinstance(task_id, str)
                or not task_id.strip()
            ):
                raise PrivilegedHelperError(
                    f"{provider_name} declares an "
                    "invalid privileged task ID."
                )

            if not callable(handler):
                raise PrivilegedHelperError(
                    f"Privileged task {task_id!r} "
                    "does not have a callable handler."
                )

            if task_id in registry:
                raise PrivilegedHelperError(
                    "Duplicate privileged task ID "
                    f"declared: {task_id}"
                )

            registry[task_id] = handler

    return registry


def execute_task(
    task_id: str,
    arguments: dict[str, Any],
) -> str:
    registry = discover_privileged_tasks()
    handler = registry.get(task_id)

    if handler is None:
        raise PrivilegedHelperError(
            f"Unknown privileged task: {task_id}"
        )

    result = handler(arguments)

    if not isinstance(result, str):
        raise PrivilegedHelperError(
            f"Privileged task {task_id} returned "
            "an invalid result."
        )

    return result



def _read_payload(
    path: Path,
) -> tuple[str, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise PrivilegedHelperError(
            "The privileged-task payload is invalid."
        )

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(payload, dict):
        raise PrivilegedHelperError(
            "The privileged-task payload must "
            "be an object."
        )

    task_id = payload.get("task_id")
    arguments = payload.get("arguments", {})

    if (
        not isinstance(task_id, str)
        or not task_id.strip()
    ):
        raise PrivilegedHelperError(
            "The privileged-task ID is missing."
        )

    if not isinstance(arguments, dict):
        raise PrivilegedHelperError(
            "The privileged-task arguments "
            "are invalid."
        )

    return task_id.strip(), arguments


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Linux Easy Config privileged helper."
        )
    )
    parser.add_argument(
        "--payload",
        required=True,
        type=Path,
    )
    return parser.parse_args()


def main() -> int:
    command_line = _parse_arguments()
    task_id, arguments = _read_payload(
        command_line.payload
    )

    result = execute_task(
        task_id,
        arguments,
    )

    if result:
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
