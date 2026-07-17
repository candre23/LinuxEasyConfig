from __future__ import annotations

from typing import Any

from .storage import load_status


class TaskSchedulerRepository:
    def snapshot(self) -> dict[str, Any]:
        return load_status()
