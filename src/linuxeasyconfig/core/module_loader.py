from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from linuxeasyconfig.core.manifest_schema import MANIFEST_SCHEMA
from linuxeasyconfig.core.module_api import LECModule


@dataclass(frozen=True)
class ModuleRecord:
    module_path: Path
    manifest_path: Path
    manifest: dict[str, Any]
    instance: LECModule


@dataclass(frozen=True)
class ModuleLoadError:
    module_path: Path
    message: str


def _load_module_instance(
    module_path: Path,
    manifest: dict[str, Any],
) -> LECModule:
    entry_module_name, class_name = manifest["entry_point"].split(":", maxsplit=1)

    package_name = f"linuxeasyconfig.modules.{module_path.name}"
    import_name = f"{package_name}.{entry_module_name}"

    imported_module = importlib.import_module(import_name)

    try:
        module_class = getattr(imported_module, class_name)
    except AttributeError as exc:
        raise ImportError(
            f"Entry-point class {class_name!r} was not found in {import_name!r}."
        ) from exc

    instance = module_class()

    if not isinstance(instance, LECModule):
        raise TypeError(
            f"Entry point {manifest['entry_point']!r} does not implement LECModule."
        )

    return instance


def discover_modules(
    modules_directory: Path,
) -> tuple[list[ModuleRecord], list[ModuleLoadError]]:
    modules: list[ModuleRecord] = []
    errors: list[ModuleLoadError] = []

    if not modules_directory.exists():
        return modules, errors

    validator = Draft202012Validator(MANIFEST_SCHEMA)

    for module_path in sorted(path for path in modules_directory.iterdir() if path.is_dir()):
        manifest_path = module_path / "manifest.json"

        if not manifest_path.is_file():
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(
                ModuleLoadError(
                    module_path=module_path,
                    message=f"Could not read manifest: {exc}",
                )
            )
            continue

        validation_errors = sorted(
            validator.iter_errors(manifest),
            key=lambda error: list(error.absolute_path),
        )

        if validation_errors:
            message = "; ".join(
                f"{'.'.join(str(part) for part in error.absolute_path) or 'manifest'}: "
                f"{error.message}"
                for error in validation_errors
            )
            errors.append(
                ModuleLoadError(
                    module_path=module_path,
                    message=message,
                )
            )
            continue

        try:
            instance = _load_module_instance(module_path, manifest)
        except (ImportError, TypeError, ValueError) as exc:
            errors.append(
                ModuleLoadError(
                    module_path=module_path,
                    message=f"Could not load module entry point: {exc}",
                )
            )
            continue

        modules.append(
            ModuleRecord(
                module_path=module_path,
                manifest_path=manifest_path,
                manifest=manifest,
                instance=instance,
            )
        )

    return modules, errors
