from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import linuxeasyconfig.modules as modules_package

from linuxeasyconfig.core.module_loader import (
    USER_MODULES_DIRECTORY,
    clear_packaged_module_cache,
    inspect_module_archive,
    safe_module_package_name,
)


@dataclass(frozen=True)
class ModuleImportCandidate:
    source_path: Path
    manifest: dict
    package_name: str
    destination: Path
    replaces_custom: bool
    overrides_builtin: bool

    @property
    def name(self) -> str:
        return str(self.manifest.get("name", self.package_name))

    @property
    def module_id(self) -> str:
        return str(self.manifest["id"])

    @property
    def version(self) -> str:
        return str(self.manifest.get("version", "Unknown"))


@dataclass(frozen=True)
class CustomModule:
    path: Path
    name: str
    module_id: str
    version: str
    overrides_builtin: bool

    @property
    def display_name(self) -> str:
        suffix = (
            " — Custom override of built-in module"
            if self.overrides_builtin
            else ""
        )
        return f"{self.name} ({self.version}){suffix}"


class ModuleManagementRepository:
    def inspect_import(self, source_path: Path) -> ModuleImportCandidate:
        manifest = inspect_module_archive(source_path)
        module_id = str(manifest["id"])
        builtin = self._builtin_modules()
        custom = self.custom_modules()

        builtin_match = next(
            (item for item in builtin if item["module_id"] == module_id),
            None,
        )
        custom_match = next(
            (item for item in custom if item.module_id == module_id),
            None,
        )

        if builtin_match is not None:
            package_name = str(builtin_match["package_name"])
        elif custom_match is not None:
            package_name = custom_match.path.stem
        else:
            package_name = safe_module_package_name(source_path.stem)

        destination = USER_MODULES_DIRECTORY / f"{package_name}.lec"
        return ModuleImportCandidate(
            source_path=source_path,
            manifest=manifest,
            package_name=package_name,
            destination=destination,
            replaces_custom=custom_match is not None,
            overrides_builtin=builtin_match is not None,
        )

    def install(self, candidate: ModuleImportCandidate) -> Path:
        USER_MODULES_DIRECTORY.mkdir(parents=True, exist_ok=True)

        for module in self.custom_modules():
            if (
                module.module_id == candidate.module_id
                and module.path != candidate.destination
            ):
                module.path.unlink(missing_ok=True)

        with tempfile.NamedTemporaryFile(
            prefix=".lec-import-",
            suffix=".tmp",
            dir=USER_MODULES_DIRECTORY,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        try:
            shutil.copyfile(candidate.source_path, temporary_path)
            temporary_path.chmod(0o644)
            temporary_path.replace(candidate.destination)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        clear_packaged_module_cache()
        return candidate.destination

    def custom_modules(self) -> list[CustomModule]:
        modules: list[CustomModule] = []
        builtin_ids = {
            str(item["module_id"])
            for item in self._builtin_modules()
        }

        if not USER_MODULES_DIRECTORY.is_dir():
            return modules

        for path in sorted(USER_MODULES_DIRECTORY.glob("*.lec")):
            try:
                manifest = inspect_module_archive(path)
            except ValueError:
                continue

            module_id = str(manifest["id"])
            modules.append(
                CustomModule(
                    path=path,
                    name=str(manifest.get("name", path.stem)),
                    module_id=module_id,
                    version=str(manifest.get("version", "Unknown")),
                    overrides_builtin=module_id in builtin_ids,
                )
            )

        return sorted(modules, key=lambda item: item.name.casefold())

    def remove(self, module: CustomModule) -> None:
        try:
            module.path.relative_to(USER_MODULES_DIRECTORY)
        except ValueError as exc:
            raise ValueError(
                "The selected module is not a custom module."
            ) from exc

        module.path.unlink()
        clear_packaged_module_cache()

    def _builtin_modules(self) -> list[dict[str, str]]:
        modules_root = self._builtin_modules_root()
        modules: list[dict[str, str]] = []

        if not modules_root.is_dir():
            return modules

        for path in sorted(modules_root.iterdir()):
            if path.is_dir():
                manifest_path = path / "manifest.json"
                if not manifest_path.is_file():
                    continue
                try:
                    manifest = json.loads(
                        manifest_path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError):
                    continue
                package_name = path.name
            elif path.suffix.lower() == ".lec":
                try:
                    with zipfile.ZipFile(path, "r") as archive:
                        manifest = json.loads(
                            archive.read("manifest.json").decode("utf-8")
                        )
                except (
                    OSError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                    KeyError,
                    zipfile.BadZipFile,
                ):
                    continue
                package_name = path.stem
            else:
                continue

            modules.append(
                {
                    "module_id": str(manifest.get("id", "")),
                    "package_name": package_name,
                }
            )

        return modules

    @staticmethod
    def _builtin_modules_root() -> Path:
        for value in modules_package.__path__:
            candidate = Path(value)
            if candidate.name == "modules":
                return candidate

        raise RuntimeError(
            "The built-in modules directory could not be located."
        )
