from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from linuxeasyconfig.core.config.audit_log import AuditLog
from linuxeasyconfig.core.config.base import ConfigurationDocument
from linuxeasyconfig.core.config.write_models import (
    WritePreview,
    WriteResult,
)


class ConfigurationWriteError(RuntimeError):
    """Raised when a configuration change cannot be completed safely."""


class ConfigurationWriter:
    """Safely write, delete, back up, and audit configuration files."""

    def __init__(
        self,
        backup_root: Path,
        audit_log: AuditLog,
    ) -> None:
        self._backup_root = backup_root
        self._audit_log = audit_log

    def preview(
        self,
        *,
        module_id: str,
        destination: Path,
        document: ConfigurationDocument,
    ) -> WritePreview:
        rendered_text = document.render()
        proposed_bytes = rendered_text.encode("utf-8")
        proposed_sha256 = self._sha256_bytes(proposed_bytes)

        destination_exists = destination.is_file()
        current_sha256: str | None = None
        contents_changed = True

        if destination_exists:
            current_bytes = destination.read_bytes()
            current_sha256 = self._sha256_bytes(current_bytes)
            contents_changed = current_bytes != proposed_bytes

        return WritePreview(
            module_id=module_id,
            destination=destination,
            rendered_text=rendered_text,
            destination_exists=destination_exists,
            contents_changed=contents_changed,
            current_sha256=current_sha256,
            proposed_sha256=proposed_sha256,
        )

    def write(
        self,
        *,
        module_id: str,
        destination: Path,
        document: ConfigurationDocument,
    ) -> WriteResult:
        preview = self.preview(
            module_id=module_id,
            destination=destination,
            document=document,
        )

        timestamp = datetime.now().astimezone()
        timestamp_text = timestamp.isoformat(timespec="seconds")
        revision = self._audit_log.next_revision(module_id)

        backup_path: Path | None = None
        previous_sha256 = preview.current_sha256

        if preview.destination_exists:
            backup_path = self._create_verified_backup(
                module_id=module_id,
                destination=destination,
                revision=revision,
            )

        destination.parent.mkdir(parents=True, exist_ok=True)

        rendered_bytes = preview.rendered_text.encode("utf-8")
        temporary_path: Path | None = None

        try:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".lec-tmp",
                dir=destination.parent,
            )
            temporary_path = Path(temporary_name)

            with os.fdopen(file_descriptor, "wb") as temporary_file:
                temporary_file.write(rendered_bytes)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            if destination.exists():
                stat_result = destination.stat()
                os.chmod(temporary_path, stat_result.st_mode)

                try:
                    os.chown(
                        temporary_path,
                        stat_result.st_uid,
                        stat_result.st_gid,
                    )
                except PermissionError:
                    pass

            os.replace(temporary_path, destination)
            temporary_path = None
            self._fsync_directory(destination.parent)

        except Exception as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

            raise ConfigurationWriteError(
                f"Could not write {destination}: {exc}"
            ) from exc

        new_sha256 = self._sha256_file(destination)

        if new_sha256 != preview.proposed_sha256:
            raise ConfigurationWriteError(
                f"Verification failed after writing {destination}."
            )

        result = WriteResult(
            revision=revision,
            timestamp=timestamp_text,
            module_id=module_id,
            action=(
                "updated"
                if preview.destination_exists
                else "created"
            ),
            destination=destination,
            backup_path=backup_path,
            previous_sha256=previous_sha256,
            new_sha256=new_sha256,
            bytes_written=len(rendered_bytes),
        )

        self._append_audit_record(result)
        return result

    def delete(
        self,
        *,
        module_id: str,
        destination: Path,
    ) -> WriteResult:
        """
        Delete a file only after creating and verifying a backup.
        """

        if destination.is_symlink():
            raise ConfigurationWriteError(
                f"Refusing to delete symbolic link: {destination}"
            )

        if not destination.is_file():
            raise ConfigurationWriteError(
                f"Cannot delete missing file: {destination}"
            )

        timestamp = datetime.now().astimezone()
        timestamp_text = timestamp.isoformat(timespec="seconds")
        revision = self._audit_log.next_revision(module_id)
        previous_sha256 = self._sha256_file(destination)

        backup_path = self._create_verified_backup(
            module_id=module_id,
            destination=destination,
            revision=revision,
        )

        if not backup_path.is_file():
            raise ConfigurationWriteError(
                f"Verified backup is missing: {backup_path}"
            )

        if self._sha256_file(backup_path) != previous_sha256:
            raise ConfigurationWriteError(
                "Backup verification failed before deletion."
            )

        try:
            destination.unlink()
            self._fsync_directory(destination.parent)
        except Exception as exc:
            raise ConfigurationWriteError(
                f"Could not delete {destination}: {exc}"
            ) from exc

        if destination.exists():
            raise ConfigurationWriteError(
                f"Deletion verification failed for {destination}."
            )

        result = WriteResult(
            revision=revision,
            timestamp=timestamp_text,
            module_id=module_id,
            action="deleted",
            destination=destination,
            backup_path=backup_path,
            previous_sha256=previous_sha256,
            new_sha256=None,
            bytes_written=0,
        )

        self._append_audit_record(result)
        return result

    def _append_audit_record(self, result: WriteResult) -> None:
        try:
            self._audit_log.append(result)
        except Exception as exc:
            raise ConfigurationWriteError(
                "The filesystem change completed, but the audit "
                f"record could not be saved: {exc}"
            ) from exc

    def _create_verified_backup(
        self,
        *,
        module_id: str,
        destination: Path,
        revision: int,
    ) -> Path:
        if destination.is_symlink():
            raise ConfigurationWriteError(
                f"Refusing to back up symbolic link: {destination}"
            )

        if not destination.is_file():
            raise ConfigurationWriteError(
                f"Cannot back up missing file: {destination}"
            )

        original_size = destination.stat().st_size
        original_sha256 = self._sha256_file(destination)
        relative_destination = self._safe_relative_path(destination)

        backup_path = (
            self._backup_root
            / self._safe_module_id(module_id)
            / f"rev{revision:06d}"
            / relative_destination
        )

        if backup_path.exists():
            raise ConfigurationWriteError(
                f"Backup revision already exists: {backup_path}"
            )

        backup_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(destination, backup_path)
            self._fsync_file(backup_path)
            self._fsync_directory(backup_path.parent)
        except Exception as exc:
            raise ConfigurationWriteError(
                f"Could not create backup for {destination}: {exc}"
            ) from exc

        if not backup_path.is_file():
            raise ConfigurationWriteError(
                f"Backup was not created: {backup_path}"
            )

        backup_size = backup_path.stat().st_size
        backup_sha256 = self._sha256_file(backup_path)

        if backup_size != original_size:
            raise ConfigurationWriteError(
                f"Backup size verification failed for {destination}."
            )

        if backup_sha256 != original_sha256:
            raise ConfigurationWriteError(
                f"Backup hash verification failed for {destination}."
            )

        return backup_path

    @staticmethod
    def _sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)

        return digest.hexdigest()

    @staticmethod
    def _fsync_file(path: Path) -> None:
        with path.open("rb") as source:
            os.fsync(source.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        directory_descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )

        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

    @staticmethod
    def _safe_module_id(module_id: str) -> str:
        cleaned = "".join(
            character
            if character.isalnum() or character in "._-"
            else "_"
            for character in module_id
        )

        return cleaned or "unknown-module"

    @staticmethod
    def _safe_relative_path(destination: Path) -> Path:
        absolute = destination.resolve()

        if absolute.is_absolute():
            return Path(*absolute.parts[1:])

        return absolute
