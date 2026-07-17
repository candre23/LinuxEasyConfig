from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CONFIG_DIR = Path(
    "/etc/linuxeasyconfig/task_scheduler"
)
TASKS_PATH = CONFIG_DIR / "tasks.json"
PUBLIC_TASKS_PATH = Path(
    "/var/lib/linuxeasyconfig/task-scheduler/tasks.json"
)
STATUS_PATH = Path(
    "/var/lib/linuxeasyconfig/task-scheduler/status.json"
)


@dataclass
class ScheduledTask:
    id: str
    name: str
    description: str
    command: str
    working_directory: str
    run_as_user: str
    schedule_type: str
    schedule_value: str
    enabled: bool = True


def load_tasks() -> list[ScheduledTask]:
    return [
        ScheduledTask(**item)
        for item in _load_list(TASKS_PATH)
    ]


def save_tasks(
    tasks: list[ScheduledTask],
) -> None:
    private = [asdict(item) for item in tasks]
    public = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "command": item.command,
            "working_directory": item.working_directory,
            "run_as_user": item.run_as_user,
            "schedule_type": item.schedule_type,
            "schedule_value": item.schedule_value,
            "enabled": item.enabled,
        }
        for item in tasks
    ]
    _save(TASKS_PATH, private, 0o600)
    _save(PUBLIC_TASKS_PATH, public, 0o644)


def load_public_tasks() -> list[dict[str, Any]]:
    return _load_list(PUBLIC_TASKS_PATH)


def load_status() -> dict[str, Any]:
    if not STATUS_PATH.is_file():
        return {}

    try:
        value = json.loads(
            STATUS_PATH.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except (OSError, json.JSONDecodeError):
        return {}

    return value if isinstance(value, dict) else {}


def save_status(
    value: dict[str, Any],
) -> None:
    _save(STATUS_PATH, value, 0o644)


def _load_list(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(value, list):
        return []

    return [
        item
        for item in value
        if isinstance(item, dict)
    ]


def _save(
    path: Path,
    value: Any,
    mode: int,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.parent.chmod(0o755)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.chmod(mode)
    temporary.replace(path)
    path.chmod(mode)
