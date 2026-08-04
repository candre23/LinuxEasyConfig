from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    optional_string,
    required_string,
)

from .installer import preview_revision_backup, restore_revision
from .uninstall import remove_component


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


def _remove_component(
    arguments: dict[str, Any],
) -> str:
    return remove_component(
        required_string(arguments, "component_id")
    )


PRIVILEGED_TASKS = {
    "lec_settings.preview": _preview,
    "lec_settings.restore": _restore,
    "lec_settings.remove_component": _remove_component,
}
