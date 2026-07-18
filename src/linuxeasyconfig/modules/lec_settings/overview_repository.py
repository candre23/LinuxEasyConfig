from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path


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
        package_root = Path(__file__).resolve().parents[2]
        modules_root = package_root / "modules"
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
        discovered: list[ModuleInformation] = []

        if not modules_root.is_dir():
            return discovered

        for candidate in sorted(modules_root.iterdir()):
            if candidate.name.startswith((".", "_")):
                continue

            manifest_path = candidate / "manifest.json"

            if not manifest_path.is_file():
                continue

            try:
                manifest = json.loads(
                    manifest_path.read_text(
                        encoding="utf-8"
                    )
                )
            except (OSError, json.JSONDecodeError):
                discovered.append(
                    ModuleInformation(
                        name=candidate.name,
                        module_id="Unknown",
                        version="Unknown",
                        source_type="Folder",
                        path=str(candidate),
                        status="Invalid manifest",
                    )
                )
                continue

            discovered.append(
                ModuleInformation(
                    name=str(
                        manifest.get(
                            "name",
                            candidate.name,
                        )
                    ),
                    module_id=str(
                        manifest.get("id", "Unknown")
                    ),
                    version=str(
                        manifest.get(
                            "version",
                            "Unknown",
                        )
                    ),
                    source_type=_source_type(candidate),
                    path=str(candidate),
                    status="Installed",
                )
            )

        return discovered


def _lec_version(package_root: Path) -> str:
    try:
        return importlib.metadata.version(
            "linuxeasyconfig"
        )
    except importlib.metadata.PackageNotFoundError:
        pass

    pyproject = package_root.parents[1] / "pyproject.toml"

    try:
        import tomllib

        data = tomllib.loads(
            pyproject.read_text(encoding="utf-8")
        )
        return str(
            data.get("project", {}).get(
                "version",
                "Development",
            )
        )
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


def _source_type(path: Path) -> str:
    text = str(path)

    if "module-cache" in text:
        return "LEC archive"

    return "Folder"
