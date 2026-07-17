from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

from .provider_registry import provider_metadata
from .storage import (
    load_public_hostnames,
    load_public_provider_accounts,
    load_status,
)


@dataclass(frozen=True)
class TimerStatus:
    installed: bool
    active: bool
    enabled: bool
    detail: str


class DynamicDNSRepository:
    def providers(self) -> list[Any]:
        return provider_metadata()

    def accounts(self) -> list[dict[str, Any]]:
        return load_public_provider_accounts()

    def hostnames(self) -> list[dict[str, Any]]:
        return load_public_hostnames()

    def status(self) -> dict[str, Any]:
        return load_status()

    def timer_status(self) -> TimerStatus:
        installed = (
            subprocess.run(
                [
                    "systemctl",
                    "list-unit-files",
                    "lec-dynamic-dns.timer",
                    "--no-legend",
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            ).returncode
            == 0
        )

        if not installed:
            return TimerStatus(
                installed=False,
                active=False,
                enabled=False,
                detail="Automatic update timer is not installed.",
            )

        active = subprocess.run(
            [
                "systemctl",
                "is-active",
                "--quiet",
                "lec-dynamic-dns.timer",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        ).returncode == 0

        enabled = subprocess.run(
            [
                "systemctl",
                "is-enabled",
                "--quiet",
                "lec-dynamic-dns.timer",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        ).returncode == 0

        detail_result = subprocess.run(
            [
                "systemctl",
                "status",
                "lec-dynamic-dns.timer",
                "--no-pager",
                "--lines",
                "0",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        return TimerStatus(
            installed=True,
            active=active,
            enabled=enabled,
            detail=(
                detail_result.stdout.strip()
                or detail_result.stderr.strip()
            ),
        )
