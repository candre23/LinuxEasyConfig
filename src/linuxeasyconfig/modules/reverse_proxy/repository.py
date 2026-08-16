from __future__ import annotations

import datetime as dt
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
class CertificateStatus:
    hostname: str
    available: bool
    issuer: str
    valid_from: str
    expires: str
    days_remaining: int | None
    serial_number: str
    status: str
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


    def certificates(self) -> list[CertificateStatus]:
        hostnames = sorted(
            {
                rule.public_host.strip().lower().rstrip(".")
                for rule in self.rules()
                if rule.enabled and rule.public_host.strip()
            }
        )

        if not hostnames:
            return []

        if shutil.which("openssl") is None:
            return [
                CertificateStatus(
                    hostname=hostname,
                    available=False,
                    issuer="",
                    valid_from="",
                    expires="",
                    days_remaining=None,
                    serial_number="",
                    status="OpenSSL unavailable",
                    detail=(
                        "The openssl command is not installed, so "
                        "certificate details could not be read."
                    ),
                )
                for hostname in hostnames
            ]

        return [
            _certificate_status(hostname)
            for hostname in hostnames
        ]

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
        try:
            lines = ACCESS_LOG.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        except OSError as exc:
            raise RuntimeError(
                f"Could not read {ACCESS_LOG}: {exc}"
            ) from exc

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


def _certificate_status(
    hostname: str,
) -> CertificateStatus:
    connection = subprocess.run(
        [
            "openssl",
            "s_client",
            "-connect",
            "127.0.0.1:443",
            "-servername",
            hostname,
            "-showcerts",
        ],
        input="",
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    combined = (
        connection.stdout
        + "\n"
        + connection.stderr
    )
    certificate = _first_pem_certificate(combined)

    if not certificate:
        detail = (
            connection.stderr.strip()
            or connection.stdout.strip()
            or "Caddy did not present a certificate."
        )
        return CertificateStatus(
            hostname=hostname,
            available=False,
            issuer="",
            valid_from="",
            expires="",
            days_remaining=None,
            serial_number="",
            status="Not available",
            detail=detail,
        )

    inspection = subprocess.run(
        [
            "openssl",
            "x509",
            "-noout",
            "-issuer",
            "-startdate",
            "-enddate",
            "-serial",
        ],
        input=certificate,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    if inspection.returncode != 0:
        return CertificateStatus(
            hostname=hostname,
            available=False,
            issuer="",
            valid_from="",
            expires="",
            days_remaining=None,
            serial_number="",
            status="Could not inspect",
            detail=(
                inspection.stderr.strip()
                or "OpenSSL could not inspect the certificate."
            ),
        )

    values: dict[str, str] = {}

    for raw_line in inspection.stdout.splitlines():
        key, separator, value = raw_line.partition("=")

        if separator:
            values[key.strip()] = value.strip()

    issuer = values.get("issuer", "")
    valid_from = values.get("notBefore", "")
    expires = values.get("notAfter", "")
    serial = values.get("serial", "")
    days_remaining = _days_until(expires)

    if days_remaining is None:
        status = "Available"
    elif days_remaining < 0:
        status = "Expired"
    elif days_remaining <= 14:
        status = "Expires soon"
    else:
        status = "Valid"

    return CertificateStatus(
        hostname=hostname,
        available=True,
        issuer=issuer,
        valid_from=valid_from,
        expires=expires,
        days_remaining=days_remaining,
        serial_number=serial,
        status=status,
        detail=(
            "Certificate currently presented by Caddy on "
            f"127.0.0.1:443 for SNI hostname {hostname}."
        ),
    )


def _first_pem_certificate(
    value: str,
) -> str:
    begin = "-----BEGIN CERTIFICATE-----"
    end = "-----END CERTIFICATE-----"
    start = value.find(begin)

    if start < 0:
        return ""

    finish = value.find(end, start)

    if finish < 0:
        return ""

    finish += len(end)
    return value[start:finish] + "\n"


def _days_until(
    openssl_date: str,
) -> int | None:
    if not openssl_date:
        return None

    try:
        expires = dt.datetime.strptime(
            openssl_date,
            "%b %d %H:%M:%S %Y %Z",
        ).replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None

    now = dt.datetime.now(dt.timezone.utc)
    return (expires - now).days
