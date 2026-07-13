from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from linuxeasyconfig.core.manifest_schema import MANIFEST_SCHEMA


@dataclass(frozen=True)
class ModuleRecord:
    module_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class ModuleLoadError:
    module_path: Path
    message: str


def discover_modules(modules_directory: Path) -> tuple[list[ModuleRecord], list[ModuleLoadError]]:
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

        modules.append(
            ModuleRecord(
                module_path=module_path,
                manifest_path=manifest_path,
                manifest=manifest,
            )
        )

    return modules, errors
