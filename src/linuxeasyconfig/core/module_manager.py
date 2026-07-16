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

    def load_from_directory(self, modules_directory: Path) -> ModuleManagerResult:
        discovered_modules, load_errors = discover_modules(modules_directory)
        registration_errors: list[ModuleRegistrationError] = []
        context = ModuleContext(
            capability_registry=self._capability_registry,
            service_registry=self._service_registry,
        )

        for record in discovered_modules:
            module_id = str(record.manifest["id"])

            try:
                record.instance.bind_context(context)
                views = record.instance.view_definitions()
                features = record.instance.feature_definitions()
                capabilities = record.instance.capability_definitions()
                services = record.instance.service_definitions()

                self._view_registry.register_many(views)
                self._feature_registry.register_many(features)
                self._capability_registry.register_many(capabilities)
                self._service_registry.register_many(services)
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

            self._loaded_modules.append(record)

        return ModuleManagerResult(
            loaded_modules=tuple(self._loaded_modules),
            load_errors=tuple(load_errors),
            registration_errors=tuple(registration_errors),
        )

    def loaded_modules(self) -> tuple[ModuleRecord, ...]:
        return tuple(self._loaded_modules)
