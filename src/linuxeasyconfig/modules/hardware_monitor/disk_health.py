from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/hardware-monitor/disk-health.json"
)


@dataclass(frozen=True)
class DiskHealthRecord:
    device: str
    name: str
    model: str
    serial: str
    capacity_bytes: int | None
    transport: str
    drive_type: str
    health: str
    health_detail: str
    temperature_c: float | None
    power_on_hours: int | None
    percentage_used: int | None
    remaining_life_percent: int | None
    reallocated_sectors: int | None
    pending_sectors: int | None
    uncorrectable_sectors: int | None
    media_errors: int | None
    unsafe_shutdowns: int | None
    self_test_status: str
    smart_supported: bool
    smart_enabled: bool
    assessment: str


def dependencies() -> dict[str, bool]:
    return {
        "smartctl": shutil.which("smartctl") is not None,
        "nvme": shutil.which("nvme") is not None,
    }




def refresh_disk_health_snapshot() -> str:
    records = collect_disk_health()

    payload = {
        "format_version": 1,
        "dependencies": dependencies(),
        "disks": [
            asdict(record)
            for record in records
        ],
    }

    SNAPSHOT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(SNAPSHOT_PATH.parent, 0o755)

    temporary = SNAPSHOT_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o644)
    temporary.replace(SNAPSHOT_PATH)
    os.chmod(SNAPSHOT_PATH, 0o644)

    return (
        f"Disk health information was refreshed for "
        f"{len(records)} physical drive(s)."
    )


