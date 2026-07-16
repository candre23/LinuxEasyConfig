from __future__ import annotations

import os
import subprocess

from .disk_health import refresh_disk_health_snapshot


def install_disk_health_tools() -> str:
    environment = os.environ.copy()
    environment["DEBIAN_FRONTEND"] = "noninteractive"

    _run(
        ["apt-get", "update"],
        timeout=600,
        environment=environment,
    )
    _run(
        [
            "apt-get",
            "install",
            "-y",
            "smartmontools",
            "nvme-cli",
        ],
        timeout=900,
        environment=environment,
    )

    refresh_disk_health_snapshot()

    return (
        "Disk health tools were installed and "
        "the drive information was refreshed."
    )


def enable_smart(*, device: str) -> str:
    _validate_device(device)

    _run(
        ["smartctl", "--smart=on", device],
        timeout=60,
    )
    refresh_disk_health_snapshot()
    return f"SMART monitoring was enabled for {device}."


def start_self_test(
    *,
    device: str,
    test_type: str,
) -> str:
    _validate_device(device)

    normalized = test_type.strip().lower()

    if normalized not in {"short", "long"}:
        raise ValueError(
            "The selected self-test type is invalid."
        )

    _run(
        ["smartctl", "--test", normalized, device],
        timeout=60,
    )
    refresh_disk_health_snapshot()

    label = (
        "extended"
        if normalized == "long"
        else "short"
    )
    return (
        f"The {label} self-test was started on "
        f"{device}. The drive runs the test in the "
        "background."
    )


def _validate_device(device: str) -> None:
    if (
        not device.startswith("/dev/")
        or any(
            character in device
            for character in "\0\n\r"
        )
    ):
        raise ValueError(
            "The selected disk device is invalid."
        )


def _run(
    command: list[str],
    *,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=environment,
    )

    if result.returncode == 0:
        return

    message = (
        result.stderr.strip()
        or result.stdout.strip()
        or (
            f"{command[0]} exited with code "
            f"{result.returncode}"
        )
    )

    raise RuntimeError(
        f"{' '.join(command)} failed:\n\n{message}"
    )
