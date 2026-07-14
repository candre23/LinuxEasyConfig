from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import psutil

from .gpu import GPUCollector


_IGNORED_FILESYSTEM_TYPES = {
    "autofs",
    "cgroup",
    "cgroup2",
    "configfs",
    "debugfs",
    "devpts",
    "devtmpfs",
    "efivarfs",
    "fusectl",
    "hugetlbfs",
    "mqueue",
    "overlay",
    "proc",
    "pstore",
    "securityfs",
    "squashfs",
    "sysfs",
    "tmpfs",
    "tracefs",
}

_IGNORED_MOUNT_PREFIXES = (
    "/snap/",
    "/run/snapd/",
)


@dataclass(frozen=True)
class Rate:
    receive_bytes_per_second: float = 0.0
    send_bytes_per_second: float = 0.0


@dataclass(frozen=True)
class DiskRate:
    read_bytes_per_second: float = 0.0
    write_bytes_per_second: float = 0.0


class HardwareCollector:
    """Collect live hardware statistics without blocking the UI."""

    def __init__(self) -> None:
        self._last_sample_time = time.monotonic()
        self._last_network = psutil.net_io_counters(pernic=True)
        self._last_disk = psutil.disk_io_counters()
        self._gpu = GPUCollector()

        psutil.cpu_percent(interval=None, percpu=True)

    def sample(self) -> dict[str, Any]:
        now = time.monotonic()
        elapsed = max(now - self._last_sample_time, 0.001)

        network_counters = psutil.net_io_counters(pernic=True)
        disk_counters = psutil.disk_io_counters()

        sample = {
            "timestamp": now,
            "cpu": self._collect_cpu(),
            "memory": self._collect_memory(),
            "network": self._collect_network(
                network_counters,
                elapsed,
            ),
            "disk_io": self._collect_disk_io(
                disk_counters,
                elapsed,
            ),
            "filesystems": self._collect_filesystems(),
            "temperatures": self._collect_temperatures(),
            "gpus": self._gpu.sample(),
        }

        self._last_sample_time = now
        self._last_network = network_counters
        self._last_disk = disk_counters

        return sample

    def close(self) -> None:
        self._gpu.close()

    @staticmethod
    def _collect_cpu() -> dict[str, Any]:
        per_core = psutil.cpu_percent(
            interval=None,
            percpu=True,
        )

        overall = (
            sum(per_core) / len(per_core)
            if per_core
            else 0.0
        )

        return {
            "overall_percent": overall,
            "per_core_percent": per_core,
            "logical_count": psutil.cpu_count(logical=True) or 0,
            "physical_count": psutil.cpu_count(logical=False) or 0,
            "frequency_mhz": HardwareCollector._cpu_frequency(),
        }

    @staticmethod
    def _cpu_frequency() -> float | None:
        frequency = psutil.cpu_freq()
        return None if frequency is None else float(frequency.current)

    @staticmethod
    def _collect_memory() -> dict[str, Any]:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "ram": {
                "total": memory.total,
                "used": memory.used,
                "available": memory.available,
                "percent": memory.percent,
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
            },
        }

    def _collect_network(
        self,
        current: dict[str, Any],
        elapsed: float,
    ) -> list[dict[str, Any]]:
        interfaces: list[dict[str, Any]] = []
        stats = psutil.net_if_stats()

        for name, counters in sorted(current.items()):
            if name == "lo":
                continue

            interface_stats = stats.get(name)

            if interface_stats is not None and not interface_stats.isup:
                continue

            previous = self._last_network.get(name)

            if previous is None:
                rate = Rate()
            else:
                rate = Rate(
                    receive_bytes_per_second=max(
                        counters.bytes_recv - previous.bytes_recv,
                        0,
                    )
                    / elapsed,
                    send_bytes_per_second=max(
                        counters.bytes_sent - previous.bytes_sent,
                        0,
                    )
                    / elapsed,
                )

            interfaces.append(
                {
                    "name": name,
                    "receive_rate": rate.receive_bytes_per_second,
                    "send_rate": rate.send_bytes_per_second,
                    "received_total": counters.bytes_recv,
                    "sent_total": counters.bytes_sent,
                }
            )

        return interfaces

    def _collect_disk_io(
        self,
        current: Any,
        elapsed: float,
    ) -> dict[str, float]:
        previous = self._last_disk

        if current is None or previous is None:
            rate = DiskRate()
        else:
            rate = DiskRate(
                read_bytes_per_second=max(
                    current.read_bytes - previous.read_bytes,
                    0,
                )
                / elapsed,
                write_bytes_per_second=max(
                    current.write_bytes - previous.write_bytes,
                    0,
                )
                / elapsed,
            )

        return {
            "read_rate": rate.read_bytes_per_second,
            "write_rate": rate.write_bytes_per_second,
        }

    @staticmethod
    def _collect_filesystems() -> list[dict[str, Any]]:
        filesystems: list[dict[str, Any]] = []
        seen_mounts: set[str] = set()

        for partition in psutil.disk_partitions(all=False):
            mountpoint = partition.mountpoint

            if mountpoint in seen_mounts:
                continue

            if partition.fstype.lower() in _IGNORED_FILESYSTEM_TYPES:
                continue

            if mountpoint.startswith(_IGNORED_MOUNT_PREFIXES):
                continue

            try:
                usage = psutil.disk_usage(mountpoint)
            except (OSError, PermissionError):
                continue

            seen_mounts.add(mountpoint)
            filesystems.append(
                {
                    "device": partition.device,
                    "mountpoint": mountpoint,
                    "filesystem": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            )

        filesystems.sort(
            key=lambda item: (
                item["mountpoint"] != "/",
                item["mountpoint"].casefold(),
            )
        )
        return filesystems

    @staticmethod
    def _collect_temperatures() -> list[dict[str, Any]]:
        try:
            sensor_groups = psutil.sensors_temperatures()
        except (AttributeError, OSError):
            return []

        temperatures: list[dict[str, Any]] = []

        for group_name, readings in sorted(sensor_groups.items()):
            for index, reading in enumerate(readings, start=1):
                label = (
                    reading.label.strip()
                    if reading.label
                    else f"Sensor {index}"
                )
                temperatures.append(
                    {
                        "group": group_name,
                        "label": label,
                        "current": reading.current,
                        "high": reading.high,
                        "critical": reading.critical,
                    }
                )

        return temperatures
