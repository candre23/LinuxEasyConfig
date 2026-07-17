from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import uuid
from pathlib import Path

from .collector import collect_status
from .storage import ScheduledTask, load_tasks, save_tasks


UNIT_DIR = Path("/etc/systemd/system")
SCRIPT_DIR = Path(
    "/etc/linuxeasyconfig/task_scheduler/scripts"
)
MONITOR_SERVICE = UNIT_DIR / "lec-task-scheduler-scan.service"
MONITOR_TIMER = UNIT_DIR / "lec-task-scheduler-scan.timer"

_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
_USER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*[$]?$")


def save_task(
    *,
    original_id: str,
    name: str,
    description: str,
    command: str,
    working_directory: str,
    run_as_user: str,
    schedule_type: str,
    schedule_value: str,
    enabled: bool,
) -> str:
    name = name.strip()
    command = command.strip()
    run_as_user = run_as_user.strip() or "root"
    working_directory = working_directory.strip() or "/"
    schedule_type = schedule_type.strip()
    schedule_value = schedule_value.strip()

    if not name:
        raise ValueError("Task name is required.")
    if not command:
        raise ValueError("Command is required.")
    if not _USER_PATTERN.fullmatch(run_as_user):
        raise ValueError("Run-as user is invalid.")
    if not Path(working_directory).is_absolute():
        raise ValueError(
            "Working directory must be an absolute path."
        )

    on_calendar, on_boot = _schedule_settings(
        schedule_type,
        schedule_value,
    )

    tasks = load_tasks()
    existing = next(
        (
            item
            for item in tasks
            if item.id == original_id
        ),
        None,
    )
    task_id = (
        existing.id
        if existing is not None
        else uuid.uuid4().hex
    )

    task = ScheduledTask(
        id=task_id,
        name=name,
        description=description.strip(),
        command=command,
        working_directory=working_directory,
        run_as_user=run_as_user,
        schedule_type=schedule_type,
        schedule_value=schedule_value,
        enabled=enabled,
    )

    SCRIPT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    SCRIPT_DIR.chmod(0o700)
    script = SCRIPT_DIR / f"{task_id}.sh"
    script.write_text(
        "#!/bin/bash\n"
        "set -o pipefail\n"
        f"cd {shlex.quote(working_directory)}\n"
        f"{command}\n",
        encoding="utf-8",
    )
    script.chmod(0o700)

    service_path = UNIT_DIR / f"lec-task-{task_id}.service"
    timer_path = UNIT_DIR / f"lec-task-{task_id}.timer"

    service_path.write_text(
        "[Unit]\n"
        f"Description=LEC scheduled task: {name}\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"User={run_as_user}\n"
        f"WorkingDirectory={working_directory}\n"
        f"ExecStart=/bin/bash {script}\n",
        encoding="utf-8",
    )
    service_path.chmod(0o644)

    timer_lines = [
        "[Unit]",
        f"Description=Schedule for LEC task: {name}",
        "",
        "[Timer]",
    ]

    if on_calendar:
        timer_lines.append(f"OnCalendar={on_calendar}")
    if on_boot:
        timer_lines.append(f"OnBootSec={on_boot}")

    timer_lines.extend(
        [
            "Persistent=true",
            "AccuracySec=1min",
            f"Unit=lec-task-{task_id}.service",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )

    timer_path.write_text(
        "\n".join(timer_lines),
        encoding="utf-8",
    )
    timer_path.chmod(0o644)

    tasks = [
        item
        for item in tasks
        if item.id != task_id
    ]
    tasks.append(task)
    save_tasks(tasks)

    _run(["systemctl", "daemon-reload"])

    if enabled:
        _run(
            [
                "systemctl",
                "enable",
                "--now",
                timer_path.name,
            ]
        )
    else:
        subprocess.run(
            [
                "systemctl",
                "disable",
                "--now",
                timer_path.name,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    collect_status()
    return f"Scheduled task {name} was saved."


def delete_task(
    *,
    task_id: str,
) -> str:
    _validate_id(task_id)
    tasks = load_tasks()
    task = next(
        (
            item
            for item in tasks
            if item.id == task_id
        ),
        None,
    )

    if task is None:
        raise ValueError("Scheduled task was not found.")

    timer = f"lec-task-{task_id}.timer"
    subprocess.run(
        ["systemctl", "disable", "--now", timer],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    for path in (
        UNIT_DIR / timer,
        UNIT_DIR / f"lec-task-{task_id}.service",
        SCRIPT_DIR / f"{task_id}.sh",
    ):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    save_tasks(
        [
            item
            for item in tasks
            if item.id != task_id
        ]
    )
    _run(["systemctl", "daemon-reload"])
    collect_status()
    return f"Scheduled task {task.name} was deleted."


def set_task_enabled(
    *,
    task_id: str,
    enabled: bool,
) -> str:
    _validate_id(task_id)
    tasks = load_tasks()
    task = next(
        (
            item
            for item in tasks
            if item.id == task_id
        ),
        None,
    )

    if task is None:
        raise ValueError("Scheduled task was not found.")

    timer = f"lec-task-{task_id}.timer"

    if enabled:
        _run(["systemctl", "enable", "--now", timer])
    else:
        _run(["systemctl", "disable", "--now", timer])

    task.enabled = enabled
    save_tasks(tasks)
    collect_status()
    return (
        f"Scheduled task {task.name} was "
        + ("enabled." if enabled else "disabled.")
    )


def run_task_now(
    *,
    task_id: str,
) -> str:
    _validate_id(task_id)
    service = f"lec-task-{task_id}.service"
    _run(["systemctl", "start", service])
    collect_status()
    return "Scheduled task completed."


def refresh_status() -> str:
    value = collect_status()
    summary = value.get("summary", {})
    return (
        "Scheduled tasks refreshed. "
        f"{summary.get('lec_tasks', 0)} LEC task(s), "
        f"{summary.get('systemd_timers', 0)} systemd timer(s), and "
        f"{summary.get('cron_entries', 0)} cron entry/entries found."
    )


def install_monitor() -> str:
    interpreter = Path(sys.executable).resolve()
    package_root = Path(__file__).resolve().parents[3]

    MONITOR_SERVICE.write_text(
        "[Unit]\n"
        "Description=Linux Easy Config scheduled-task inventory\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"Environment=PYTHONPATH={package_root}\n"
        f"ExecStart={interpreter} -m "
        "linuxeasyconfig.modules.task_scheduler.snapshot_runner\n",
        encoding="utf-8",
    )
    MONITOR_SERVICE.chmod(0o644)

    MONITOR_TIMER.write_text(
        "[Unit]\n"
        "Description=Refresh Linux Easy Config scheduled-task inventory\n\n"
        "[Timer]\n"
        "OnBootSec=1min\n"
        "OnUnitActiveSec=5min\n"
        "AccuracySec=30s\n"
        "Persistent=true\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n",
        encoding="utf-8",
    )
    MONITOR_TIMER.chmod(0o644)

    _run(["systemctl", "daemon-reload"])
    _run(
        [
            "systemctl",
            "enable",
            "--now",
            MONITOR_TIMER.name,
        ]
    )
    collect_status()
    return "Task Scheduler inventory monitor was installed."


def _schedule_settings(
    schedule_type: str,
    schedule_value: str,
) -> tuple[str, str]:
    if schedule_type == "minutes":
        try:
            minutes = int(schedule_value)
        except ValueError as exc:
            raise ValueError(
                "Minutes must be a whole number."
            ) from exc
        if minutes < 1:
            raise ValueError(
                "Minutes must be at least 1."
            )
        return f"*:0/{minutes}", ""

    if schedule_type == "hourly":
        return "hourly", ""
    if schedule_type == "daily":
        value = schedule_value or "03:00"
        return f"*-*-* {value}:00", ""
    if schedule_type == "weekly":
        value = schedule_value or "Mon 03:00"
        return f"{value}:00", ""
    if schedule_type == "monthly":
        value = schedule_value or "1 03:00"
        day, _, clock = value.partition(" ")
        if not day.isdigit():
            raise ValueError(
                "Monthly schedule must look like: 1 03:00"
            )
        return f"*-*-{int(day):02d} {clock or '03:00'}:00", ""
    if schedule_type == "boot":
        return "", schedule_value or "2min"
    if schedule_type == "calendar":
        if not schedule_value:
            raise ValueError(
                "A systemd calendar expression is required."
            )
        return schedule_value, ""

    raise ValueError("Schedule type is not supported.")


def _validate_id(task_id: str) -> None:
    if not _ID_PATTERN.fullmatch(task_id):
        raise ValueError("Scheduled task identifier is invalid.")


def _run(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"{' '.join(command)} failed."
        )
