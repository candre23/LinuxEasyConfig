#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


DEFAULT_MODULES = (
    "services",
    "user_permissions",
    "firewall",
    "reverse_proxy",
)

EXCLUDED_DIRECTORY_NAMES = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".swp",
    ".tmp",
    ".bak",
}


def package_module(
    module_directory: Path,
    output_path: Path,
) -> None:
    manifest_path = (
        module_directory / "manifest.json"
    )

    if not manifest_path.is_file():
        raise ValueError(
            f"{module_directory} does not contain "
            "manifest.json."
        )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    for required in (
        "id",
        "name",
        "version",
        "entry_point",
    ):
        if not str(
            manifest.get(required, "")
        ).strip():
            raise ValueError(
                f"{manifest_path} is missing "
                f"{required!r}."
            )

    if not (
        module_directory / "__init__.py"
    ).is_file():
        raise ValueError(
            f"{module_directory} must contain "
            "__init__.py."
        )

    files = [
        path
        for path in module_directory.rglob("*")
        if _include_path(
            path,
            module_directory,
        )
    ]

    if not files:
        raise ValueError(
            f"{module_directory} contains no "
            "packageable files."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=output_path.name + ".",
            suffix=".tmp",
            dir=output_path.parent,
        )
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for source_path in sorted(files):
                relative = source_path.relative_to(
                    module_directory
                )
                archive_name = PurePosixPath(
                    *relative.parts
                ).as_posix()

                archive.write(
                    source_path,
                    arcname=archive_name,
                )

            archive.comment = (
                "Linux Easy Config module archive"
            ).encode("utf-8")

        with zipfile.ZipFile(
            temporary_path,
            mode="r",
        ) as archive:
            names = set(archive.namelist())

            if "manifest.json" not in names:
                raise RuntimeError(
                    "Packaged archive is missing "
                    "manifest.json."
                )

            if "__init__.py" not in names:
                raise RuntimeError(
                    "Packaged archive is missing "
                    "__init__.py."
                )

            bad_entry = archive.testzip()

            if bad_entry is not None:
                raise RuntimeError(
                    "Archive verification failed "
                    f"for {bad_entry}."
                )

        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(
            missing_ok=True
        )
        raise


def _include_path(
    path: Path,
    module_directory: Path,
) -> bool:
    if not path.is_file():
        return False

    relative = path.relative_to(
        module_directory
    )

    if any(
        part in EXCLUDED_DIRECTORY_NAMES
        for part in relative.parts
    ):
        return False

    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False

    if path.name.startswith("."):
        return False

    return True


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Package LEC module folders as "
            "single-file .lec archives."
        )
    )
    parser.add_argument(
        "modules",
        nargs="*",
        default=list(DEFAULT_MODULES),
        help=(
            "Module folder names to package. "
            "Defaults to the completed modules."
        ),
    )
    parser.add_argument(
        "--modules-directory",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "src"
            / "linuxeasyconfig"
            / "modules"
        ),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=None,
        help=(
            "Destination directory. Defaults to "
            "the modules directory."
        ),
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    modules_directory = (
        arguments.modules_directory.resolve()
    )
    output_directory = (
        arguments.output_directory.resolve()
        if arguments.output_directory is not None
        else modules_directory
    )

    for module_name in arguments.modules:
        module_directory = (
            modules_directory / module_name
        )
        output_path = (
            output_directory
            / f"{module_name}.lec"
        )

        if not module_directory.is_dir():
            raise FileNotFoundError(
                f"Module folder not found: "
                f"{module_directory}"
            )

        package_module(
            module_directory,
            output_path,
        )
        print(
            f"Created {output_path}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
