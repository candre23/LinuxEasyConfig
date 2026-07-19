#!/usr/bin/env python3
"""Build deterministic .lec archives for all built-in LEC modules.

The source tree keeps each module unpacked for readability. During packaging,
this script creates one sibling .lec archive for every module directory that
contains manifest.json. The original directories are never modified.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys
import zipfile

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".bak",
    ".swp",
}

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def should_include(path: Path, module_dir: Path) -> bool:
    relative = path.relative_to(module_dir)

    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False

    if path.name.endswith("~"):
        return False

    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False

    return path.is_file()


def archive_info(relative_path: str, source: Path) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(relative_path, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3

    mode = source.stat().st_mode
    executable = bool(mode & stat.S_IXUSR)
    permissions = 0o755 if executable else 0o644
    info.external_attr = permissions << 16

    return info


def build_archive(module_dir: Path, output_path: Path) -> None:
    files = sorted(
        (
            path
            for path in module_dir.rglob("*")
            if should_include(path, module_dir)
        ),
        key=lambda path: path.relative_to(module_dir).as_posix(),
    )

    manifest = module_dir / "manifest.json"
    if manifest not in files:
        raise RuntimeError(f"Missing manifest.json in {module_dir}")

    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.unlink(missing_ok=True)

    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for source in files:
                relative_path = source.relative_to(module_dir).as_posix()
                info = archive_info(relative_path, source)
                archive.writestr(info, source.read_bytes())

        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create deterministic .lec archives for built-in modules."
    )
    parser.add_argument(
        "--modules-dir",
        type=Path,
        default=Path("src/linuxeasyconfig/modules"),
        help="Directory containing unpacked built-in module folders.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove generated .lec archives instead of building them.",
    )
    args = parser.parse_args()

    modules_dir = args.modules_dir.resolve()
    if not modules_dir.is_dir():
        print(f"Modules directory does not exist: {modules_dir}", file=sys.stderr)
        return 1

    module_dirs = sorted(
        (
            path
            for path in modules_dir.iterdir()
            if path.is_dir() and (path / "manifest.json").is_file()
        ),
        key=lambda path: path.name,
    )

    if args.clean:
        removed = 0
        for archive_path in sorted(modules_dir.glob("*.lec")):
            archive_path.unlink()
            print(f"Removed {archive_path.relative_to(Path.cwd())}")
            removed += 1
        print(f"Removed {removed} generated archive(s).")
        return 0

    if not module_dirs:
        print(f"No module directories found under {modules_dir}", file=sys.stderr)
        return 1

    expected_outputs: set[Path] = set()

    for module_dir in module_dirs:
        output_path = modules_dir / f"{module_dir.name}.lec"
        expected_outputs.add(output_path)
        build_archive(module_dir, output_path)
        print(
            f"Built {output_path.relative_to(Path.cwd())} "
            f"from {module_dir.relative_to(Path.cwd())}"
        )

    for archive_path in modules_dir.glob("*.lec"):
        if archive_path not in expected_outputs:
            archive_path.unlink()
            print(f"Removed stale archive {archive_path.relative_to(Path.cwd())}")

    print(f"Built {len(module_dirs)} module archive(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
