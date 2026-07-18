from __future__ import annotations

import re
import subprocess
from typing import Any


_UNIT_PATTERN = re.compile(
    r"^[A-Za-z0-9_.@:-]+\.(?:service|timer|socket|mount|path|target)$"
)


def _reset_failed(arguments: dict[str, Any]) -> str:
    raw_units = arguments.get("units", [])

    if not isinstance(raw_units, list):
        raise ValueError("The failed-unit list is invalid.")

    units: list[str] = []

    for value in raw_units:
        unit = str(value).strip()

        if not _UNIT_PATTERN.fullmatch(unit):
            raise ValueError(
                f"{unit!r} is not a valid systemd unit name."
            )

        units.append(unit)

    if not units:
        raise ValueError(
            "Select at least one failed unit."
        )

    result = subprocess.run(
        ["systemctl", "reset-failed", *units],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "systemctl reset-failed failed."
        )

    return (
        f"Cleared the old failed marker for "
        f"{len(units)} unit"
        f"{'s' if len(units) != 1 else ''}."
    )


PRIVILEGED_TASKS = {
    "system_logs.reset_failed": _reset_failed,
}
