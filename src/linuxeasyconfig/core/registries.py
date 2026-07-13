from __future__ import annotations

from collections.abc import Iterable

from linuxeasyconfig.core.module_api import FeatureDefinition, ViewDefinition


class RegistryError(ValueError):
    """Raised when a definition cannot be added to a registry."""


class FeatureRegistry:
    def __init__(self) -> None:
        self._features: dict[str, FeatureDefinition] = {}

    def register(self, feature: FeatureDefinition) -> None:
        if feature.id in self._features:
            raise RegistryError(f"Feature ID already registered: {feature.id}")

        self._features[feature.id] = feature

    def register_many(self, features: Iterable[FeatureDefinition]) -> None:
        for feature in features:
            self.register(feature)

    def get(self, feature_id: str) -> FeatureDefinition | None:
        return self._features.get(feature_id)

    def all(self) -> tuple[FeatureDefinition, ...]:
        return tuple(self._features.values())

    def by_category(self) -> dict[str, tuple[FeatureDefinition, ...]]:
        categories: dict[str, list[FeatureDefinition]] = {}

        for feature in self._features.values():
            categories.setdefault(feature.category, []).append(feature)

        return {
            category: tuple(features)
            for category, features in categories.items()
        }

    def __len__(self) -> int:
        return len(self._features)


class ViewRegistry:
    def __init__(self) -> None:
        self._views: dict[str, ViewDefinition] = {}

    def register(self, view: ViewDefinition) -> None:
        if view.id in self._views:
            raise RegistryError(f"View ID already registered: {view.id}")

        self._views[view.id] = view

    def register_many(self, views: Iterable[ViewDefinition]) -> None:
        for view in views:
            self.register(view)

    def get(self, view_id: str) -> ViewDefinition | None:
        return self._views.get(view_id)

    def all(self) -> tuple[ViewDefinition, ...]:
        return tuple(self._views.values())

    def __len__(self) -> int:
        return len(self._views)
