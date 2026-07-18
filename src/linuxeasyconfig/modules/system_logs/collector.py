from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .interpreter import interpret


PRIORITY_NAMES = {
    0: "Emergency",
    1: "Alert",
    2: "Critical",
    3: "Error",
    4: "Warning",
    5: "Notice",
    6: "Info",
    7: "Debug",
}

ALLOWED_RAW_ROOT = Path("/var/log")
MAX_RAW_FILE_BYTES = 2_000_000


def collect_journal(
    *,
    mode: str,
    since: str,
    priority: int,
    unit: str = "",
    keyword: str = "",
    limit: int = 1000,
    current_boot: bool = False,
    grouped: bool = True,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 5000))
    priority = max(0, min(int(priority), 7))
    mode = mode.strip().lower()

    command = [
        "journalctl",
        "--no-pager",
        "--output=json",
        "--reverse",
        f"--lines={limit}",
        f"--priority=0..{priority}",
    ]

    if since:
        command.extend(["--since", since])

    if current_boot or mode in {"boot", "security"}:
        command.append("--boot")

    if mode == "boot":
        command.extend(["--dmesg"])
    elif mode == "security":
        command.extend(
            [
                "--identifier=sshd",
                "--identifier=sudo",
                "--identifier=su",
                "--identifier=polkitd",
                "--identifier=systemd-logind",
            ]
        )
    elif unit:
        command.extend(["--unit", unit])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or "journalctl failed."
        )

        if (
            "permission" in detail.casefold()
            or "not authorized" in detail.casefold()
        ):
            raise RuntimeError(
                "Your account does not currently have permission to "
                "read the system journal. Add the account to the "
                "'systemd-journal' or 'adm' group, then sign out and "
                "back in. LEC will not repeatedly request administrator "
                "authorization for this read-only module.\n\n"
                + detail
            )

        raise RuntimeError(detail)

    events: list[dict[str, Any]] = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue

        event = _event_from_journal(raw)

        if keyword and keyword.casefold() not in (
            event["message"]
            + " "
            + event["source"]
            + " "
            + event["unit"]
            + " "
            + event["summary"]
        ).casefold():
            continue

        events.append(event)

    if grouped:
        events = _group_events(events)

    summary = _summary(events)

    return {
        "events": events,
        "summary": summary,
        "units": list_units(),
        "generated_at": dt.datetime.now(
            dt.timezone.utc
        ).isoformat(),
        "mode": mode,
    }


def collect_overview() -> dict[str, Any]:
    recent = collect_journal(
        mode="overview",
        since="24 hours ago",
        priority=4,
        limit=2000,
        grouped=True,
    )

    failed_units = _failed_units()
    boots = _recent_boots()

    return {
        "events": recent["events"][:100],
        "summary": recent["summary"],
        "failed_units": failed_units,
        "boots": boots,
        "generated_at": recent["generated_at"],
    }


