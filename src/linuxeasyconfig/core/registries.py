from __future__ import annotations

from collections.abc import Iterable
from typing import Generic, TypeVar

from linuxeasyconfig.core.module_api import (
    CapabilityDefinition,
    FeatureDefinition,
    LocalServiceDefinition,
    ViewDefinition,
)


class RegistryError(ValueError):
    """Raised when a definition cannot be added to a registry."""


T = TypeVar("T")


class _DefinitionRegistry(Generic[T]):
    def __init__(self) -> None:
        self._values: dict[str, T] = {}

    def register(self, value: T) -> None:
        value_id = str(getattr(value, "id"))
        if value_id in self._values:
            raise RegistryError(
                f"Definition ID already registered: {value_id}"
            )
        self._values[value_id] = value

    def register_many(self, values: Iterable[T]) -> None:
        for value in values:
            self.register(value)

    def get(self, value_id: str) -> T | None:
        return self._values.get(value_id)

    def all(self) -> tuple[T, ...]:
        return tuple(self._values.values())

    def __len__(self) -> int:
        return len(self._values)


class FeatureRegistry(_DefinitionRegistry[FeatureDefinition]):
    def by_category(self) -> dict[str, tuple[FeatureDefinition, ...]]:
        categories: dict[str, list[FeatureDefinition]] = {}
        for feature in self._values.values():
            categories.setdefault(feature.category, []).append(feature)
        return {
            category: tuple(features)
            for category, features in categories.items()
        }


class ViewRegistry(_DefinitionRegistry[ViewDefinition]):
    pass


class CapabilityRegistry(_DefinitionRegistry[CapabilityDefinition]):
    def by_provider(
        self,
        module_id: str,
    ) -> tuple[CapabilityDefinition, ...]:
        return tuple(
            value
            for value in self._values.values()
            if value.provider_module_id == module_id
        )


class LocalServiceRegistry(_DefinitionRegistry[LocalServiceDefinition]):
    def by_category(
        self,
        category: str,
    ) -> tuple[LocalServiceDefinition, ...]:
        return tuple(
            value
            for value in self._values.values()
            if value.category == category
        )
