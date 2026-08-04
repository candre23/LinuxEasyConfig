from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LECComponent:
    component_id: str
    title: str
    description: str
    installed: bool
    detail: str


_COMPONENTS: dict[str, dict[str, object]] = {
    "dynamic_dns": {
        "title": "Dynamic DNS automatic updater",
        "description": (
            "Removes the LEC Dynamic DNS service and five-minute timer. "
            "Provider accounts and hostname settings are retained."
        ),
        "units": ("lec-dynamic-dns.timer", "lec-dynamic-dns.service"),
        "paths": (
            Path("/etc/systemd/system/lec-dynamic-dns.timer"),
            Path("/etc/systemd/system/lec-dynamic-dns.service"),
        ),
    },
    "port_usage": {
        "title": "Port Usage background collector",
        "description": (
            "Removes the LEC Port Usage service and timer. The Port Usage "
            "page can still refresh information while LEC is open."
        ),
        "units": ("lec-port-usage.timer", "lec-port-usage.service"),
        "paths": (
            Path("/etc/systemd/system/lec-port-usage.timer"),
            Path("/etc/systemd/system/lec-port-usage.service"),
            Path("/var/lib/linuxeasyconfig/port-usage/status.json"),
        ),
    },
    "docker_firewall": {
        "title": "Docker firewall persistence helper",
        "description": (
            "Removes the LEC Docker firewall systemd service and apply script, "
            "and removes the active LEC-DOCKER iptables chain. Saved Docker "
            "firewall rule definitions are retained."
        ),
        "units": ("lec-docker-firewall.service",),
        "paths": (
            Path("/etc/systemd/system/lec-docker-firewall.service"),
            Path("/usr/local/sbin/lec-docker-firewall-apply"),
        ),
    },
    "task_scheduler": {
        "title": "Task Scheduler inventory scanner",
        "description": (
            "Removes only the LEC Task Scheduler inventory service and timer. "
            "Scheduled tasks created by the user are retained and continue to run."
        ),
        "units": (
            "lec-task-scheduler-scan.timer",
            "lec-task-scheduler-scan.service",
        ),
        "paths": (
            Path("/etc/systemd/system/lec-task-scheduler-scan.timer"),
            Path("/etc/systemd/system/lec-task-scheduler-scan.service"),
            Path("/var/lib/linuxeasyconfig/task-scheduler/status.json"),
        ),
    },
}


def component_statuses() -> list[LECComponent]:
    result: list[LECComponent] = []
    for component_id, definition in _COMPONENTS.items():
        paths = tuple(definition["paths"])
        units = tuple(definition["units"])
        installed_paths = [
            str(path) for path in paths
            if isinstance(path, Path) and path.exists()
        ]
        known_units = [
            str(unit) for unit in units
            if _unit_known(str(unit))
        ]
        installed = bool(installed_paths or known_units)
        details: list[str] = []
        if known_units:
            details.append("Units: " + ", ".join(known_units))
        if installed_paths:
            details.append("Files: " + ", ".join(installed_paths))
        result.append(
            LECComponent(
                component_id=component_id,
                title=str(definition["title"]),
                description=str(definition["description"]),
                installed=installed,
                detail="\n".join(details) if details else "Not installed.",
            )
        )
    return result


def remove_component(component_id: str) -> str:
    definition = _COMPONENTS.get(component_id)
    if definition is None:
        raise ValueError("The requested LEC component is not recognized.")

    units = tuple(str(value) for value in definition["units"])
    paths = tuple(
        value for value in definition["paths"]
        if isinstance(value, Path)
    )
    removed: list[str] = []

    for unit in units:
        _run_best_effort(["systemctl", "disable", "--now", unit])

    if component_id == "docker_firewall":
        _remove_docker_firewall_chain()

    for path in paths:
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
            removed.append(str(path))
        except OSError as exc:
            raise RuntimeError(f"Could not remove {path}: {exc}") from exc

    _run_required(["systemctl", "daemon-reload"])
    _run_best_effort(["systemctl", "reset-failed"])

    title = str(definition["title"])
    if removed:
        return f"{title} was removed.\n\nRemoved:\n" + "\n".join(removed)
    return f"{title} was already absent."


def _unit_known(unit: str) -> bool:
    result = subprocess.run(
        ["systemctl", "show", unit, "--property=LoadState", "--value"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    return result.stdout.strip() not in {"", "not-found"}


def _remove_docker_firewall_chain() -> None:
    if shutil.which("iptables") is None:
        return
    _run_best_effort(["iptables", "-D", "DOCKER-USER", "-j", "LEC-DOCKER"])
    _run_best_effort(["iptables", "-F", "LEC-DOCKER"])
    _run_best_effort(["iptables", "-X", "LEC-DOCKER"])


def _run_best_effort(command: list[str]) -> None:
    try:
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _run_required(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"{' '.join(command)} failed."
        )
