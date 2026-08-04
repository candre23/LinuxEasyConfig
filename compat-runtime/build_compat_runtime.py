#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PACKAGE_NAME = "linuxeasyconfig-qt-runtime"
RUNTIME_VERSION = "6.11.1"
PACKAGE_REVISION = "1"
ARCHITECTURE = "amd64"
INSTALL_ROOT = Path("opt/linuxeasyconfig/qt-runtime")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def write_control(package_root: Path) -> None:
    debian = package_root / "DEBIAN"
    debian.mkdir(parents=True, exist_ok=True)

    control = f"""Package: {PACKAGE_NAME}
Version: {RUNTIME_VERSION}-{PACKAGE_REVISION}
Section: libs
Priority: optional
Architecture: {ARCHITECTURE}
Maintainer: Linux Easy Config Project <candre23@users.noreply.github.com>
Depends: python3 (>= 3.12), python3 (<< 3.15), libc6 (>= 2.34), libegl1, libgl1, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0
Provides: python3-pyside6.qtcore, python3-pyside6.qtgui, python3-pyside6.qtwidgets
Description: Private Qt for Python runtime for Linux Easy Config
 This package installs PySide6 Essentials and Shiboken6 under
 /opt/linuxeasyconfig/qt-runtime. It is intended for supported systems
 whose repositories do not provide the native PySide6 packages required
 by Linux Easy Config.
"""
    (debian / "control").write_text(control, encoding="utf-8")


def prune_runtime(runtime: Path) -> None:
    for cache in runtime.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)

    for pattern in ("*.pyc", "*.pyo"):
        for bytecode in runtime.rglob(pattern):
            bytecode.unlink(missing_ok=True)

    for directory_name in ("bin", "include", "share"):
        candidate = runtime / directory_name
        if candidate.exists():
            shutil.rmtree(candidate)

    pyside_bin = runtime / "PySide6"
    for tool_name in (
        "assistant",
        "designer",
        "linguist",
        "lrelease",
        "lupdate",
        "qml",
        "qmlformat",
        "qmllint",
        "qmltyperegistrar",
        "rcc",
        "uic",
    ):
        candidate = pyside_bin / tool_name
        candidate.unlink(missing_ok=True)


def validate_runtime(runtime: Path) -> None:
    required = [
        runtime / "PySide6" / "__init__.py",
        runtime / "PySide6" / "QtCore.abi3.so",
        runtime / "PySide6" / "QtGui.abi3.so",
        runtime / "PySide6" / "QtWidgets.abi3.so",
        runtime / "shiboken6" / "__init__.py",
    ]

    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(
            "Downloaded runtime is incomplete:\n"
            + "\n".join(missing)
        )


def build(output_directory: Path) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / (
        f"{PACKAGE_NAME}_{RUNTIME_VERSION}-{PACKAGE_REVISION}_{ARCHITECTURE}.deb"
    )

    with tempfile.TemporaryDirectory(prefix="lec-qt-runtime-") as temp_name:
        temp = Path(temp_name)
        package_root = temp / "package"
        runtime = package_root / INSTALL_ROOT
        runtime.mkdir(parents=True)

        run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-compile",
                "--ignore-installed",
                "--only-binary=:all:",
                "--target",
                str(runtime),
                f"PySide6-Essentials=={RUNTIME_VERSION}",
                f"shiboken6=={RUNTIME_VERSION}",
            ]
        )

        prune_runtime(runtime)
        validate_runtime(runtime)
        write_control(package_root)

        run(
            [
                "dpkg-deb",
                "--root-owner-group",
                "--build",
                str(package_root),
                str(output_path),
            ]
        )

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the reusable Linux Easy Config "
            "PySide6 compatibility runtime package."
        )
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path.cwd().parent,
        help=(
            "Directory in which to place the .deb. "
            "Defaults to the parent of the current directory."
        ),
    )
    arguments = parser.parse_args()

    if shutil.which("dpkg-deb") is None:
        raise SystemExit("dpkg-deb is required.")

    try:
        import pip  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Python pip is required. Install python3-pip."
        ) from exc

    output = build(arguments.output_directory.resolve())
    print(f"\nBuilt: {output}")
    print(
        "Install this package before Linux Easy Config "
        "on systems without native PySide6 packages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
