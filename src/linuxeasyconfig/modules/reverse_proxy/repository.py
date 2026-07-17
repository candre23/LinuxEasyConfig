from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
import json
from pathlib import Path

from .storage import (
    ProtectionSettings,
    ProxyCredential,
    ProxyRule,
    load_credentials,
    load_rules,
    load_settings,
)


CADDYFILE = Path("/etc/caddy/Caddyfile")
LEC_CADDY_DIR = Path("/etc/caddy/lec")
FAIL2BAN_FILTER = Path(
    "/etc/fail2ban/filter.d/lec-caddy-auth.conf"
)
FAIL2BAN_JAIL = Path(
    "/etc/fail2ban/jail.d/lec-caddy-auth.local"
)
ACCESS_LOG = Path(
    "/var/log/caddy/lec-access.json"
)
DYNAMIC_DNS_HOSTNAMES = Path(
    "/var/lib/linuxeasyconfig/dynamic-dns/hostnames.json"
)


@dataclass(frozen=True)
class ServiceState:
    installed: bool
    active: bool
    enabled: bool
    version: str
    detail: str


@dataclass(frozen=True)
class ReverseProxyStatus:
    caddy: ServiceState
    fail2ban: ServiceState
    caddy_config_valid: bool
    caddy_config_detail: str
    fail2ban_config_valid: bool
    fail2ban_config_detail: str
    lec_setup_complete: bool


class ReverseProxyRepository:
    def status(self) -> ReverseProxyStatus:
        caddy = _service_state(
            command="caddy",
            service="caddy",
            version_command=[
                "caddy",
                "version",
            ],
        )
        fail2ban = _service_state(
            command="fail2ban-client",
            service="fail2ban",
            version_command=[
                "fail2ban-client",
                "--version",
            ],
        )

        caddy_valid, caddy_detail = (
            self._check_caddy_config(caddy.installed)
        )
        fail2ban_valid, fail2ban_detail = (
            self._check_fail2ban_config(
                fail2ban.installed,
                fail2ban.active,
            )
        )

        setup_complete = (
            caddy.installed
            and fail2ban.installed
            and CADDYFILE.is_file()
            and LEC_CADDY_DIR.is_dir()
            and FAIL2BAN_FILTER.is_file()
            and FAIL2BAN_JAIL.is_file()
        )

        return ReverseProxyStatus(
            caddy=caddy,
            fail2ban=fail2ban,
            caddy_config_valid=caddy_valid,
            caddy_config_detail=caddy_detail,
            fail2ban_config_valid=fail2ban_valid,
            fail2ban_config_detail=fail2ban_detail,
            lec_setup_complete=setup_complete,
        )


    def credentials(self) -> list[ProxyCredential]:
        return load_credentials()

    def rules(self) -> list[ProxyRule]:
        return load_rules()

    def protection_settings(self) -> ProtectionSettings:
        return load_settings()

    def dynamic_dns_hostnames(self) -> list[str]:
        if not DYNAMIC_DNS_HOSTNAMES.is_file():
            return []

        try:
            value = json.loads(
                DYNAMIC_DNS_HOSTNAMES.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(value, list):
            return []

        hostnames: set[str] = set()

        for item in value:
            if not isinstance(item, dict):
                continue

            if not bool(item.get("enabled", True)):
                continue

            hostname = str(
                item.get("hostname", "")
            ).strip().lower().rstrip(".")

            if hostname:
                hostnames.add(hostname)

        return sorted(hostnames)

    def recent_activity(
        self,
        *,
        maximum_lines: int = 300,
    ) -> list[str]:
        if not ACCESS_LOG.exists():
            return []

        try:
            lines = ACCESS_LOG.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        except OSError:
            return []

        return lines[-maximum_lines:]

    def banned_addresses(self) -> list[str]:
        if shutil.which("fail2ban-client") is None:
            return []

        result = subprocess.run(
            [
                "fail2ban-client",
                "status",
                "lec-caddy-auth",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if result.returncode != 0:
            return []

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()

            if "Banned IP list:" not in line:
                continue

            _, _, values = line.partition(
                "Banned IP list:"
            )
            return [
                value
                for value in values.split()
                if value
            ]

        return []

    @staticmethod
    def _check_caddy_config(
        installed: bool,
    ) -> tuple[bool, str]:
        if not installed:
            return False, "Caddy is not installed."

        if not CADDYFILE.is_file():
            return False, (
                "/etc/caddy/Caddyfile does not exist."
            )

        result = subprocess.run(
            [
                "caddy",
                "adapt",
                "--config",
                str(CADDYFILE),
                "--adapter",
                "caddyfile",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            return True, "Configuration syntax is valid."

        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Configuration syntax check failed."
        )
        return False, detail

    @staticmethod
    def _check_fail2ban_config(
        installed: bool,
        active: bool,
    ) -> tuple[bool, str]:
        if not installed:
            return False, "Fail2Ban is not installed."

        if not FAIL2BAN_FILTER.is_file():
            return False, (
                "The LEC Caddy protection filter is missing."
            )

        if not FAIL2BAN_JAIL.is_file():
            return False, (
                "The LEC Caddy protection settings are missing."
            )

        if active:
            return True, (
                "Configuration is loaded by the running service."
            )

        return False, (
            "Configuration files are present, but Fail2Ban "
            "is not running."
        )


def _service_state(
    *,
    command: str,
    service: str,
    version_command: list[str],
) -> ServiceState:
    installed = shutil.which(command) is not None

    if not installed:
        return ServiceState(
            installed=False,
            active=False,
            enabled=False,
            version="Not installed",
            detail="Package is not installed.",
        )

    active_result = subprocess.run(
        [
            "systemctl",
            "is-active",
            service,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    enabled_result = subprocess.run(
        [
            "systemctl",
            "is-enabled",
            service,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    version_result = subprocess.run(
        version_command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    version = (
        version_result.stdout.strip()
        or version_result.stderr.strip()
        or "Installed"
    )

    return ServiceState(
        installed=True,
        active=active_result.returncode == 0,
        enabled=enabled_result.returncode == 0,
        version=version,
        detail=(
            active_result.stdout.strip()
            or active_result.stderr.strip()
            or "Unknown"
        ),
    )
