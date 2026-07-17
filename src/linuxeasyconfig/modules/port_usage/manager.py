from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .collector import write_snapshot


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

    SERVICE_PATH.write_text(
        "[Unit]\n"
        "Description=Linux Easy Config port usage snapshot\n"
        "After=network.target docker.service caddy.service\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"Environment=PYTHONPATH={package_root}\n"
        f"ExecStart={interpreter} -m "
        "linuxeasyconfig.modules.port_usage.snapshot_runner\n",
        encoding="utf-8",
    )
    SERVICE_PATH.chmod(0o644)

    TIMER_PATH.write_text(
        "[Unit]\n"
        "Description=Refresh Linux Easy Config port usage snapshot\n\n"
        "[Timer]\n"
        "OnBootSec=30s\n"
        "OnUnitActiveSec=5min\n"
        "AccuracySec=15s\n"
        "Persistent=true\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n",
        encoding="utf-8",
    )
    TIMER_PATH.chmod(0o644)

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
