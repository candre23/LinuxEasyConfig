from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask

from .collector import (
    collect_journal,
    collect_overview,
    list_raw_sources,
    read_raw_source,
)
from .models import LogEvent


class SystemLogsRepository:
    """
    Read-only log access deliberately runs as the current desktop user.

    journalctl and systemctl do not require LEC's privileged helper for
    users who already have normal journal access. This prevents repeated
    PolicyKit password prompts from every tab refresh.
    """

    def overview(self) -> dict[str, Any]:
        return collect_overview()

    def journal(
        self,
        *,
        mode: str,
        since: str,
        priority: int,
        unit: str = "",
        keyword: str = "",
        limit: int = 1000,
        current_boot: bool = False,
        grouped: bool = True,
    ) -> dict[str, Any]:
        result = collect_journal(
            mode=mode,
            since=since,
            priority=priority,
            unit=unit,
            keyword=keyword,
            limit=limit,
            current_boot=current_boot,
            grouped=grouped,
        )
        result["events"] = [
            LogEvent.from_dict(item)
            for item in result.get("events", [])
        ]
        return result

    def reset_failed(
        self,
        units: list[str],
    ) -> str:
        return str(
            PrivilegedRunner().run(
                PrivilegedTask(
                    task_id="system_logs.reset_failed",
                    arguments={"units": units},
                ),
                timeout=90,
            )
        )

    def raw_sources(self) -> list[dict[str, Any]]:
        return list_raw_sources()

    def raw_read(
        self,
        *,
        path: str,
        lines: int,
    ) -> dict[str, Any]:
        return read_raw_source(
            path=path,
            lines=lines,
        )
