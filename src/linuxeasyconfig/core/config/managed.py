from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from linuxeasyconfig.core.config.audit_log import AuditLog
from linuxeasyconfig.core.config.base import ConfigurationDocument
from linuxeasyconfig.core.config.writer import ConfigurationWriter


DEFAULT_BACKUP_ROOT = Path(
    "/var/lib/linuxeasyconfig/backups"
)
DEFAULT_AUDIT_PATH = Path(
    "/var/lib/linuxeasyconfig/audit.jsonl"
)


class TextConfiguration(ConfigurationDocument):
    def __init__(
        self,
        text: str,
        *,
        ensure_trailing_newline: bool = True,
    ) -> None:
        self._text = text
        self._ensure_trailing_newline = (
            ensure_trailing_newline
        )

    def render(self) -> str:
        if (
            self._ensure_trailing_newline
            and self._text
            and not self._text.endswith("\n")
        ):
            return self._text + "\n"

        return self._text


@dataclass(frozen=True)
class ExternalTextFileSnapshot:
    path: Path
    existed: bool
    text: str
    mode: int | None


def configuration_writer() -> ConfigurationWriter:
    return ConfigurationWriter(
        backup_root=DEFAULT_BACKUP_ROOT,
        audit_log=AuditLog(DEFAULT_AUDIT_PATH),
    )


def write_text(
    *,
    module_id: str,
    destination: Path,
    text: str,
    mode: int | None = None,
    ensure_trailing_newline: bool = True,
):
    result = configuration_writer().write(
        module_id=module_id,
        destination=destination,
        document=TextConfiguration(
            text,
            ensure_trailing_newline=(
                ensure_trailing_newline
            ),
        ),
    )

    if mode is not None:
        os.chmod(destination, mode)

    return result


def write_json(
    *,
    module_id: str,
    destination: Path,
    value: Any,
    mode: int | None = None,
):
    return write_text(
        module_id=module_id,
        destination=destination,
        text=(
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ),
        mode=mode,
        ensure_trailing_newline=False,
    )


def remove_file(
    *,
    module_id: str,
    destination: Path,
) -> bool:
    if not destination.exists():
        return False

    write_text(
        module_id=module_id,
        destination=destination,
        text="",
        ensure_trailing_newline=False,
    )
    destination.unlink()
    return True


def capture_external_text_files(
    paths: Iterable[Path],
) -> dict[Path, ExternalTextFileSnapshot]:
    """
    Capture files before invoking a trusted system utility that edits
    configuration internally, such as UFW.

    Pair this with record_external_text_changes() after the command.
    """
    snapshots: dict[Path, ExternalTextFileSnapshot] = {}

    for path in paths:
        path = Path(path)

        if path.is_file():
            file_stat = path.stat()
            snapshots[path] = ExternalTextFileSnapshot(
                path=path,
                existed=True,
                text=path.read_text(
                    encoding="utf-8",
                    errors="surrogateescape",
                ),
                mode=stat.S_IMODE(file_stat.st_mode),
            )
        else:
            snapshots[path] = ExternalTextFileSnapshot(
                path=path,
                existed=False,
                text="",
                mode=None,
            )

    return snapshots


def record_external_text_changes(
    *,
    module_id: str,
    before: dict[Path, ExternalTextFileSnapshot],
) -> int:
    """
    Record text-file changes made by a trusted external command.

    ConfigurationWriter normally observes both the old and new versions
    because LEC performs the write itself. For tools that edit their own
    files, this function captures the command's resulting files, briefly
    restores each pre-command version, then applies the resulting version
    through ConfigurationWriter. The final file contents remain exactly
    as produced by the external command, while Recovery receives a normal
    backup and audit entry.

    This is intended only for deterministic, trusted system tools.
    """
    changed = 0

    for path, old in before.items():
        new = _snapshot_external_text_file(path)

        if (
            old.existed == new.existed
            and old.text == new.text
        ):
            continue

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            _restore_external_snapshot(old)

            if new.existed:
                write_text(
                    module_id=module_id,
                    destination=path,
                    text=new.text,
                    mode=new.mode,
                    ensure_trailing_newline=False,
                )
            else:
                remove_file(
                    module_id=module_id,
                    destination=path,
                )
        except Exception:
            # Never leave the system utility's successful change reverted
            # merely because audit recording failed.
            _restore_external_snapshot(new)
            raise

        changed += 1

    return changed


def _snapshot_external_text_file(
    path: Path,
) -> ExternalTextFileSnapshot:
    if not path.is_file():
        return ExternalTextFileSnapshot(
            path=path,
            existed=False,
            text="",
            mode=None,
        )

    file_stat = path.stat()
    return ExternalTextFileSnapshot(
        path=path,
        existed=True,
        text=path.read_text(
            encoding="utf-8",
            errors="surrogateescape",
        ),
        mode=stat.S_IMODE(file_stat.st_mode),
    )


def _restore_external_snapshot(
    snapshot: ExternalTextFileSnapshot,
) -> None:
    path = snapshot.path

    if not snapshot.existed:
        path.unlink(missing_ok=True)
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        snapshot.text,
        encoding="utf-8",
        errors="surrogateescape",
    )

    if snapshot.mode is not None:
        os.chmod(path, snapshot.mode)
