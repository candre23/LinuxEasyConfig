from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


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


@dataclass(frozen=True)
class CapabilityDefinition:
    id: str
    provider_module_id: str
    title: str
    description: str
    privileged_task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LocalServiceDefinition:
    id: str
    provider_module_id: str
    title: str
    protocol: str
    host: str
    port: int
    category: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleContext:
    capability_registry: Any
    service_registry: Any


class LECModule(ABC):
    def bind_context(self, context: ModuleContext) -> None:
        self._lec_context = context

    @abstractmethod
    def feature_definitions(self) -> list[FeatureDefinition]:
        """Return the user-facing features provided by this module."""

    def view_definitions(self) -> list[ViewDefinition]:
        return []

    def capability_definitions(self) -> list[CapabilityDefinition]:
        return []

    def service_definitions(self) -> list[LocalServiceDefinition]:
        return []
