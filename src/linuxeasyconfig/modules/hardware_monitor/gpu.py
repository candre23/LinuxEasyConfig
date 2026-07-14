from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


_INTEL_VENDOR = "0x8086"
_AMD_VENDOR = "0x1002"
_NVIDIA_VENDOR = "0x10de"


class GPUCollector:
    """Detect GPUs and expose the best available monitoring adapter."""

    def __init__(self) -> None:
        self._devices = self._detect_devices()
        self._intel_monitor: _IntelMonitor | None = None

        if any(device["vendor"] == "intel" for device in self._devices):
            self._intel_monitor = _IntelMonitor()

    def sample(self) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []

        for device in self._devices:
            vendor = device["vendor"]

            if vendor == "intel":
                samples.append(self._sample_intel(device))
            elif vendor == "nvidia":
                samples.extend(self._sample_nvidia(device))
            elif vendor == "amd":
                samples.append(self._sample_amd(device))
            else:
                samples.append(
                    {
                        **device,
                        "status": "unsupported",
                        "message": (
                            "This graphics device is detected, but LEC "
                            "does not yet have a monitoring adapter for it."
                        ),
                    }
                )

        return samples

    def close(self) -> None:
        if self._intel_monitor is not None:
            self._intel_monitor.close()

    def _sample_intel(
        self,
        device: dict[str, Any],
    ) -> dict[str, Any]:
        if shutil.which("intel_gpu_top") is None:
            return {
                **device,
                "status": "missing_tool",
                "message": (
                    "Detailed Intel GPU monitoring requires "
                    "intel-gpu-tools."
                ),
                "install_command": (
                    "sudo apt install intel-gpu-tools"
                ),
            }

        if self._intel_monitor is None:
            self._intel_monitor = _IntelMonitor()

        reading = self._intel_monitor.latest()

        if reading is None:
            error = self._intel_monitor.error

            permission_denied = bool(
                error
                and (
                    "CAP_PERFMON" in error
                    or "Permission denied" in error
                    or "Failed to initialize PMU" in error
                )
            )

            if permission_denied:
                return {
                    **device,
                    "status": "permission_required",
                    "message": (
                        "intel_gpu_top is installed, but this user does "
                        "not have permission to read Intel GPU performance "
                        "counters."
                    ),
                    "install_command": (
                        'sudo setcap cap_perfmon=ep $(readlink -f "$(command -v intel_gpu_top)")'
                    ),
                    "additional_note": (
                        "Close and reopen LEC after running this command. "
                        "A future intel-gpu-tools package upgrade may require "
                        "the capability to be applied again."
                    ),
                }

            return {
                **device,
                "status": "waiting" if not error else "error",
                "message": (
                    error
                    or "Waiting for the first Intel GPU sample…"
                ),
            }

        return {
            **device,
            "status": "ok",
            **reading,
            "memory_type": "Shared system memory",
        }

    @staticmethod
    def _sample_nvidia(
        device: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if shutil.which("nvidia-smi") is None:
            return [
                {
                    **device,
                    "status": "missing_tool",
                    "message": (
                        "Detailed NVIDIA monitoring requires the "
                        "proprietary NVIDIA driver, which supplies "
                        "nvidia-smi. Install the recommended driver "
                        "through Ubuntu's Additional Drivers tool."
                    ),
                }
            ]

        command = [
            "nvidia-smi",
            "--query-gpu=index,name,driver_version,utilization.gpu,"
            "utilization.memory,memory.used,memory.total,"
            "temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return [
                {
                    **device,
                    "status": "error",
                    "message": str(exc),
                }
            ]

        if result.returncode != 0:
            return [
                {
                    **device,
                    "status": "error",
                    "message": (
                        result.stderr.strip()
                        or result.stdout.strip()
                        or "nvidia-smi failed."
                    ),
                }
            ]

        samples: list[dict[str, Any]] = []

        for line in result.stdout.splitlines():
            fields = [field.strip() for field in line.split(",")]

            if len(fields) != 9:
                continue

            (
                index,
                name,
                driver,
                gpu_util,
                memory_util,
                memory_used,
                memory_total,
                temperature,
                power,
            ) = fields

            samples.append(
                {
                    "vendor": "nvidia",
                    "name": name,
                    "driver": driver,
                    "device_path": device.get("device_path", ""),
                    "index": index,
                    "status": "ok",
                    "utilization_percent": _number(gpu_util),
                    "memory_utilization_percent": _number(
                        memory_util
                    ),
                    "memory_used_bytes": _mib_to_bytes(
                        memory_used
                    ),
                    "memory_total_bytes": _mib_to_bytes(
                        memory_total
                    ),
                    "temperature_c": _number(temperature),
                    "power_w": _number(power),
                    "memory_type": "Dedicated VRAM",
                }
            )

        return samples or [
            {
                **device,
                "status": "error",
                "message": "nvidia-smi returned no GPU records.",
            }
        ]

    @staticmethod
    def _sample_amd(
        device: dict[str, Any],
    ) -> dict[str, Any]:
        card_path = Path(device["device_path"])
        device_path = card_path / "device"

        busy = _read_number(device_path / "gpu_busy_percent")
        memory_used = _read_number(
            device_path / "mem_info_vram_used"
        )
        memory_total = _read_number(
            device_path / "mem_info_vram_total"
        )

        temperature = _read_amd_temperature(device_path)

        if (
            busy is None
            and memory_used is None
            and memory_total is None
            and temperature is None
        ):
            return {
                **device,
                "status": "unsupported",
                "message": (
                    "The active AMD driver does not expose supported "
                    "GPU monitoring counters through sysfs."
                ),
            }

        return {
            **device,
            "status": "ok",
            "utilization_percent": busy,
            "memory_used_bytes": memory_used,
            "memory_total_bytes": memory_total,
            "temperature_c": temperature,
            "memory_type": "VRAM",
        }

    @staticmethod
    def _detect_devices() -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = []

        for card in sorted(Path("/sys/class/drm").iterdir()):
            if re.fullmatch(r"card\d+", card.name) is None:
                continue

            if not (card / "device").exists():
                continue

            vendor_id = _read_text(card / "device/vendor")
            driver = _driver_name(card / "device")
            vendor = {
                _INTEL_VENDOR: "intel",
                _AMD_VENDOR: "amd",
                _NVIDIA_VENDOR: "nvidia",
            }.get(vendor_id, "unknown")

            devices.append(
                {
                    "vendor": vendor,
                    "name": _pci_display_name(card),
                    "driver": driver or "Unknown",
                    "device_path": str(card),
                }
            )

        if devices:
            return devices

        return _detect_devices_with_lspci()


class _IntelMonitor:
    """Maintain one background intel_gpu_top JSON stream."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: dict[str, Any] | None = None
        self._error = ""
        self._stop = threading.Event()
        self._process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None

        if shutil.which("intel_gpu_top") is not None:
            self._start()

    @property
    def error(self) -> str:
        with self._lock:
            return self._error

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            return (
                dict(self._latest)
                if self._latest is not None
                else None
            )

    def close(self) -> None:
        self._stop.set()

        process = self._process

        if process is not None and process.poll() is None:
            process.terminate()

            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()

    def _start(self) -> None:
        self._thread = threading.Thread(
            target=self._run,
            name="lec-intel-gpu-monitor",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        try:
            self._process = subprocess.Popen(
                [
                    "intel_gpu_top",
                    "-J",
                    "-s",
                    "1000",
                    "-o",
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            self._set_error(str(exc))
            return

        assert self._process.stdout is not None

        decoder = json.JSONDecoder()
        buffer = ""

        while not self._stop.is_set():
            line = self._process.stdout.readline()

            if not line:
                break

            buffer += line

            while buffer:
                buffer = buffer.lstrip(" \t\r\n,[")

                if not buffer:
                    break

                if buffer.startswith("]"):
                    buffer = buffer[1:]
                    continue

                try:
                    value, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    break

                buffer = buffer[end:]

                if isinstance(value, dict):
                    self._set_latest(
                        _parse_intel_gpu_top(value)
                    )

        return_code = self._process.poll()

        if (
            not self._stop.is_set()
            and return_code not in (None, 0)
        ):
            stderr = ""

            if self._process.stderr is not None:
                stderr = self._process.stderr.read().strip()

            self._set_error(
                stderr
                or (
                    "intel_gpu_top exited unexpectedly. GPU performance "
                    "counters may require additional permissions."
                )
            )

    def _set_latest(self, value: dict[str, Any]) -> None:
        with self._lock:
            self._latest = value
            self._error = ""

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._error = message


def _parse_intel_gpu_top(
    payload: dict[str, Any],
) -> dict[str, Any]:
    engines = payload.get("engines", {})
    engine_values: dict[str, float] = {}

    if isinstance(engines, dict):
        for name, metrics in engines.items():
            if not isinstance(metrics, dict):
                continue

            busy = metrics.get("busy")

            if isinstance(busy, (int, float)):
                engine_values[str(name)] = float(busy)

    utilization = max(engine_values.values(), default=0.0)

    render = max(
        (
            value
            for name, value in engine_values.items()
            if "render" in name.casefold()
            or "3d" in name.casefold()
        ),
        default=None,
    )
    video = max(
        (
            value
            for name, value in engine_values.items()
            if "video" in name.casefold()
        ),
        default=None,
    )
    blitter = max(
        (
            value
            for name, value in engine_values.items()
            if "blitter" in name.casefold()
            or "copy" in name.casefold()
        ),
        default=None,
    )

    frequency = payload.get("frequency", {})

    if not isinstance(frequency, dict):
        frequency = {}

    power = payload.get("power", {})

    if not isinstance(power, dict):
        power = {}

    return {
        "utilization_percent": utilization,
        "render_percent": render,
        "video_percent": video,
        "copy_percent": blitter,
        "frequency_mhz": _number(
            frequency.get("actual")
        ),
        "requested_frequency_mhz": _number(
            frequency.get("requested")
        ),
        "power_w": _number(power.get("GPU")),
        "engines": engine_values,
    }


def _detect_devices_with_lspci() -> list[dict[str, Any]]:
    if shutil.which("lspci") is None:
        return []

    try:
        result = subprocess.run(
            ["lspci", "-nnk"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    devices: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in result.stdout.splitlines():
        if line and not line[0].isspace():
            lower = line.casefold()

            if not any(
                marker in lower
                for marker in (
                    "vga compatible controller",
                    "3d controller",
                    "display controller",
                )
            ):
                current = None
                continue

            vendor = "unknown"

            if "[8086:" in lower:
                vendor = "intel"
            elif "[1002:" in lower:
                vendor = "amd"
            elif "[10de:" in lower:
                vendor = "nvidia"

            name = line.split(":", 2)[-1].strip()
            current = {
                "vendor": vendor,
                "name": name,
                "driver": "Unknown",
                "device_path": "",
            }
            devices.append(current)
        elif current is not None:
            stripped = line.strip()

            if stripped.startswith("Kernel driver in use:"):
                current["driver"] = stripped.partition(":")[2].strip()

    return devices


def _pci_display_name(card: Path) -> str:
    slot = _read_text(card / "device/uevent")
    pci_slot = ""

    for line in slot.splitlines():
        if line.startswith("PCI_SLOT_NAME="):
            pci_slot = line.partition("=")[2]
            break

    if not pci_slot or shutil.which("lspci") is None:
        return card.name

    try:
        result = subprocess.run(
            ["lspci", "-s", pci_slot],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return card.name

    text = result.stdout.strip()

    if not text:
        return card.name

    return text.split(":", 2)[-1].strip()


def _driver_name(device_path: Path) -> str:
    driver = device_path / "driver"

    try:
        return driver.resolve().name
    except OSError:
        return ""


def _read_amd_temperature(device_path: Path) -> float | None:
    for hwmon in sorted((device_path / "hwmon").glob("hwmon*")):
        for input_path in sorted(hwmon.glob("temp*_input")):
            value = _read_number(input_path)

            if value is not None:
                return value / 1000.0

    return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()
    except OSError:
        return ""


def _read_number(path: Path) -> float | None:
    text = _read_text(path)

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text or text.casefold() in {
        "n/a",
        "not supported",
        "[not supported]",
    }:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def _mib_to_bytes(value: Any) -> float | None:
    number = _number(value)
    return None if number is None else number * 1024 * 1024
