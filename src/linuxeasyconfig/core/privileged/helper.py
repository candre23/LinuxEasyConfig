from __future__ import annotations

from linuxeasyconfig.bootstrap import (
    enable_compat_runtime,
)

enable_compat_runtime()

import argparse
import importlib
import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import linuxeasyconfig.modules as modules_package

from linuxeasyconfig.core.module_loader import (
    USER_MODULES_DIRECTORY,
    active_module_package_names,
)


PrivilegedHandler = Callable[[dict[str, Any]], str]
Registry = dict[str, PrivilegedHandler]


class PrivilegedHelperError(RuntimeError):
    """Raised when a privileged helper request is invalid."""


def discover_privileged_tasks() -> Registry:
    """
    Discover privileged.py providers from the active LEC module set.

    Development folders take precedence over packaged .lec copies.
    Packaged modules are extracted into LEC's module cache before
    providers are imported.
    """

    registry: Registry = {}

    modules_directory = _modules_directory()
    package_names, load_errors = active_module_package_names(
        modules_directory,
        USER_MODULES_DIRECTORY,
    )

    if load_errors:
        details = "; ".join(
            f"{error.module_path.name}: {error.message}"
            for error in load_errors
        )
        raise PrivilegedHelperError(
            "One or more modules could not be prepared: "
            + details
        )

    for package_name in package_names:
        provider_name = (
            f"{modules_package.__name__}."
            f"{package_name}.privileged"
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


def _modules_directory() -> Path:
    package_paths = list(
        getattr(modules_package, "__path__", [])
    )

    for value in package_paths:
        path = Path(value)

        if path.name == "modules":
            return path

    raise PrivilegedHelperError(
        "LEC's modules directory could not be located."
    )


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
