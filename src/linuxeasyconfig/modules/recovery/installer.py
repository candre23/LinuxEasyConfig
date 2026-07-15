from __future__ import annotations

import os
from pathlib import Path

from linuxeasyconfig.core.config.audit_log import AuditLog
from linuxeasyconfig.core.config.base import ConfigurationDocument
from linuxeasyconfig.core.config.writer import ConfigurationWriter


MODULE_ID = "org.linuxeasyconfig.recovery"
BACKUP_ROOT = Path(
    "/var/lib/linuxeasyconfig/backups"
)
AUDIT_PATH = Path(
    "/var/lib/linuxeasyconfig/audit.jsonl"
)


class RestoredConfiguration(
    ConfigurationDocument
):
    def __init__(self, text: str) -> None:
        self._text = text

    def render(self) -> str:
        return (
            self._text
            if self._text.endswith("\n")
            else self._text + "\n"
        )


def restore_revision(
    *,
    source_module_id: str,
    revision: int,
    destination: str,
    backup_path: str,
    restore_mode: str,
) -> str:
    destination_path = Path(destination)

    if not destination_path.is_absolute():
        raise ValueError(
            "The recovery destination must be an absolute path."
        )

    if destination_path == Path("/"):
        raise ValueError(
            "The root directory cannot be restored."
        )

    if restore_mode not in {
        "file",
        "delete",
    }:
        raise ValueError(
            "This revision does not have a restorable backup."
        )

    writer = ConfigurationWriter(
        backup_root=BACKUP_ROOT,
        audit_log=AuditLog(AUDIT_PATH),
    )

    if restore_mode == "delete":
        if destination_path.exists():
            result = writer.delete(
                module_id=MODULE_ID,
                destination=destination_path,
            )
            return (
                f"Removed {destination_path} to restore the "
                f"state before {source_module_id} revision "
                f"{revision}. Recovery revision "
                f"{result.revision} recorded."
            )

        return (
            f"{destination_path} was already absent. "
            "No change was needed."
        )

    backup = _validate_backup_path(
        backup_path=backup_path,
        source_module_id=source_module_id,
        revision=revision,
        destination=destination_path,
    )

    raw = backup.read_bytes()

    if b"\0" in raw:
        raise ValueError(
            "Binary backup restoration is not supported by "
            "this recovery module."
        )

    text = raw.decode(
        "utf-8",
        errors="strict",
    )

    result = writer.write(
        module_id=MODULE_ID,
        destination=destination_path,
        document=RestoredConfiguration(text),
    )

    _restore_mode_from_backup(
        backup,
        destination_path,
    )

    return (
        f"Restored {destination_path} from "
        f"{source_module_id} revision {revision}. "
        f"Recovery revision {result.revision} recorded."
    )


def _validate_backup_path(
    *,
    backup_path: str,
    source_module_id: str,
    revision: int,
    destination: Path,
) -> Path:
    if not backup_path:
        raise ValueError(
            "The selected revision does not specify a backup file."
        )

    backup = Path(backup_path)

    if not backup.is_absolute():
        raise ValueError(
            "The backup path must be absolute."
        )

    try:
        resolved_backup = backup.resolve(strict=True)
        resolved_root = BACKUP_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ValueError(
            f"The backup file is unavailable: {exc}"
        ) from exc

    try:
        resolved_backup.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(
            "The selected backup is outside LEC's backup directory."
        ) from exc

    expected_roots = (
        BACKUP_ROOT
        / source_module_id
        / f"rev{revision:06d}",
        BACKUP_ROOT
        / source_module_id
        / f"rev{revision}",
    )

    if not any(
        _is_beneath(
            resolved_backup,
            root,
        )
        for root in expected_roots
    ):
        raise ValueError(
            "The backup does not match the selected module revision."
        )

    if not resolved_backup.is_file():
        raise ValueError(
            "The selected backup is not a regular file."
        )

    expected_suffix = Path(
        str(destination).lstrip(os.sep)
    )

    if not str(resolved_backup).endswith(
        str(expected_suffix)
    ):
        raise ValueError(
            "The backup does not match the selected destination."
        )

    return resolved_backup


def _is_beneath(
    path: Path,
    root: Path,
) -> bool:
    try:
        path.relative_to(
            root.resolve(strict=False)
        )
        return True
    except ValueError:
        return False


def _restore_mode_from_backup(
    backup: Path,
    destination: Path,
) -> None:
    try:
        mode = backup.stat().st_mode & 0o7777
        os.chmod(destination, mode)
    except OSError:
        pass
