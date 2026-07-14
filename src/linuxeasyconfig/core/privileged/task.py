from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PrivilegedTask:
    """A named administrative operation requested by a LEC module."""

    task_id: str
    arguments: dict[str, Any] = field(default_factory=dict)
