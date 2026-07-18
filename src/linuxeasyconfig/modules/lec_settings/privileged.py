from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    optional_string,
    required_string,
)

from .installer import preview_revision_backup, restore_revision


def _preview(
    arguments: dict[str, Any],
) -> str:
    revision_value = arguments.get("revision")

    try:
        revision = int(revision_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "The recovery revision is invalid."
        ) from exc

    return preview_revision_backup(
        source_module_id=required_string(
            arguments,
            "module_id",
        ),
        revision=revision,
        destination=required_string(
            arguments,
            "destination",
        ),
        backup_path=required_string(
            arguments,
            "backup_path",
        ),
    )


def _restore(
    arguments: dict[str, Any],
) -> str:
    revision_value = arguments.get("revision")

    try:
        revision = int(revision_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "The recovery revision is invalid."
        ) from exc

    return restore_revision(
        source_module_id=required_string(
            arguments,
            "module_id",
        ),
        revision=revision,
        destination=required_string(
            arguments,
            "destination",
        ),
        backup_path=optional_string(
            arguments,
            "backup_path",
        ),
        restore_mode=required_string(
            arguments,
            "restore_mode",
        ),
    )


PRIVILEGED_TASKS = {
    "lec_settings.preview": _preview,
    "lec_settings.restore": _restore,
}