def load_disk_health_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_PATH.is_file():
        return {
            "dependencies": dependencies(),
            "disks": [],
        }

    try:
        value = json.loads(
            SNAPSHOT_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        return {
            "dependencies": dependencies(),
            "disks": [],
        }

    return value if isinstance(value, dict) else {}


def collect_disk_health() -> list[DiskHealthRecord]:
    if shutil.which("smartctl") is None:
        return []

    devices = _list_physical_devices()
    records: list[DiskHealthRecord] = []

    for device in devices:
        record = _read_device(device)
        if record is not None:
            records.append(record)

    return sorted(
        records,
        key=lambda item: item.device.casefold(),
    )


def _list_physical_devices() -> list[dict[str, Any]]:
    result = subprocess.run(
        [
            "lsblk",
            "--json",
            "--bytes",
            "--nodeps",
            "--output",
            "NAME,KNAME,PATH,TYPE,SIZE,MODEL,SERIAL,TRAN,ROTA",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    if result.returncode != 0:
        return []

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return []

    devices: list[dict[str, Any]] = []

    for item in payload.get("blockdevices", []):
        if not isinstance(item, dict):
            continue

        if str(item.get("type", "")) != "disk":
            continue

        path = str(item.get("path", "")).strip()
        if not path:
            continue

        devices.append(item)

    return devices


def _read_device(
    device: dict[str, Any],
) -> DiskHealthRecord | None:
    path = str(device.get("path", "")).strip()

    result = subprocess.run(
        ["smartctl", "-a", "-j", path],
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )

    if not result.stdout.strip():
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    smart_support = payload.get("smart_support", {})
    if not isinstance(smart_support, dict):
        smart_support = {}

    smart_supported = bool(
        smart_support.get("available", False)
    )
    smart_enabled = bool(
        smart_support.get("enabled", False)
    )

    passed = _nested_bool(
        payload,
        "smart_status",
        "passed",
    )

    health, health_detail = _health_text(
        passed=passed,
        supported=smart_supported,
        enabled=smart_enabled,
        messages=payload.get("smartctl", {}).get(
            "messages",
            [],
        )
        if isinstance(payload.get("smartctl"), dict)
        else [],
    )

    temperature = _first_number(
        payload,
        (
            ("temperature", "current"),
            ("nvme_smart_health_information_log", "temperature"),
        ),
    )

    power_on_hours = _first_int(
        payload,
        (
            ("power_on_time", "hours"),
            (
                "nvme_smart_health_information_log",
                "power_on_hours",
            ),
        ),
    )

    percentage_used = _first_int(
        payload,
        (
            (
                "nvme_smart_health_information_log",
                "percentage_used",
            ),
        ),
    )

    remaining_life = (
        max(0, 100 - percentage_used)
        if percentage_used is not None
        else _ata_life_remaining(payload)
    )

    attributes = _ata_attributes(payload)

    reallocated = _attribute_raw(
        attributes,
        names=(
            "Reallocated_Sector_Ct",
            "Reallocated_Event_Count",
        ),
        ids=(5, 196),
    )
    pending = _attribute_raw(
        attributes,
        names=("Current_Pending_Sector",),
        ids=(197,),
    )
    uncorrectable = _attribute_raw(
        attributes,
        names=(
            "Offline_Uncorrectable",
            "Reported_Uncorrect",
        ),
        ids=(198, 187),
    )

    media_errors = _first_int(
        payload,
        (
            (
                "nvme_smart_health_information_log",
                "media_errors",
            ),
        ),
    )
    unsafe_shutdowns = _first_int(
        payload,
        (
            (
                "nvme_smart_health_information_log",
                "unsafe_shutdowns",
            ),
        ),
    )

    self_test_status = _self_test_status(payload)

    model = (
        str(payload.get("model_name", "")).strip()
        or str(device.get("model", "") or "").strip()
        or "Unknown model"
    )
    serial = (
        str(payload.get("serial_number", "")).strip()
        or str(device.get("serial", "") or "").strip()
        or "Unknown"
    )
    capacity = _first_int(
        payload,
        (("user_capacity", "bytes"),),
    )
    if capacity is None:
        try:
            capacity = int(device.get("size"))
        except (TypeError, ValueError):
            capacity = None

    transport = (
        str(device.get("tran", "") or "").strip()
        or str(payload.get("interface_speed", {}).get(
            "type",
            "",
        )).strip()
        if isinstance(payload.get("interface_speed"), dict)
        else ""
    )
    transport = transport or "Unknown"

    rotational = device.get("rota")
    if rotational in (True, 1, "1"):
        drive_type = "Hard disk"
    elif rotational in (False, 0, "0"):
        drive_type = "Solid-state drive"
    else:
        drive_type = "Physical disk"

    assessment = _assessment(
        health=health,
        reallocated=reallocated,
        pending=pending,
        uncorrectable=uncorrectable,
        media_errors=media_errors,
        percentage_used=percentage_used,
        temperature=temperature,
    )

    return DiskHealthRecord(
        device=path,
        name=str(device.get("name", "") or path),
        model=model,
        serial=serial,
        capacity_bytes=capacity,
        transport=transport.upper(),
        drive_type=drive_type,
        health=health,
        health_detail=health_detail,
        temperature_c=temperature,
        power_on_hours=power_on_hours,
        percentage_used=percentage_used,
        remaining_life_percent=remaining_life,
        reallocated_sectors=reallocated,
        pending_sectors=pending,
        uncorrectable_sectors=uncorrectable,
        media_errors=media_errors,
        unsafe_shutdowns=unsafe_shutdowns,
        self_test_status=self_test_status,
        smart_supported=smart_supported,
        smart_enabled=smart_enabled,
        assessment=assessment,
    )


def _health_text(
    *,
    passed: bool | None,
    supported: bool,
    enabled: bool,
    messages: Any,
) -> tuple[str, str]:
    if not supported:
        return (
            "Unavailable",
            "This drive does not report SMART support.",
        )

    if not enabled:
        return (
            "SMART disabled",
            "SMART is supported but currently disabled.",
        )

    if passed is True:
        return (
            "Passed",
            "The drive reports that its overall health test passed.",
        )

    if passed is False:
        return (
            "FAILED",
            "The drive reports a failing overall health result.",
        )

    message_text = ""
    if isinstance(messages, list):
        values = [
            str(item.get("string", "")).strip()
            for item in messages
            if isinstance(item, dict)
            and str(item.get("string", "")).strip()
        ]
        message_text = "; ".join(values)

    return (
        "Unknown",
        message_text
        or "No overall health result was reported.",
    )


def _ata_attributes(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    table = payload.get("ata_smart_attributes", {})
    if not isinstance(table, dict):
        return []

    values = table.get("table", [])
    return [
        value
        for value in values
        if isinstance(value, dict)
    ]


def _attribute_raw(
    attributes: list[dict[str, Any]],
    *,
    names: tuple[str, ...],
    ids: tuple[int, ...],
) -> int | None:
    for attribute in attributes:
        name = str(attribute.get("name", ""))
        attribute_id = attribute.get("id")

        if name not in names and attribute_id not in ids:
            continue

        raw = attribute.get("raw", {})
        if isinstance(raw, dict):
            value = raw.get("value")
        else:
            value = raw

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return None


def _ata_life_remaining(
    payload: dict[str, Any],
) -> int | None:
    attributes = _ata_attributes(payload)

    for attribute in attributes:
        name = str(
            attribute.get("name", "")
        ).casefold()

        if not any(
            marker in name
            for marker in (
                "remaining_lifetime",
                "ssd_life_left",
                "percent_lifetime_remain",
                "media_wearout_indicator",
            )
        ):
            continue

        value = attribute.get("value")

        try:
            number = int(value)
        except (TypeError, ValueError):
            continue

        if 0 <= number <= 100:
            return number

    return None


def _self_test_status(
    payload: dict[str, Any],
) -> str:
    ata = payload.get("ata_smart_self_test_log", {})
    if isinstance(ata, dict):
        table = ata.get("standard", {}).get(
            "table",
            [],
        ) if isinstance(ata.get("standard"), dict) else []

        if isinstance(table, list) and table:
            first = table[0]
            if isinstance(first, dict):
                status = first.get("status", {})
                if isinstance(status, dict):
                    text = str(
                        status.get("string", "")
                    ).strip()
                    if text:
                        return text

    nvme = payload.get(
        "nvme_self_test_log",
        {},
    )
    if isinstance(nvme, dict):
        current = nvme.get(
            "current_self_test_operation",
        )
        if isinstance(current, dict):
            text = str(
                current.get("string", "")
            ).strip()
            if text and text.casefold() != "none":
                return text

        result = nvme.get(
            "self_test_result",
            [],
        )
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                text = str(
                    first.get("self_test_result", {}).get(
                        "string",
                        "",
                    )
                ).strip() if isinstance(
                    first.get("self_test_result"),
                    dict,
                ) else ""
                if text:
                    return text

    return "No self-test result reported"


def _assessment(
    *,
    health: str,
    reallocated: int | None,
    pending: int | None,
    uncorrectable: int | None,
    media_errors: int | None,
    percentage_used: int | None,
    temperature: float | None,
) -> str:
    if health == "FAILED":
        return (
            "Critical: back up this drive immediately "
            "and plan to replace it."
        )

    concerns: list[str] = []

    if pending and pending > 0:
        concerns.append(
            f"{pending} pending sector(s)"
        )
    if uncorrectable and uncorrectable > 0:
        concerns.append(
            f"{uncorrectable} uncorrectable sector error(s)"
        )
    if media_errors and media_errors > 0:
        concerns.append(
            f"{media_errors} media/data integrity error(s)"
        )
    if reallocated and reallocated > 0:
        concerns.append(
            f"{reallocated} reallocated sector event(s)"
        )
    if percentage_used is not None and percentage_used >= 90:
        concerns.append(
            f"{percentage_used}% of rated endurance used"
        )
    if temperature is not None and temperature >= 60:
        concerns.append(
            f"high temperature ({temperature:.0f} °C)"
        )

    if concerns:
        return (
            "Attention recommended: "
            + "; ".join(concerns)
            + "."
        )

    if health == "Passed":
        return (
            "No obvious SMART warning indicators were found. "
            "SMART cannot guarantee that a drive will not fail."
        )

    return health


def _nested_bool(
    payload: dict[str, Any],
    *keys: str,
) -> bool | None:
    value: Any = payload

    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    return value if isinstance(value, bool) else None


def _first_int(
    payload: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> int | None:
    value = _first_value(payload, paths)

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_number(
    payload: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> float | None:
    value = _first_value(payload, paths)

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_value(
    payload: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> Any:
    for path in paths:
        value: Any = payload

        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)

        if value is not None:
            return value

    return None
