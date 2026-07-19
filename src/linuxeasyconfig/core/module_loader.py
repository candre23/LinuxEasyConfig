from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import stat
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from platformdirs import user_cache_path, user_data_path

from linuxeasyconfig.core.manifest_schema import MANIFEST_SCHEMA
from linuxeasyconfig.core.module_api import LECModule


_ARCHIVE_SUFFIX = ".lec"
_CACHE_ROOT = user_cache_path(
    "linuxeasyconfig",
    appauthor=False,
) / "module-cache"

USER_MODULES_DIRECTORY = user_data_path(
    "linuxeasyconfig",
    appauthor=False,
) / "modules"


@dataclass(frozen=True)
class ModuleRecord:
    module_path: Path
    manifest_path: Path
    manifest: dict[str, Any]
    instance: LECModule
    source_path: Path | None = None
    packaged: bool = False


@dataclass(frozen=True)
class ModuleLoadError:
    module_path: Path
    message: str


def _load_module_instance(
    module_path: Path,
    manifest: dict[str, Any],
) -> LECModule:
    entry_module_name, class_name = manifest[
        "entry_point"
    ].split(":", maxsplit=1)

    package_name = (
        f"linuxeasyconfig.modules.{module_path.name}"
    )
    import_name = (
        f"{package_name}.{entry_module_name}"
    )

    imported_module = importlib.import_module(
        import_name
    )

    try:
        module_class = getattr(
            imported_module,
            class_name,
        )
    except AttributeError as exc:
        raise ImportError(
            f"Entry-point class {class_name!r} "
            f"was not found in {import_name!r}."
        ) from exc

    instance = module_class()

    if not isinstance(instance, LECModule):
        raise TypeError(
            f"Entry point "
            f"{manifest['entry_point']!r} "
            "does not implement LECModule."
        )

    return instance


def discover_modules(
    modules_directory: Path,
    user_modules_directory: Path | None = None,
) -> tuple[
    list[ModuleRecord],
    list[ModuleLoadError],
]:
    modules: list[ModuleRecord] = []
    errors: list[ModuleLoadError] = []

    if not modules_directory.exists():
        return modules, errors

    validator = Draft202012Validator(MANIFEST_SCHEMA)
    _prepare_archive_import_path()

    folder_records, folder_errors = _discover_folder_modules(
        modules_directory,
        validator,
    )
    modules.extend(folder_records)
    errors.extend(folder_errors)

    loaded_ids = {
        str(record.manifest["id"])
        for record in folder_records
    }

    if user_modules_directory is not None:
        user_records, user_errors = _discover_archive_modules(
            user_modules_directory,
            validator,
            excluded_ids=loaded_ids,
        )
        modules.extend(user_records)
        errors.extend(user_errors)
        loaded_ids.update(
            str(record.manifest["id"])
            for record in user_records
        )

    archive_records, archive_errors = _discover_archive_modules(
        modules_directory,
        validator,
        excluded_ids=loaded_ids,
    )
    modules.extend(archive_records)
    errors.extend(archive_errors)

    return modules, errors

def _discover_folder_modules(
    modules_directory: Path,
    validator: Draft202012Validator,
) -> tuple[
    list[ModuleRecord],
    list[ModuleLoadError],
]:
    modules: list[ModuleRecord] = []
    errors: list[ModuleLoadError] = []

    module_paths = sorted(
        path
        for path in modules_directory.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
    )

    for module_path in module_paths:
        manifest_path = (
            module_path / "manifest.json"
        )

        if not manifest_path.is_file():
            continue

        record, error = _load_record(
            module_path=module_path,
            manifest_path=manifest_path,
            validator=validator,
            source_path=module_path,
            packaged=False,
        )

        if error is not None:
            errors.append(error)
        elif record is not None:
            modules.append(record)

    return modules, errors


def _discover_archive_modules(
    modules_directory: Path,
    validator: Draft202012Validator,
    excluded_ids: set[str],
) -> tuple[
    list[ModuleRecord],
    list[ModuleLoadError],
]:
    modules: list[ModuleRecord] = []
    errors: list[ModuleLoadError] = []
    archive_ids: set[str] = set()

    if not modules_directory.is_dir():
        return modules, errors

    for archive_path in sorted(modules_directory.glob("*.lec")):
        manifest, manifest_error = _read_archive_manifest(
            archive_path,
            validator,
        )

        if manifest_error is not None:
            errors.append(
                ModuleLoadError(
                    module_path=archive_path,
                    message=manifest_error,
                )
            )
            continue

        assert manifest is not None
        module_id = str(manifest["id"])

        if module_id in excluded_ids:
            continue

        if module_id in archive_ids:
            errors.append(
                ModuleLoadError(
                    module_path=archive_path,
                    message=(
                        "Another packaged module with ID "
                        f"{module_id!r} was already loaded "
                        "from this module source."
                    ),
                )
            )
            continue

        try:
            extracted_path = _extract_archive_to_cache(archive_path)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            errors.append(
                ModuleLoadError(
                    module_path=archive_path,
                    message=f"Could not prepare packaged module: {exc}",
                )
            )
            continue

        record, error = _load_record(
            module_path=extracted_path,
            manifest_path=extracted_path / "manifest.json",
            validator=validator,
            source_path=archive_path,
            packaged=True,
            preloaded_manifest=manifest,
        )

        if error is not None:
            errors.append(error)
            continue

        if record is not None:
            archive_ids.add(module_id)
            modules.append(record)

    return modules, errors


