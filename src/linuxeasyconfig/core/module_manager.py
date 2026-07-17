from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from linuxeasyconfig.core.module_loader import (
    ModuleLoadError,
    ModuleRecord,
    discover_modules,
)
from linuxeasyconfig.core.registries import (
    FeatureRegistry,
    RegistryError,
    ViewRegistry,
)


@dataclass(frozen=True)
class ModuleRegistrationError:
    module_id: str
    module_path: Path
    message: str


@dataclass(frozen=True)
class ModuleManagerResult:
    loaded_modules: tuple[ModuleRecord, ...]
    load_errors: tuple[ModuleLoadError, ...]
    registration_errors: tuple[ModuleRegistrationError, ...]


class ModuleManager:
    def __init__(
        self,
        feature_registry: FeatureRegistry,
        view_registry: ViewRegistry,
    ) -> None:
        self._feature_registry = feature_registry
        self._view_registry = view_registry
        self._loaded_modules: list[ModuleRecord] = []
        self._feature_module_paths: dict[str, Path] = {}

    def load_from_directory(self, modules_directory: Path) -> ModuleManagerResult:
        discovered_modules, load_errors = discover_modules(modules_directory)
        registration_errors: list[ModuleRegistrationError] = []

        for record in discovered_modules:
            module_id = str(record.manifest["id"])

            try:
                features = record.instance.feature_definitions()
                views = record.instance.view_definitions()

                self._view_registry.register_many(views)
                self._feature_registry.register_many(features)
            except RegistryError as exc:
                registration_errors.append(
                    ModuleRegistrationError(
                        module_id=module_id,
                        module_path=record.module_path,
                        message=str(exc),
                    )
                )
                continue
            except Exception as exc:
                registration_errors.append(
                    ModuleRegistrationError(
                        module_id=module_id,
                        module_path=record.module_path,
                        message=f"Module registration failed: {exc}",
                    )
                )
                continue

            for feature in features:
                self._feature_module_paths[feature.id] = record.module_path

            self._loaded_modules.append(record)

        return ModuleManagerResult(
            loaded_modules=tuple(self._loaded_modules),
            load_errors=tuple(load_errors),
            registration_errors=tuple(registration_errors),
        )

    def loaded_modules(self) -> tuple[ModuleRecord, ...]:
        return tuple(self._loaded_modules)

    def feature_module_paths(self) -> dict[str, Path]:
        return dict(self._feature_module_paths)
