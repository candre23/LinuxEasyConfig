from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


BACKUP_ROOT = Path("/var/lib/linuxeasyconfig/backups")
AUDIT_PATH = Path("/var/lib/linuxeasyconfig/audit.jsonl")


@dataclass(frozen=True)
class RecoveryRevision:
    key: str
    revision: int
    module_id: str
    timestamp: str
    operation: str
    destination: Path
    backup_path: Path | None
    restore_mode: str
    old_sha256: str
    new_sha256: str

    @property
    def backup_available(self) -> bool:
        return (
            self.restore_mode == "file"
            and self.backup_path is not None
            and self.backup_path.is_file()
        )

    @property
    def display_timestamp(self) -> str:
        text = self.timestamp.strip()

        if not text:
            return "Unknown time"

        try:
            normalized = text.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed.astimezone().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            return text


class RecoveryRepository:
    """Read LEC's append-only audit log and versioned backups."""

    def revisions(self) -> list[RecoveryRevision]:
        records = self._read_audit_records()
        revisions: list[RecoveryRevision] = []

        for index, record in enumerate(records):
            revision = _integer(
                record,
                "revision",
                "revision_number",
                "rev",
                default=index + 1,
            )
            module_id = _text(
                record,
                "module_id",
                "module",
                default="unknown",
            )
            timestamp = _text(
                record,
                "timestamp",
                "created_at",
                "time",
                default="",
            )
            operation = _text(
                record,
                "operation",
                "action",
                "event",
                default="write",
            ).lower()
            destination_text = _text(
                record,
                "destination",
                "path",
                "target",
                "file_path",
                default="",
            )

            if not destination_text:
                continue

            destination = Path(destination_text)

            if not destination.is_absolute():
                continue

            backup_path = self._resolve_backup_path(
                record=record,
                module_id=module_id,
                revision=revision,
                destination=destination,
            )

            old_exists = _boolean_or_none(
                record,
                "old_exists",
                "previously_existed",
                "destination_existed",
            )

            if old_exists is False:
                restore_mode = "delete"
            elif backup_path is not None and backup_path.is_file():
                restore_mode = "file"
            elif operation in {"create", "created"}:
                restore_mode = "delete"
            else:
                restore_mode = "unavailable"

            key = (
                f"{module_id}\0{revision}\0"
                f"{destination}\0{index}"
            )

            revisions.append(
                RecoveryRevision(
                    key=key,
                    revision=revision,
                    module_id=module_id,
                    timestamp=timestamp,
                    operation=operation,
                    destination=destination,
                    backup_path=backup_path,
                    restore_mode=restore_mode,
                    old_sha256=_text(
                        record,
                        "old_sha256",
                        "previous_sha256",
                        default="",
                    ),
                    new_sha256=_text(
                        record,
                        "new_sha256",
                        "sha256",
                        default="",
                    ),
                )
            )

        revisions.sort(
            key=lambda item: (
                _timestamp_sort_key(item.timestamp),
                item.revision,
            ),
            reverse=True,
        )
        return revisions

    def later_revisions_for_file(
        self,
        selected: RecoveryRevision,
    ) -> list[RecoveryRevision]:
        all_revisions = self.revisions()
        same_file = [
            revision
            for revision in all_revisions
            if revision.destination == selected.destination
        ]

        try:
            selected_index = next(
                index
                for index, revision in enumerate(same_file)
                if revision.key == selected.key
            )
        except StopIteration:
            return []

        return same_file[:selected_index]

    def preview_text(
        self,
        revision: RecoveryRevision,
    ) -> str:
        header = [
            f"Module: {revision.module_id}",
            f"Revision: {revision.revision}",
            f"Time: {revision.display_timestamp}",
            f"Operation: {revision.operation}",
            f"Destination: {revision.destination}",
            "",
        ]

        if revision.restore_mode == "delete":
            return "\n".join(
                header
                + [
                    "This revision represents the state before the file "
                    "was created.",
                    "",
                    "Reverting to it will remove the current file.",
                ]
            )

        if not revision.backup_available:
            return "\n".join(
                header
                + [
                    "The backup for this revision is not available.",
                    "",
                    "This revision cannot be restored.",
                ]
            )

        assert revision.backup_path is not None

        try:
            raw = revision.backup_path.read_bytes()
        except PermissionError:
            return "\n".join(
                header
                + [
                    "The backup exists and can be restored.",
                    "",
                    "Its contents are protected because backups may "
                    "contain passwords, API tokens, or other sensitive "
                    "configuration.",
                    "",
                    "Select Load Protected Preview to inspect it with "
                    "administrator authorization.",
                ]
            )
        except OSError as exc:
            return "\n".join(
                header
                + [
                    "The backup could not be read:",
                    str(exc),
                ]
            )

        if b"\0" in raw:
            return "\n".join(
                header
                + [
                    "Binary backup",
                    f"Size: {len(raw):,} bytes",
                    "",
                    "Binary files are not displayed in the preview.",
                ]
            )

        text = raw.decode(
            "utf-8",
            errors="replace",
        )

        return "\n".join(
            header
            + [
                "Backup contents",
                "------------------------------------------------------------",
                text,
            ]
        )

    def _read_audit_records(
        self,
    ) -> list[dict[str, Any]]:
        try:
            lines = AUDIT_PATH.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        except OSError:
            return []

        records: list[dict[str, Any]] = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            try:
                value = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            if isinstance(value, dict):
                records.append(value)

        return records

    def _resolve_backup_path(
        self,
        *,
        record: dict[str, Any],
        module_id: str,
        revision: int,
        destination: Path,
    ) -> Path | None:
        explicit = _text(
            record,
            "backup_path",
            "backup",
            "backup_file",
            default="",
        )

        if explicit:
            candidate = Path(explicit)

            if candidate.is_absolute():
                return candidate

        relative_destination = Path(
            str(destination).lstrip(os.sep)
        )

        candidates = (
            BACKUP_ROOT
            / module_id
            / f"rev{revision:06d}"
            / relative_destination,
            BACKUP_ROOT
            / module_id
            / f"rev{revision}"
            / relative_destination,
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate

        revision_root = (
            BACKUP_ROOT
            / module_id
            / f"rev{revision:06d}"
        )

        if revision_root.is_dir():
            matches = [
                path
                for path in revision_root.rglob(
                    destination.name
                )
                if path.is_file()
            ]

            if len(matches) == 1:
                return matches[0]

        return candidates[0]


def _text(
    record: dict[str, Any],
    *names: str,
    default: str,
) -> str:
    for name in names:
        value = record.get(name)

        if value is not None:
            return str(value)

    return default


def _integer(
    record: dict[str, Any],
    *names: str,
    default: int,
) -> int:
    for name in names:
        value = record.get(name)

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return default


def _boolean_or_none(
    record: dict[str, Any],
    *names: str,
) -> bool | None:
    for name in names:
        value = record.get(name)

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            lowered = value.strip().lower()

            if lowered in {"true", "yes", "1"}:
                return True

            if lowered in {"false", "no", "0"}:
                return False

    return None


def _timestamp_sort_key(value: str) -> str:
    return value or ""