def _read_archive_manifest(
    archive_path: Path,
    validator: Draft202012Validator,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            members = archive.infolist()
            if not members:
                return None, "The .lec archive is empty."

            for member in members:
                _validated_member_path(member)

            try:
                raw = archive.read("manifest.json")
            except KeyError:
                return None, (
                    "The .lec archive does not contain "
                    "manifest.json at its root."
                )

        manifest = json.loads(raw.decode("utf-8"))
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        zipfile.BadZipFile,
    ) as exc:
        return None, f"Could not read packaged module: {exc}"

    validation_errors = sorted(
        validator.iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )

    if validation_errors:
        messages: list[str] = []
        for error in validation_errors:
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            messages.append(
                f"{location or 'manifest'}: {error.message}"
            )
        return None, "; ".join(messages)

    return manifest, None


def inspect_module_archive(archive_path: Path) -> dict[str, Any]:
    """Validate a .lec archive and return its manifest."""
    if archive_path.suffix.lower() != _ARCHIVE_SUFFIX:
        raise ValueError("Module files must use the .lec extension.")

    manifest, error = _read_archive_manifest(
        archive_path,
        Draft202012Validator(MANIFEST_SCHEMA),
    )
    if error is not None:
        raise ValueError(error)

    assert manifest is not None
    return manifest


def safe_module_package_name(value: str) -> str:
    return _safe_module_directory_name(value)

def _load_record(
    *,
    module_path: Path,
    manifest_path: Path,
    validator: Draft202012Validator,
    source_path: Path,
    packaged: bool,
    preloaded_manifest: (
        dict[str, Any] | None
    ) = None,
) -> tuple[
    ModuleRecord | None,
    ModuleLoadError | None,
]:
    if preloaded_manifest is None:
        manifest, manifest_error = (
            _read_and_validate_manifest(
                manifest_path,
                validator,
            )
        )

        if manifest_error is not None:
            return (
                None,
                ModuleLoadError(
                    module_path=source_path,
                    message=manifest_error,
                ),
            )
    else:
        manifest = preloaded_manifest

    assert manifest is not None

    try:
        instance = _load_module_instance(
            module_path,
            manifest,
        )
    except (
        ImportError,
        TypeError,
        ValueError,
    ) as exc:
        return (
            None,
            ModuleLoadError(
                module_path=source_path,
                message=(
                    "Could not load module "
                    f"entry point: {exc}"
                ),
            ),
        )

    return (
        ModuleRecord(
            module_path=module_path,
            manifest_path=manifest_path,
            manifest=manifest,
            instance=instance,
            source_path=source_path,
            packaged=packaged,
        ),
        None,
    )


def _read_and_validate_manifest(
    manifest_path: Path,
    validator: Draft202012Validator,
) -> tuple[
    dict[str, Any] | None,
    str | None,
]:
    try:
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return (
            None,
            f"Could not read manifest: {exc}",
        )

    validation_errors = sorted(
        validator.iter_errors(manifest),
        key=lambda error: list(
            error.absolute_path
        ),
    )

    if validation_errors:
        messages: list[str] = []

        for error in validation_errors:
            location = ".".join(
                str(part)
                for part in error.absolute_path
            )
            messages.append(
                f"{location or 'manifest'}: "
                f"{error.message}"
            )

        return None, "; ".join(messages)

    return manifest, None


def _prepare_archive_import_path() -> None:
    _CACHE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    modules_package = importlib.import_module(
        "linuxeasyconfig.modules"
    )
    package_paths = getattr(
        modules_package,
        "__path__",
        None,
    )

    if package_paths is None:
        raise RuntimeError(
            "linuxeasyconfig.modules is not "
            "a package."
        )

    cache_text = str(_CACHE_ROOT)

    if cache_text not in package_paths:
        package_paths.append(cache_text)


