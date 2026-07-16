from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from linuxeasyconfig.core.config.audit_log import AuditLog
from linuxeasyconfig.core.config.base import ConfigurationDocument
from linuxeasyconfig.core.config.writer import ConfigurationWriter


MODULE_ID = "org.linuxeasyconfig.services"
BACKUP_ROOT = Path("/var/lib/linuxeasyconfig/backups")
AUDIT_PATH = Path("/var/lib/linuxeasyconfig/audit.jsonl")
SYSTEMD_DIRECTORY = Path("/etc/systemd/system")

_SERVICE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9_.@:-]+$"
)


class RenderedConfiguration(ConfigurationDocument):
    """Configuration document containing already-rendered text."""

    def __init__(self, text: str) -> None:
        self._text = text

    def render(self) -> str:
        text = self._text

        if not text.endswith("\n"):
            text += "\n"

        return text


def install_service(
    *,
    source: Path,
    service_name: str,
    enable_at_startup: bool,
    start_immediately: bool,
) -> str:
    service_name = _validate_service_name(service_name)
    destination = SYSTEMD_DIRECTORY / f"{service_name}.service"

    if source.is_symlink() or not source.is_file():
        raise ValueError("The staged service configuration is invalid.")

    rendered_text = source.read_text(encoding="utf-8")
    document = RenderedConfiguration(rendered_text)

    validation = subprocess.run(
        [
            "systemd-analyze",
            "verify",
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if validation.returncode != 0:
        message = (
            validation.stderr.strip()
            or validation.stdout.strip()
            or "systemd-analyze reported an unknown error."
        )
        raise RuntimeError(
            f"The generated service configuration is invalid:\n\n{message}"
        )

    writer = ConfigurationWriter(
        backup_root=BACKUP_ROOT,
        audit_log=AuditLog(AUDIT_PATH),
    )

    result = writer.write(
        module_id=MODULE_ID,
        destination=destination,
        document=document,
    )

    _run_systemctl("daemon-reload")

    if enable_at_startup:
        _run_systemctl("enable", destination.name)
    else:
        _run_systemctl(
            "disable",
            destination.name,
            allow_failure=True,
        )

    if start_immediately:
        _run_systemctl("restart", destination.name)

    actions: list[str] = [
        f"Installed {destination.name}",
        f"revision {result.revision}",
    ]

    if enable_at_startup:
        actions.append("enabled at startup")

    if start_immediately:
        actions.append("started")

    return ", ".join(actions) + "."


def remove_service(
    *,
    service_name: str,
    stop_service: bool,
    disable_at_startup: bool,
) -> str:
    service_name = _validate_service_name(service_name)
    unit_name = f"{service_name}.service"
    destination = SYSTEMD_DIRECTORY / unit_name

    if destination.is_symlink():
        raise ValueError(
            "LEC will not remove a service definition that is a symbolic link."
        )

    if not destination.is_file():
        raise ValueError(
            "The selected service does not have a removable definition "
            "under /etc/systemd/system."
        )

    if destination.parent.resolve() != SYSTEMD_DIRECTORY.resolve():
        raise ValueError("The service definition path is invalid.")

    if stop_service:
        _run_systemctl(
            "stop",
            unit_name,
            allow_failure=True,
        )

    if disable_at_startup:
        _run_systemctl(
            "disable",
            unit_name,
            allow_failure=True,
        )

    writer = ConfigurationWriter(
        backup_root=BACKUP_ROOT,
        audit_log=AuditLog(AUDIT_PATH),
    )

    result = writer.delete(
        module_id=MODULE_ID,
        destination=destination,
    )

    _run_systemctl("daemon-reload")
    _run_systemctl(
        "reset-failed",
        unit_name,
        allow_failure=True,
    )

    return (
        f"Removed {unit_name}. A verified backup was saved as "
        f"revision {result.revision}."
    )


def _validate_service_name(service_name: str) -> str:
    name = service_name.strip()

    if name.endswith(".service"):
        name = name.removesuffix(".service")

    if not _SERVICE_NAME_PATTERN.fullmatch(name):
        raise ValueError("The service name is invalid.")

    return name


def _run_systemctl(
    *arguments: str,
    allow_failure: bool = False,
) -> None:
    result = subprocess.run(
        ["systemctl", *arguments],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode == 0 or allow_failure:
        return

    message = (
        result.stderr.strip()
        or result.stdout.strip()
        or f"systemctl exited with code {result.returncode}"
    )

    raise RuntimeError(
        f"systemctl {' '.join(arguments)} failed:\n\n{message}"
    )


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage a service generated by Linux Easy Config."
    )

    parser.add_argument(
        "--source",
        type=Path,
    )
    parser.add_argument(
        "--service-name",
        required=True,
    )
    parser.add_argument(
        "--enable-at-startup",
        action="store_true",
    )
    parser.add_argument(
        "--start-immediately",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    arguments = _parse_arguments()

    if arguments.source is None:
        raise ValueError("--source is required when installing a service.")

    message = install_service(
        source=arguments.source,
        service_name=arguments.service_name,
        enable_at_startup=arguments.enable_at_startup,
        start_immediately=arguments.start_immediately,
    )

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
