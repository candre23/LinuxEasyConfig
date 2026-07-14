from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from linuxeasyconfig.core.config.write_models import WriteResult


class AuditLog:
    """Append-only JSON Lines audit log for LEC configuration changes."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def next_revision(self, module_id: str) -> int:
        """Return the next revision number for one module."""

        highest_revision = 0

        for record in self.read_all():
            if record.get("module_id") != module_id:
                continue

            revision = record.get("revision")

            if isinstance(revision, int):
                highest_revision = max(highest_revision, revision)

        return highest_revision + 1

    def append(self, result: WriteResult) -> None:
        """Append one completed write record and flush it to disk."""

        record = self._serialize_result(result)

        self._path.parent.mkdir(parents=True, exist_ok=True)

        with self._path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            audit_file.write("\n")
            audit_file.flush()
            os.fsync(audit_file.fileno())

    def read_all(self) -> list[dict[str, Any]]:
        """Read every valid audit record currently stored."""

        if not self._path.exists():
            return []

        records: list[dict[str, Any]] = []

        with self._path.open("r", encoding="utf-8") as audit_file:
            for line_number, line in enumerate(audit_file, start=1):
                text = line.strip()

                if not text:
                    continue

                try:
                    record = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid audit-log entry on line "
                        f"{line_number}: {exc}"
                    ) from exc

                if not isinstance(record, dict):
                    raise ValueError(
                        f"Audit-log entry on line {line_number} "
                        "is not a JSON object."
                    )

                records.append(record)

        return records

    @staticmethod
    def _serialize_result(result: WriteResult) -> dict[str, Any]:
        record = asdict(result)

        record["destination"] = str(result.destination)
        record["backup_path"] = (
            str(result.backup_path)
            if result.backup_path is not None
            else None
        )

        return record
