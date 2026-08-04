from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from linuxeasyconfig.core.config.managed import write_text

from .collector import write_snapshot


MODULE_ID = "org.linuxeasyconfig.port_usage"
SERVICE_PATH = Path(
    "/etc/systemd/system/lec-port-usage.service"
)
TIMER_PATH = Path(
    "/etc/systemd/system/lec-port-usage.timer"
)


def refresh_snapshot() -> str:
    value = write_snapshot()
    count = len(value.get("rows", []))
    return f"Port usage refreshed. {count} listening socket(s) found."


def install_monitor() -> str:
    interpreter = Path(sys.executable).resolve()
    package_root = Path(__file__).resolve().parents[3]

    write_text(
        module_id=MODULE_ID,
        destination=SERVICE_PATH,
        text=(
            "[Unit]\n"
            "Description=Linux Easy Config port usage snapshot\n"
            "After=network.target docker.service caddy.service\n\n"
            "[Service]\n"
            "Type=oneshot\n"
            f"Environment=PYTHONPATH={package_root}\n"
            "Environment=PYTHONDONTWRITEBYTECODE=1\n"
            f"ExecStart={interpreter} -B -m "
            "linuxeasyconfig.modules.port_usage.snapshot_runner\n"
        ),
        mode=0o644,
    )

    write_text(
        module_id=MODULE_ID,
        destination=TIMER_PATH,
        text=(
            "[Unit]\n"
            "Description=Refresh Linux Easy Config port usage snapshot\n\n"
            "[Timer]\n"
            "OnBootSec=30s\n"
            "OnUnitActiveSec=5min\n"
            "AccuracySec=15s\n"
            "Persistent=true\n\n"
            "[Install]\n"
            "WantedBy=timers.target\n"
        ),
        mode=0o644,
    )

    _run(["systemctl", "daemon-reload"])
    _run(
        [
            "systemctl",
            "enable",
            "--now",
            "lec-port-usage.timer",
        ]
    )
    write_snapshot()
    return "Port Usage monitor was installed and started."


def _run(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"{' '.join(command)} failed."
        )
