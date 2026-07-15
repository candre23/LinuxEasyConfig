from __future__ import annotations

from typing import Any


class PrivilegedArgumentError(RuntimeError):
    """Raised when privileged task arguments are invalid."""


def required_string(
    arguments: dict[str, Any],
    name: str,
) -> str:
    value = arguments.get(name)

    if not isinstance(value, str) or not value.strip():
        raise PrivilegedArgumentError(
            f"Missing or invalid argument: {name}"
        )

    return value.strip()


def optional_string(
    arguments: dict[str, Any],
    name: str,
    *,
    strip: bool = True,
) -> str:
    value = arguments.get(name, "")

    if not isinstance(value, str):
        raise PrivilegedArgumentError(
            f"Invalid argument: {name}"
        )

    return value.strip() if strip else value


def optional_bool(
    arguments: dict[str, Any],
    name: str,
    *,
    default: bool,
) -> bool:
    value = arguments.get(name, default)

    if not isinstance(value, bool):
        raise PrivilegedArgumentError(
            f"Invalid argument: {name}"
        )

    return value