def list_units() -> list[str]:
    result = subprocess.run(
        [
            "systemctl",
            "list-units",
            "--type=service",
            "--all",
            "--no-legend",
            "--plain",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    units: list[str] = []

    for line in result.stdout.splitlines():
        parts = line.split()

        if parts and parts[0].endswith(".service"):
            units.append(parts[0])

    return sorted(set(units), key=str.casefold)


def list_raw_sources() -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []

    if not ALLOWED_RAW_ROOT.is_dir():
        return sources

    for path in sorted(
        ALLOWED_RAW_ROOT.rglob("*"),
        key=lambda item: str(item).casefold(),
    ):
        try:
            if (
                path.is_symlink()
                or not path.is_file()
                or not os.access(path, os.R_OK)
            ):
                continue

            relative = path.relative_to(ALLOWED_RAW_ROOT)

            if len(relative.parts) > 3:
                continue

            stat_result = path.stat()

            sources.append(
                {
                    "path": str(path),
                    "size": stat_result.st_size,
                    "modified": dt.datetime.fromtimestamp(
                        stat_result.st_mtime
                    ).astimezone().isoformat(
                        timespec="seconds"
                    ),
                }
            )
        except OSError:
            continue

    return sources[:500]


def read_raw_source(
    *,
    path: str,
    lines: int = 500,
) -> dict[str, Any]:
    requested = Path(path)
    resolved = requested.resolve(strict=True)
    root = ALLOWED_RAW_ROOT.resolve(strict=True)

    if resolved == root or root not in resolved.parents:
        raise ValueError(
            "Only regular files beneath /var/log may be read."
        )

    if resolved.is_symlink() or not resolved.is_file():
        raise ValueError(
            "The selected log source is not a regular file."
        )

    lines = max(1, min(int(lines), 5000))
    size = resolved.stat().st_size

    try:
        with resolved.open("rb") as handle:
            if size > MAX_RAW_FILE_BYTES:
                handle.seek(-MAX_RAW_FILE_BYTES, os.SEEK_END)

            raw = handle.read(MAX_RAW_FILE_BYTES)
    except PermissionError as exc:
        raise RuntimeError(
            "This log file is protected and cannot be read by your "
            "normal account. LEC intentionally does not request an "
            "administrator password for passive log browsing."
        ) from exc

    text = raw.decode("utf-8", errors="replace")
    selected = text.splitlines()[-lines:]

    return {
        "path": str(resolved),
        "size": size,
        "truncated": size > len(raw),
        "text": "\n".join(selected),
    }


def _event_from_journal(
    raw: dict[str, Any],
) -> dict[str, Any]:
    priority = _integer(raw.get("PRIORITY"), 6)
    message = _value(raw.get("MESSAGE"))
    source = (
        _value(raw.get("SYSLOG_IDENTIFIER"))
        or _value(raw.get("_COMM"))
        or _value(raw.get("_EXE")).rsplit("/", 1)[-1]
    )
    unit = _value(raw.get("_SYSTEMD_UNIT"))
    process = _value(raw.get("_COMM"))
    pid = _value(raw.get("_PID"))
    timestamp = _timestamp(
        raw.get("__REALTIME_TIMESTAMP")
    )
    severity = PRIORITY_NAMES.get(priority, "Info")
    interpretation = interpret(
        message=message,
        source=source,
        unit=unit,
        severity=severity,
    )

    return {
        "timestamp": timestamp,
        "first_timestamp": timestamp,
        "last_timestamp": timestamp,
        "priority": priority,
        "severity": severity,
        "source": source,
        "unit": unit,
        "process": process,
        "pid": pid,
        "category": interpretation.category,
        "summary": interpretation.summary,
        "explanation": interpretation.explanation,
        "suggestion": interpretation.suggestion,
        "confidence": interpretation.confidence,
        "message": message,
        "count": 1,
        "boot_id": _value(raw.get("_BOOT_ID")),
    }


def _group_events(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    ordered: list[str] = []

    for event in events:
        key = _group_key(event)

        if key not in groups:
            groups[key] = dict(event)
            ordered.append(key)
            continue

        group = groups[key]
        group["count"] += 1
        group["first_timestamp"] = min(
            group["first_timestamp"],
            event["timestamp"],
        )
        group["last_timestamp"] = max(
            group["last_timestamp"],
            event["timestamp"],
        )
        group["timestamp"] = max(
            group["timestamp"],
            event["timestamp"],
        )

    return [groups[key] for key in ordered]


def _group_key(event: dict[str, Any]) -> str:
    normalized = event["message"].casefold()
    normalized = re.sub(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "<ip>",
        normalized,
    )
    normalized = re.sub(
        r"\b[0-9a-f]{8,}\b",
        "<id>",
        normalized,
    )
    normalized = re.sub(
        r"\b\d+\b",
        "<n>",
        normalized,
    )
    value = "|".join(
        [
            event["source"],
            event["unit"],
            event["severity"],
            event["summary"],
            normalized,
        ]
    )
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def _summary(
    events: list[dict[str, Any]],
) -> dict[str, int]:
    result = {
        "total": 0,
        "critical": 0,
        "errors": 0,
        "warnings": 0,
        "known_patterns": 0,
    }

    for event in events:
        count = int(event.get("count", 1))
        result["total"] += count

        if event["priority"] <= 2:
            result["critical"] += count
        elif event["priority"] == 3:
            result["errors"] += count
        elif event["priority"] == 4:
            result["warnings"] += count

        if event["confidence"] == "Known pattern":
            result["known_patterns"] += count

    return result


def _failed_units() -> list[dict[str, str]]:
    result = subprocess.run(
        [
            "systemctl",
            "list-units",
            "--state=failed",
            "--no-legend",
            "--plain",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    failed: list[dict[str, str]] = []

    for line in result.stdout.splitlines():
        parts = line.split(None, 4)

        if not parts:
            continue

        unit = parts[0]
        properties = _systemctl_properties(
            unit,
            (
                "Description",
                "Result",
                "ExecMainStatus",
                "ExecMainCode",
                "ActiveEnterTimestamp",
                "InactiveEnterTimestamp",
            ),
        )
        timer = _associated_timer(unit)
        timer_properties = (
            _systemctl_properties(
                timer,
                (
                    "ActiveState",
                    "UnitFileState",
                    "NextElapseUSecRealtime",
                    "LastTriggerUSec",
                ),
            )
            if timer
            else {}
        )

        failed.append(
            {
                "unit": unit,
                "description": (
                    properties.get("Description")
                    or (parts[4] if len(parts) >= 5 else "")
                ),
                "result": properties.get("Result") or "Unknown",
                "exit_status": _exit_status_text(properties),
                "last_failure": (
                    properties.get("InactiveEnterTimestamp")
                    or properties.get("ActiveEnterTimestamp")
                    or "Unknown"
                ),
                "timer": timer or "None",
                "timer_status": _timer_status_text(
                    timer_properties
                ),
                "next_run": (
                    timer_properties.get("NextElapseUSecRealtime")
                    or "Not scheduled"
                ),
            }
        )

    return failed


def _systemctl_properties(
    unit: str,
    properties: tuple[str, ...],
) -> dict[str, str]:
    command = ["systemctl", "show", unit]

    for property_name in properties:
        command.extend(["--property", property_name])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    values: dict[str, str] = {}

    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")

        if separator:
            values[key] = value.strip()

    return values


def _associated_timer(service_unit: str) -> str:
    if not service_unit.endswith(".service"):
        return ""

    candidate = (
        service_unit.removesuffix(".service")
        + ".timer"
    )
    result = subprocess.run(
        [
            "systemctl",
            "show",
            candidate,
            "--property=LoadState",
            "--value",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    return candidate if result.stdout.strip() == "loaded" else ""


def _exit_status_text(
    properties: dict[str, str],
) -> str:
    code = properties.get("ExecMainCode", "")
    status = properties.get("ExecMainStatus", "")

    if not code and not status:
        return "Unknown"

    if status in {"", "0"}:
        return code or "0"

    return f"{code or 'exit'} / {status}"


def _timer_status_text(
    properties: dict[str, str],
) -> str:
    if not properties:
        return "No associated timer"

    active = properties.get("ActiveState", "unknown")
    enabled = properties.get("UnitFileState", "unknown")
    last_trigger = properties.get("LastTriggerUSec", "")
    result = f"{active}; {enabled}"

    if last_trigger:
        result += f"; last trigger {last_trigger}"

    return result


def _recent_boots() -> list[dict[str, str]]:
    result = subprocess.run(
        [
            "journalctl",
            "--list-boots",
            "--no-pager",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    boots: list[dict[str, str]] = []

    for line in result.stdout.splitlines()[-10:]:
        parts = line.split(None, 2)

        if len(parts) < 3:
            continue

        boots.append(
            {
                "offset": parts[0],
                "boot_id": parts[1],
                "range": parts[2],
            }
        )

    return boots


def _timestamp(value: Any) -> str:
    try:
        microseconds = int(value)
        return dt.datetime.fromtimestamp(
            microseconds / 1_000_000,
            tz=dt.timezone.utc,
        ).astimezone().isoformat(
            timespec="seconds"
        )
    except (TypeError, ValueError, OSError):
        return ""


def _integer(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _value(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)

    if value is None:
        return ""

    return str(value)
