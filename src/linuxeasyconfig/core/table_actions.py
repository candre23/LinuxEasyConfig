from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableAction:
    id: str
    label: str
    enabled: bool = True
    confirmation_title: str | None = None
    confirmation_message: str | None = None
