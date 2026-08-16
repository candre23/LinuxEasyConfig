from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import linuxeasyconfig.modules as modules_package
from packaging.version import InvalidVersion, Version

from linuxeasyconfig.core.module_loader import (
    USER_MODULES_DIRECTORY,
    clear_packaged_module_cache,
    inspect_module_archive,
    safe_module_package_name,
)

OFFICIAL_MODULE_INDEX_URL = (
    "https://raw.githubusercontent.com/"
    "candre23/LinuxEasyConfig/main/module-repository/index.json"
)
_TRUSTED_DOWNLOAD_HOST = "raw.githubusercontent.com"
_TRUSTED_DOWNLOAD_PREFIX = "/candre23/LinuxEasyConfig/"
_MAX_INDEX_BYTES = 2 * 1024 * 1024
_MAX_MODULE_BYTES = 64 * 1024 * 1024


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
        suffix = " — Override of bundled module" if self.overrides_builtin else ""
        return f"{self.name} ({self.version}){suffix}"


@dataclass(frozen=True)
class SystemModuleUpdate:
    name: str
    module_id: str
    package_name: str
    installed_version: str
    available_version: str
    min_lec_version: str
    download_url: str
    sha256: str
    status: str
    update_available: bool


class ModuleManagementRepository:
    def inspect_import(self, source_path: Path) -> ModuleImportCandidate:
        manifest = inspect_module_archive(source_path)
        module_id = str(manifest["id"])
        builtin = self._builtin_modules()
        custom = self.custom_modules()
        builtin_match = next(
            (item for item in builtin if item["module_id"] == module_id), None
        )
        custom_match = next(
            (item for item in custom if item.module_id == module_id), None
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
            if module.module_id == candidate.module_id and module.path != candidate.destination:
                module.path.unlink(missing_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=".lec-import-", suffix=".tmp", dir=USER_MODULES_DIRECTORY, delete=False
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
        builtin_ids = {str(item["module_id"]) for item in self._builtin_modules()}
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
            raise ValueError("The selected module is not a custom module.") from exc
        module.path.unlink()
        clear_packaged_module_cache()

    def check_system_updates(self) -> list[SystemModuleUpdate]:
        index = self._fetch_index()
        builtins = {str(item["module_id"]): item for item in self._builtin_modules()}
        customs = {item.module_id: item for item in self.custom_modules()}
        lec_version = _current_lec_version()
        updates: list[SystemModuleUpdate] = []
        for raw in index.get("modules", []):
            if not isinstance(raw, dict):
                raise ValueError("The official module index contains an invalid module entry.")
            module_id = _required_text(raw, "id")
            if module_id not in builtins:
                raise ValueError(
                    f"The official module index references unknown system module {module_id!r}."
                )
            builtin = builtins[module_id]
            name = str(raw.get("name", builtin.get("name", builtin["package_name"])))
            available = _required_text(raw, "version")
            minimum = str(raw.get("min_lec_version", "1.0.0")).strip() or "1.0.0"
            download_url = _required_text(raw, "url")
            digest = _required_text(raw, "sha256").lower()
            _validate_download_url(download_url)
            _validate_sha256(digest)
            custom = customs.get(module_id)
            installed = custom.version if custom is not None else str(builtin.get("version", "0"))
            installed_version = _parse_version(installed, f"installed version for {name}")
            available_version = _parse_version(available, f"available version for {name}")
            minimum_version = _parse_version(minimum, f"minimum LEC version for {name}")
            source_type = str(builtin.get("source_type", ""))
            if source_type == "folder":
                status, update_available = "Development source", False
            elif lec_version < minimum_version:
                status, update_available = f"Requires LEC {minimum} or newer", False
            elif available_version > installed_version:
                status, update_available = "Update available", True
            elif installed_version > available_version:
                status, update_available = "Newer version installed", False
            else:
                status, update_available = "Current", False
            updates.append(
                SystemModuleUpdate(
                    name=name,
                    module_id=module_id,
                    package_name=str(builtin["package_name"]),
                    installed_version=installed,
                    available_version=available,
                    min_lec_version=minimum,
                    download_url=download_url,
                    sha256=digest,
                    status=status,
                    update_available=update_available,
                )
            )
        return sorted(updates, key=lambda item: item.name.casefold())

    def install_system_update(self, update: SystemModuleUpdate) -> Path:
        if not update.update_available:
            raise ValueError(f"{update.name} does not have an installable update.")
        _validate_download_url(update.download_url)
        _validate_sha256(update.sha256)
        with tempfile.NamedTemporaryFile(
            prefix=".lec-system-update-", suffix=".lec", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            digest = hashlib.sha256()
            request = Request(
                update.download_url,
                headers={"User-Agent": "LinuxEasyConfig/" + str(_current_lec_version())},
            )
            try:
                with urlopen(request, timeout=30) as response:
                    total = 0
                    with temporary_path.open("wb") as output:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            total += len(chunk)
                            if total > _MAX_MODULE_BYTES:
                                raise ValueError("The downloaded module is larger than the allowed limit.")
                            digest.update(chunk)
                            output.write(chunk)
            except (HTTPError, URLError, TimeoutError) as exc:
                raise RuntimeError(f"Could not download {update.name}: {exc}") from exc
            if digest.hexdigest() != update.sha256:
                raise ValueError(
                    f"Checksum verification failed for {update.name}. The downloaded file was not installed."
                )
            candidate = self.inspect_import(temporary_path)
            if candidate.module_id != update.module_id:
                raise ValueError("The downloaded module ID does not match the official update index.")
            if candidate.version != update.available_version:
                raise ValueError("The downloaded module version does not match the official update index.")
            if not candidate.overrides_builtin:
                raise ValueError("Official system updates may only replace bundled LEC system modules.")
            return self.install(candidate)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _fetch_index(self) -> dict:
        request = Request(
            OFFICIAL_MODULE_INDEX_URL,
            headers={"User-Agent": "LinuxEasyConfig/" + str(_current_lec_version())},
        )
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read(_MAX_INDEX_BYTES + 1)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"Could not contact the official Linux Easy Config module repository: {exc}"
            ) from exc
        if len(raw) > _MAX_INDEX_BYTES:
            raise ValueError("The official module index is unexpectedly large.")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("The official module index is not valid JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("The official module index has an invalid format.")
        if value.get("schema_version") != 1:
            raise ValueError("The official module index uses an unsupported schema version.")
        if not isinstance(value.get("modules"), list):
            raise ValueError("The official module index is missing its module list.")
        return value

    def _builtin_modules(self) -> list[dict[str, str]]:
        modules_root = self._builtin_modules_root()
        modules: list[dict[str, str]] = []
        if not modules_root.is_dir():
            return modules
        candidates = sorted(
            modules_root.iterdir(),
            key=lambda path: (0 if path.is_dir() else 1, path.name.casefold()),
        )
        selected_ids: set[str] = set()
        for path in candidates:
            if path.is_dir():
                manifest_path = path / "manifest.json"
                if not manifest_path.is_file():
                    continue
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                package_name, source_type = path.name, "folder"
            elif path.suffix.lower() == ".lec":
                try:
                    with zipfile.ZipFile(path, "r") as archive:
                        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                except (
                    OSError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                    KeyError,
                    zipfile.BadZipFile,
                ):
                    continue
                package_name, source_type = path.stem, "archive"
            else:
                continue
            module_id = str(manifest.get("id", ""))
            if not module_id or module_id in selected_ids:
                continue
            selected_ids.add(module_id)
            modules.append(
                {
                    "module_id": module_id,
                    "package_name": package_name,
                    "name": str(manifest.get("name", package_name)),
                    "version": str(manifest.get("version", "0")),
                    "source_type": source_type,
                }
            )
        return modules

    @staticmethod
    def _builtin_modules_root() -> Path:
        for value in modules_package.__path__:
            candidate = Path(value)
            if candidate.name == "modules":
                return candidate
        raise RuntimeError("The built-in modules directory could not be located.")


def _current_lec_version() -> Version:
    try:
        value = package_version("linuxeasyconfig")
    except PackageNotFoundError:
        value = "1.0.2"
    return _parse_version(value, "Linux Easy Config version")


def _parse_version(value: str, description: str) -> Version:
    try:
        return Version(str(value))
    except InvalidVersion as exc:
        raise ValueError(f"Invalid {description}: {value!r}.") from exc


def _required_text(value: dict, key: str) -> str:
    result = str(value.get(key, "")).strip()
    if not result:
        raise ValueError(f"The official module index entry is missing {key!r}.")
    return result


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("The official module index contains an invalid SHA-256 checksum.")


def _validate_download_url(value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != _TRUSTED_DOWNLOAD_HOST
        or not parsed.path.startswith(_TRUSTED_DOWNLOAD_PREFIX)
    ):
        raise ValueError("The official module index contains an untrusted download URL.")
