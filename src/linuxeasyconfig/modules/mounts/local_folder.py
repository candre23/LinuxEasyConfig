from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalFolderPreview:
    source: str
    mountpoint: str
    filesystem: str
    options: tuple[str, ...]
    fstab_line: str


def build_local_folder_preview(
    *,
    source: str,
    mountpoint: str,
    read_only: bool,
    startup_mode: str,
) -> LocalFolderPreview:
    source_path = _validate_source(source)
    mountpoint_path = _validate_mountpoint(mountpoint)

    if source_path == mountpoint_path:
        raise ValueError(
            "The source folder and mount point must be different."
        )

    if _is_inside(source_path, mountpoint_path):
        raise ValueError(
            "The mount point cannot be inside the source folder."
        )

    options = _build_options(
        read_only=read_only,
        startup_mode=startup_mode,
    )

    source_text = str(source_path)
    mountpoint_text = str(mountpoint_path)

    return LocalFolderPreview(
        source=source_text,
        mountpoint=mountpoint_text,
        filesystem="none",
        options=tuple(options),
        fstab_line=(
            f"{_escape_fstab(source_text)} "
            f"{_escape_fstab(mountpoint_text)} "
            f"none {','.join(options)} 0 0"
        ),
    )


def suggested_mountpoint(source: str) -> str:
    source_path = Path(source.strip())
    name = source_path.name or "folder"
    return f"/mnt/{name}"


def _build_options(
    *,
    read_only: bool,
    startup_mode: str,
) -> list[str]:
    mode = startup_mode.strip().lower()

    options = ["bind"]
    options.append("ro" if read_only else "rw")
    options.append("nofail")

    if mode == "manual":
        options.append("noauto")
    elif mode == "startup":
        pass
    elif mode == "on-demand":
        options.extend(
            [
                "x-systemd.automount",
                "x-systemd.idle-timeout=60",
            ]
        )
    else:
        raise ValueError(
            f"Unknown startup mode: {startup_mode}"
        )

    return options


def _validate_source(value: str) -> Path:
    text = value.strip()

    if not text:
        raise ValueError("Select a source folder.")

    path = Path(os.path.normpath(text))

    if not path.is_absolute():
        raise ValueError(
            "The source folder must use an absolute path."
        )

    if not path.is_dir():
        raise ValueError(
            "The selected source folder does not exist."
        )

    return path


def _validate_mountpoint(value: str) -> Path:
    text = value.strip()

    if not text:
        raise ValueError("Enter a local mount point.")

    path = Path(os.path.normpath(text))

    if not path.is_absolute() or path == Path("/"):
        raise ValueError(
            "The mount point must be an absolute path other than /."
        )

    return path


def _is_inside(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _escape_fstab(value: str) -> str:
    return (
        value.replace("\\", "\\134")
        .replace(" ", "\\040")
        .replace("\t", "\\011")
    )
