from __future__ import annotations

import importlib.metadata
import json

import linuxeasyconfig
import linuxeasyconfig.modules as modules_package
import platform

from linuxeasyconfig.core.module_loader import (
    USER_MODULES_DIRECTORY,
)
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModuleInformation:
    name: str
    module_id: str
    version: str
    source_type: str
    path: str
    status: str


@dataclass(frozen=True)
class ApplicationInformation:
    lec_version: str
    python_version: str
    operating_system: str
    installation_path: str
    loaded_module_count: int
    modules: tuple[ModuleInformation, ...]


class OverviewRepository:
    def information(self) -> ApplicationInformation:
        package_root = Path(linuxeasyconfig.__file__).resolve().parent
        modules_root = _installed_modules_root()
        modules = tuple(
            sorted(
                self._discover_modules(modules_root),
                key=lambda item: item.name.casefold(),
            )
        )

        return ApplicationInformation(
            lec_version=_lec_version(package_root),
            python_version=platform.python_version(),
            operating_system=_operating_system(),
            installation_path=str(package_root),
            loaded_module_count=len(modules),
            modules=modules,
        )

    def _discover_modules(
        self,
        modules_root: Path,
    ) -> list[ModuleInformation]:
        by_id: dict[str, ModuleInformation] = {}

        if modules_root.is_dir():
            for candidate in sorted(
                modules_root.iterdir()
            ):
                if (
                    not candidate.is_dir()
                    or candidate.name.startswith(
                        (".", "_")
                    )
                ):
                    continue

                manifest_path = (
                    candidate / "manifest.json"
                )

                if not manifest_path.is_file():
                    continue

                information = (
                    self._from_manifest_file(
                        manifest_path,
                        candidate,
                        "Folder",
                        candidate.name,
                    )
                )
                by_id[information.module_id] = (
                    information
                )

            for archive_path in sorted(
                modules_root.glob("*.lec")
            ):
                information = self._from_archive(
                    archive_path
                )
                by_id[information.module_id] = (
                    information
                )

        # User-installed modules override bundled modules
        # with the same manifest ID.
        if USER_MODULES_DIRECTORY.is_dir():
            for archive_path in sorted(
                USER_MODULES_DIRECTORY.glob(
                    "*.lec"
                )
            ):
                information = self._from_archive(
                    archive_path
                )

                by_id[information.module_id] = (
                    ModuleInformation(
                        name=information.name,
                        module_id=(
                            information.module_id
                        ),
                        version=information.version,
                        source_type=(
                            "Custom LEC archive"
                        ),
                        path=information.path,
                        status="Installed",
                    )
                )

        return list(by_id.values())

    def _from_manifest_file(
        self,
        manifest_path: Path,
        display_path: Path,
        source_type: str,
        fallback_name: str,
    ) -> ModuleInformation:
        try:
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            return _module_information(
                manifest,
                fallback_name=fallback_name,
                source_type=source_type,
                path=display_path,
                status="Installed",
            )
        except (OSError, json.JSONDecodeError, TypeError):
            return ModuleInformation(
                name=fallback_name,
                module_id="Unknown",
                version="Unknown",
                source_type=source_type,
                path=str(display_path),
                status="Invalid manifest",
            )

    def _from_archive(
        self,
        archive_path: Path,
    ) -> ModuleInformation:
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                with archive.open("manifest.json", "r") as stream:
                    raw = stream.read().decode("utf-8")
            manifest = json.loads(raw)
            return _module_information(
                manifest,
                fallback_name=archive_path.stem,
                source_type="LEC archive",
                path=archive_path,
                status="Installed",
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            zipfile.BadZipFile,
            TypeError,
        ):
            return ModuleInformation(
                name=archive_path.stem,
                module_id="Unknown",
                version="Unknown",
                source_type="LEC archive",
                path=str(archive_path),
                status="Invalid archive or manifest",
            )



def _installed_modules_root() -> Path:
    for value in modules_package.__path__:
        candidate = Path(value)

        # The actual source or installed package directory is named
        # 'modules'. The archive extraction cache is named
        # 'module-cache' and must not be used for inventory scanning.
        if candidate.name == "modules":
            return candidate

    return Path(linuxeasyconfig.__file__).resolve().parent / "modules"

def _module_information(
    manifest: dict[str, Any],
    *,
    fallback_name: str,
    source_type: str,
    path: Path,
    status: str,
) -> ModuleInformation:
    return ModuleInformation(
        name=str(manifest.get("name", fallback_name)),
        module_id=str(manifest.get("id", "Unknown")),
        version=str(manifest.get("version", "Unknown")),
        source_type=source_type,
        path=str(path),
        status=status,
    )


def _lec_version(package_root: Path) -> str:
    try:
        return importlib.metadata.version("linuxeasyconfig")
    except importlib.metadata.PackageNotFoundError:
        pass

    pyproject = package_root.parents[1] / "pyproject.toml"

    try:
        import tomllib
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return str(data.get("project", {}).get("version", "Development"))
    except (OSError, ValueError, TypeError):
        return "Development"


def _operating_system() -> str:
    os_release = Path("/etc/os-release")

    try:
        values: dict[str, str] = {}
        for line in os_release.read_text(
            encoding="utf-8"
        ).splitlines():
            key, separator, value = line.partition("=")
            if separator:
                values[key] = value.strip().strip('"')

        if values.get("PRETTY_NAME"):
            return values["PRETTY_NAME"]
    except OSError:
        pass

    return platform.platform()