def _extract_archive_to_cache(
    archive_path: Path,
) -> Path:
    digest = _archive_digest(archive_path)
    safe_stem = _safe_module_directory_name(
        archive_path.stem
    )
    # The extracted directory name must exactly match the Python
    # package name. linuxeasyconfig.modules.__path__ points at
    # _CACHE_ROOT, so dynamic_dns must live at _CACHE_ROOT/dynamic_dns.
    destination = _CACHE_ROOT / safe_stem
    completion_marker = destination / ".lec-complete"

    if completion_marker.is_file():
        try:
            if (
                completion_marker.read_text(
                    encoding="utf-8"
                ).strip()
                == digest
            ):
                return destination
        except OSError:
            pass

    temporary = destination.with_name(
        destination.name + ".tmp"
    )

    if temporary.exists():
        shutil.rmtree(temporary)

    temporary.mkdir(
        parents=True,
        exist_ok=False,
    )

    try:
        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:
            members = archive.infolist()

            if not members:
                raise ValueError(
                    "The archive is empty."
                )

            for member in members:
                relative_path = (
                    _validated_member_path(
                        member
                    )
                )
                target = (
                    temporary / relative_path
                )

                if member.is_dir():
                    target.mkdir(
                        parents=True,
                        exist_ok=True,
                    )
                    continue

                target.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                with archive.open(
                    member,
                    "r",
                ) as source:
                    with target.open(
                        "wb",
                    ) as output:
                        shutil.copyfileobj(
                            source,
                            output,
                        )

        if not (
            temporary / "manifest.json"
        ).is_file():
            raise ValueError(
                "manifest.json must be stored "
                "at the archive root."
            )

        if destination.exists():
            shutil.rmtree(destination)

        temporary.replace(destination)
        completion_marker.write_text(
            digest + "\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )
        raise

    return destination


def _validated_member_path(
    member: zipfile.ZipInfo,
) -> Path:
    raw_name = member.filename

    if "\\" in raw_name:
        raise ValueError(
            "Archive entries must use forward "
            "slashes."
        )

    pure_path = PurePosixPath(raw_name)

    if (
        pure_path.is_absolute()
        or ".." in pure_path.parts
        or not pure_path.parts
    ):
        raise ValueError(
            f"Unsafe archive path: {raw_name!r}"
        )

    mode = member.external_attr >> 16

    if stat.S_ISLNK(mode):
        raise ValueError(
            "Symbolic links are not permitted "
            "inside .lec archives."
        )

    return Path(*pure_path.parts)


def _archive_digest(
    archive_path: Path,
) -> str:
    hasher = hashlib.sha256()

    with archive_path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            hasher.update(block)

    return hasher.hexdigest()


def _safe_module_directory_name(
    value: str,
) -> str:
    cleaned = "".join(
        character
        if (
            character.isalnum()
            or character == "_"
        )
        else "_"
        for character in value
    ).strip("_")

    if not cleaned:
        cleaned = "module"

    if cleaned[0].isdigit():
        cleaned = f"module_{cleaned}"

    return cleaned



def active_module_package_names(
    modules_directory: Path,
    user_modules_directory: Path | None = None,
) -> tuple[list[str], list[ModuleLoadError]]:
    """Return import package names for the active module set."""
    names: list[str] = []
    errors: list[ModuleLoadError] = []

    if not modules_directory.exists():
        return names, errors

    validator = Draft202012Validator(MANIFEST_SCHEMA)
    _prepare_archive_import_path()
    selected_ids: set[str] = set()

    for module_path in sorted(
        path
        for path in modules_directory.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ):
        manifest_path = module_path / "manifest.json"
        if not manifest_path.is_file():
            continue

        manifest, manifest_error = _read_and_validate_manifest(
            manifest_path,
            validator,
        )
        if manifest_error is not None:
            errors.append(
                ModuleLoadError(module_path, manifest_error)
            )
            continue

        assert manifest is not None
        selected_ids.add(str(manifest["id"]))
        names.append(module_path.name)

    archive_sources: list[Path] = []
    if user_modules_directory is not None:
        archive_sources.append(user_modules_directory)
    archive_sources.append(modules_directory)

    for source_directory in archive_sources:
        if not source_directory.is_dir():
            continue

        source_ids: set[str] = set()
        for archive_path in sorted(source_directory.glob("*.lec")):
            manifest, manifest_error = _read_archive_manifest(
                archive_path,
                validator,
            )
            if manifest_error is not None:
                errors.append(
                    ModuleLoadError(archive_path, manifest_error)
                )
                continue

            assert manifest is not None
            module_id = str(manifest["id"])
            if module_id in selected_ids:
                continue

            if module_id in source_ids:
                errors.append(
                    ModuleLoadError(
                        archive_path,
                        (
                            "Another packaged module with ID "
                            f"{module_id!r} was already selected "
                            "from this module source."
                        ),
                    )
                )
                continue

            try:
                extracted_path = _extract_archive_to_cache(archive_path)
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                errors.append(
                    ModuleLoadError(
                        archive_path,
                        f"Could not prepare packaged module: {exc}",
                    )
                )
                continue

            source_ids.add(module_id)
            selected_ids.add(module_id)
            names.append(extracted_path.name)

    return names, errors

def clear_packaged_module_cache() -> None:
    """
    Remove extracted .lec modules.

    This is primarily useful for troubleshooting.
    Normal archive updates use content-addressed
    cache directories and do not require manual
    cache clearing.
    """
    if _CACHE_ROOT.exists():
        shutil.rmtree(_CACHE_ROOT)

    for module_name in tuple(sys.modules):
        if module_name.startswith(
            "linuxeasyconfig.modules."
        ):
            sys.modules.pop(
                module_name,
                None,
            )
