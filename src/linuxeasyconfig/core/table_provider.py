from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from linuxeasyconfig.core.table_actions import TableAction


class TableDataProvider(ABC):
    @abstractmethod
    def columns(self) -> Sequence[dict[str, Any]]:
        """Return table column definitions."""

    @abstractmethod
    def rows(self) -> Sequence[dict[str, Any]]:
        """Return the current table rows."""

    def refresh(self) -> None:
        """Refresh cached data before rows() is called."""
        return

    def status_text(self) -> str:
        return f"{len(self.rows())} items"

    @property
    def refresh_interval_ms(self) -> int | None:
        return None

    def actions_for_row(
        self,
        row: dict[str, Any] | None,
    ) -> Sequence[TableAction]:
        return ()

    def execute_action(
        self,
        action_id: str,
        row: dict[str, Any],
    ) -> str:
        raise ValueError(f"Unsupported table action: {action_id}")
