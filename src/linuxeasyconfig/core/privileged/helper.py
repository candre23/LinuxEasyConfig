from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from linuxeasyconfig.modules.services.installer import (
    install_service,
    remove_service,
)


class PrivilegedHelperError(RuntimeError):
    """Raised when a privileged helper request is invalid."""


def execute_task(
    task_id: str,
    arguments: dict[str, Any],
) -> str:
    if task_id == "services.install":
        return install_service(
            source=Path(_required_string(arguments, "source")),
            service_name=_required_string(
                arguments,
                "service_name",
            ),
            enable_at_startup=bool(
                arguments.get("enable_at_startup", False)
            ),
            start_immediately=bool(
                arguments.get("start_immediately", False)
            ),
        )

    if task_id == "services.remove":
        return remove_service(
            service_name=_required_string(
                arguments,
                "service_name",
            ),
            stop_service=bool(
                arguments.get("stop_service", True)
            ),
            disable_at_startup=bool(
                arguments.get("disable_at_startup", True)
            ),
        )

    raise PrivilegedHelperError(
        f"Unknown privileged task: {task_id}"
    )


def _required_string(
    arguments: dict[str, Any],
    name: str,
) -> str:
    value = arguments.get(name)

    if not isinstance(value, str) or not value.strip():
        raise PrivilegedHelperError(
            f"Missing or invalid argument: {name}"
        )

    return value.strip()


def _read_payload(path: Path) -> tuple[str, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise PrivilegedHelperError(
            "The privileged-task payload is invalid."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise PrivilegedHelperError(
            "The privileged-task payload must be an object."
        )

    task_id = payload.get("task_id")
    arguments = payload.get("arguments", {})

    if not isinstance(task_id, str) or not task_id:
        raise PrivilegedHelperError(
            "The privileged-task ID is missing."
        )

    if not isinstance(arguments, dict):
        raise PrivilegedHelperError(
            "The privileged-task arguments are invalid."
        )

    return task_id, arguments


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Linux Easy Config privileged helper."
    )
    parser.add_argument(
        "--payload",
        required=True,
        type=Path,
    )
    return parser.parse_args()


def main() -> int:
    command_line = _parse_arguments()
    task_id, arguments = _read_payload(command_line.payload)

    result = execute_task(task_id, arguments)

    if result:
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
