from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/port-usage/status.json"
)


class PortUsageRepository:
    def snapshot(self) -> dict[str, Any]:
        if not SNAPSHOT_PATH.is_file():
            return {}

        try:
            value = json.loads(
                SNAPSHOT_PATH.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )
        except (OSError, json.JSONDecodeError):
            return {}

        return value if isinstance(value, dict) else {}

    def monitor_status(self) -> str:
        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "lec-port-usage.timer",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        return (
            "Installed and running"
            if result.returncode == 0
            else "Not installed or not running"
        )
