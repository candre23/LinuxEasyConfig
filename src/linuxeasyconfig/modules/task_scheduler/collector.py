from __future__ import annotations

import datetime as dt
import json
import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .storage import STATUS_PATH, load_public_tasks, save_status


CRON_SYSTEM_FILES = (
    Path("/etc/crontab"),
)
CRON_DIRECTORIES = (
    Path("/etc/cron.d"),
)


def collect_status() -> dict[str, Any]:
    lec_tasks = load_public_tasks()
    timer_rows = _systemd_timers()
    cron_rows = _cron_entries()
    lec_runtime = _lec_runtime(lec_tasks)

    value = {
        "generated_at": dt.datetime.now(
            dt.timezone.utc
        ).isoformat(),
        "lec_tasks": lec_runtime,
        "systemd_timers": timer_rows,
        "cron_entries": cron_rows,
        "summary": {
            "lec_tasks": len(lec_runtime),
            "enabled_lec_tasks": sum(
                1
                for item in lec_runtime
                if item.get("enabled")
            ),
            "systemd_timers": len(timer_rows),
            "cron_entries": len(cron_rows),
        },
    }
    save_status(value)
    return value


def _systemd_timers() -> list[dict[str, Any]]:
    if shutil.which("systemctl") is None:
        return []

    result = subprocess.run(
        [
            "systemctl",
            "list-timers",
            "--all",
            "--no-legend",
            "--no-pager",
            "--plain",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        return []

    rows: list[dict[str, Any]] = []

    for line in result.stdout.splitlines():
        text = line.strip()

        if not text:
            continue

        parts = re.split(r"\s{2,}", text)

        if len(parts) < 6:
            continue

        next_run, left, last_run, passed, unit, activates = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            parts[4],
            parts[5],
        )
        rows.append(
            {
                "source": "systemd",
                "name": unit,
                "schedule": next_run,
                "next_run": next_run,
                "last_run": last_run,
                "status": _unit_state(unit),
                "activates": activates,
                "detail": (
                    f"Next: {next_run}; Last: {last_run}; "
                    f"Activates: {activates}"
                ),
                "editable": unit.startswith("lec-task-"),
            }
        )

    return rows


def _unit_state(unit: str) -> str:
    enabled = subprocess.run(
        [
            "systemctl",
            "is-enabled",
            unit,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    ).stdout.strip()

    active = subprocess.run(
        [
            "systemctl",
            "is-active",
            unit,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    ).stdout.strip()

    if active == "active":
        return "Active"
    if enabled:
        return enabled.capitalize()
    return "Unknown"


def _cron_entries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for path in CRON_SYSTEM_FILES:
        rows.extend(
            _parse_cron_file(
                path,
                source="system cron",
                includes_user=True,
            )
        )

    for directory in CRON_DIRECTORIES:
        if not directory.is_dir():
            continue

        for path in sorted(directory.iterdir()):
            if path.is_file():
                rows.extend(
                    _parse_cron_file(
                        path,
                        source="cron.d",
                        includes_user=True,
                    )
                )

    rows.extend(_user_crontabs())
    return rows


def _parse_cron_file(
    path: Path,
    *,
    source: str,
    includes_user: bool,
) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return []

    rows: list[dict[str, Any]] = []

    for number, raw in enumerate(lines, start=1):
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
            or "=" in line.split()[0]
        ):
            continue

        if line.startswith("@"):
            parts = line.split(None, 2 if includes_user else 1)
            if len(parts) < (3 if includes_user else 2):
                continue
            schedule = parts[0]
            user = parts[1] if includes_user else ""
            command = parts[2] if includes_user else parts[1]
        else:
            parts = line.split()

            minimum = 7 if includes_user else 6
            if len(parts) < minimum:
                continue

            schedule = " ".join(parts[:5])
            user = parts[5] if includes_user else ""
            command = " ".join(
                parts[6:] if includes_user else parts[5:]
            )

        rows.append(
            {
                "source": source,
                "name": path.name,
                "schedule": schedule,
                "next_run": "",
                "last_run": "",
                "status": "Configured",
                "activates": command,
                "user": user,
                "detail": f"{path}:{number}",
                "editable": False,
            }
        )

    return rows


def _user_crontabs() -> list[dict[str, Any]]:
    if shutil.which("crontab") is None:
        return []

    rows: list[dict[str, Any]] = []

    for account in pwd.getpwall():
        if account.pw_uid < 1000 and account.pw_name != "root":
            continue

        result = subprocess.run(
            [
                "crontab",
                "-l",
                "-u",
                account.pw_name,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if result.returncode != 0:
            continue

        temporary = Path(
            f"/tmp/lec-crontab-{os.getpid()}-{account.pw_name}"
        )

        try:
            temporary.write_text(
                result.stdout,
                encoding="utf-8",
            )
            entries = _parse_cron_file(
                temporary,
                source="user cron",
                includes_user=False,
            )
        finally:
            try:
                temporary.unlink()
            except OSError:
                pass

        for item in entries:
            item["name"] = account.pw_name
            item["user"] = account.pw_name
            item["detail"] = (
                f"User crontab: {account.pw_name}"
            )
            rows.append(item)

    return rows


def _lec_runtime(
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for task in tasks:
        task_id = str(task.get("id", ""))
        timer = f"lec-task-{task_id}.timer"
        service = f"lec-task-{task_id}.service"

        next_run = _show_property(
            timer,
            "NextElapseUSecRealtime",
        )
        last_result = _show_property(
            service,
            "Result",
        )
        last_exit = _show_property(
            service,
            "ExecMainStatus",
        )
        active = _unit_state(timer)

        item = dict(task)
        item.update(
            {
                "timer_unit": timer,
                "service_unit": service,
                "next_run": next_run or "Not scheduled",
                "last_result": last_result or "Never run",
                "last_exit_code": last_exit,
                "runtime_status": active,
            }
        )
        rows.append(item)

    return rows


def _show_property(
    unit: str,
    property_name: str,
) -> str:
    result = subprocess.run(
        [
            "systemctl",
            "show",
            unit,
            f"--property={property_name}",
            "--value",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    return (
        result.stdout.strip()
        if result.returncode == 0
        else ""
    )
