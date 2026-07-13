from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FeatureDefinition:
    id: str
    title: str
    target_type: str
    target_id: str
    description: str = ""
    category: str = "General"
    icon: str | None = None
    keywords: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ViewDefinition:
    id: str
    title: str
    view_type: str
    data: dict[str, Any]


class LECModule(ABC):
    @abstractmethod
    def feature_definitions(self) -> list[FeatureDefinition]:
        """Return the user-facing features provided by this module."""

    def view_definitions(self) -> list[ViewDefinition]:
        """Return view definitions provided by this module."""
        return []
