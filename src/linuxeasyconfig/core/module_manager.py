from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from linuxeasyconfig.core.module_api import ModuleContext
from linuxeasyconfig.core.module_loader import (
    ModuleLoadError,
    ModuleRecord,
    discover_modules,
)
from linuxeasyconfig.core.registries import (
    CapabilityRegistry,
    FeatureRegistry,
    LocalServiceRegistry,
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
        capability_registry: CapabilityRegistry,
        service_registry: LocalServiceRegistry,
    ) -> None:
        self._feature_registry = feature_registry
        self._view_registry = view_registry
        self._capability_registry = capability_registry
        self._service_registry = service_registry
        self._loaded_modules: list[ModuleRecord] = []
        self._feature_module_paths: dict[str, Path] = {}

    def load_from_directory(
        self,
        modules_directory: Path,
        user_modules_directory: Path | None = None,
    ) -> ModuleManagerResult:
        discovered_modules, load_errors = discover_modules(
            modules_directory,
            user_modules_directory,
        )
        registration_errors: list[ModuleRegistrationError] = []

        context = ModuleContext(
            capability_registry=self._capability_registry,
            service_registry=self._service_registry,
        )

        # Bind every module to the same live registries before any
        # feature or view factories are created.
        for record in discovered_modules:
            try:
                record.instance.bind_context(context)
            except Exception as exc:
                registration_errors.append(
                    ModuleRegistrationError(
                        module_id=str(record.manifest["id"]),
                        module_path=record.module_path,
                        message=(
                            "Module context binding failed: "
                            f"{exc}"
                        ),
                    )
                )

        failed_ids = {
            error.module_id
            for error in registration_errors
        }

        # Register cross-module capabilities and discovered services
        # first so every subsequent view sees the complete registry.
        for record in discovered_modules:
            module_id = str(record.manifest["id"])

            if module_id in failed_ids:
                continue

            try:
                self._capability_registry.register_many(
                    record.instance.capability_definitions()
                )
                self._service_registry.register_many(
                    record.instance.service_definitions()
                )
            except RegistryError as exc:
                registration_errors.append(
                    ModuleRegistrationError(
                        module_id=module_id,
                        module_path=record.module_path,
                        message=str(exc),
                    )
                )
                failed_ids.add(module_id)
            except Exception as exc:
                registration_errors.append(
                    ModuleRegistrationError(
                        module_id=module_id,
                        module_path=record.module_path,
                        message=(
                            "Capability or service registration "
                            f"failed: {exc}"
                        ),
                    )
                )
                failed_ids.add(module_id)

        for record in discovered_modules:
            module_id = str(record.manifest["id"])

            if module_id in failed_ids:
                continue

            try:
                features = (
                    record.instance.feature_definitions()
                )
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
                        message=(
                            "Module registration failed: "
                            f"{exc}"
                        ),
                    )
                )
                continue

            for feature in features:
                self._feature_module_paths[
                    feature.id
                ] = record.module_path

            self._loaded_modules.append(record)

        return ModuleManagerResult(
            loaded_modules=tuple(self._loaded_modules),
            load_errors=tuple(load_errors),
            registration_errors=tuple(
                registration_errors
            ),
        )

    def loaded_modules(self) -> tuple[ModuleRecord, ...]:
        return tuple(self._loaded_modules)

    def feature_module_paths(self) -> dict[str, Path]:
        return dict(self._feature_module_paths)
