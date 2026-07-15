from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import (
    optional_bool,
    optional_string,
    required_string,
)

from .installer import (
    apply_folder_access,
    create_group,
    create_service_account,
    delete_group,
    remove_folder_access,
    rename_group,
    set_supplementary_groups,
)


def _create_service_account(
    arguments: dict[str, Any],
) -> str:
    return create_service_account(
        username=required_string(
            arguments,
            "username",
        ),
        description=optional_string(
            arguments,
            "description",
        ),
        create_home=optional_bool(
            arguments,
            "create_home",
            default=False,
        ),
        home_directory=optional_string(
            arguments,
            "home_directory",
        ),
    )


def _set_groups(
    arguments: dict[str, Any],
) -> str:
    raw_groups = arguments.get("groups", [])

    if not isinstance(raw_groups, list):
        raise ValueError(
            "The supplementary groups value is invalid."
        )

    groups: list[str] = []

    for value in raw_groups:
        if not isinstance(value, str):
            raise ValueError(
                "A supplementary group name is invalid."
            )
        groups.append(value)

    return set_supplementary_groups(
        username=required_string(
            arguments,
            "username",
        ),
        groups=groups,
    )


def _create_group(arguments: dict[str, Any]) -> str:
    return create_group(
        name=required_string(arguments, "name"),
        system_group=optional_bool(arguments, "system_group", default=True),
    )


def _rename_group(arguments: dict[str, Any]) -> str:
    return rename_group(
        old_name=required_string(arguments, "old_name"),
        new_name=required_string(arguments, "new_name"),
    )


def _delete_group(arguments: dict[str, Any]) -> str:
    return delete_group(name=required_string(arguments, "name"))


def _apply_folder_access(
    arguments: dict[str, Any],
) -> str:
    return apply_folder_access(
        username=required_string(
            arguments,
            "username",
        ),
        path=required_string(
            arguments,
            "path",
        ),
        access_level=required_string(
            arguments,
            "access_level",
        ),
        recursive=optional_bool(
            arguments,
            "recursive",
            default=False,
        ),
        inherit=optional_bool(
            arguments,
            "inherit",
            default=True,
        ),
        traverse_parents=optional_bool(
            arguments,
            "traverse_parents",
            default=True,
        ),
    )


def _remove_folder_access(
    arguments: dict[str, Any],
) -> str:
    return remove_folder_access(
        username=required_string(
            arguments,
            "username",
        ),
        path=required_string(
            arguments,
            "path",
        ),
        recursive=optional_bool(
            arguments,
            "recursive",
            default=False,
        ),
        remove_default=optional_bool(
            arguments,
            "remove_default",
            default=True,
        ),
    )


PRIVILEGED_TASKS = {
    "user_permissions.create_service_account": (
        _create_service_account
    ),
    "user_permissions.set_groups": _set_groups,
    "user_permissions.create_group": _create_group,
    "user_permissions.rename_group": _rename_group,
    "user_permissions.delete_group": _delete_group,
    "user_permissions.apply_folder_access": (
        _apply_folder_access
    ),
    "user_permissions.remove_folder_access": (
        _remove_folder_access
    ),
}
