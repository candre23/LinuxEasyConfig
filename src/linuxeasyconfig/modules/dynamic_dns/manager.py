from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
from urllib.parse import urlsplit
from pathlib import Path
from typing import Any

from linuxeasyconfig.core.config.managed import write_text

from .provider_registry import get_provider
from .storage import (
    ManagedHostname,
    ProviderAccount,
    load_hostnames,
    load_provider_accounts,
    save_hostnames,
    save_provider_accounts,
)
from .updater import update_all


MODULE_ID = "org.linuxeasyconfig.dynamic_dns"
SERVICE_PATH = Path(
    "/etc/systemd/system/lec-dynamic-dns.service"
)
TIMER_PATH = Path(
    "/etc/systemd/system/lec-dynamic-dns.timer"
)

_HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
    r"[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
    r"[A-Za-z0-9])?$"
)


def save_provider_account(
    *,
    original_id: str,
    provider_id: str,
    name: str,
    credentials: dict[str, str],
    enabled: bool,
) -> str:
    provider = get_provider(provider_id)
    name = name.strip()

    if not name:
        raise ValueError(
            "Provider account name is required."
        )

    cleaned_credentials = {
        str(key): str(value).strip()
        for key, value in credentials.items()
    }

    accounts = load_provider_accounts()
    existing = next(
        (
            item
            for item in accounts
            if item.id == original_id
        ),
        None,
    )

    if existing is not None:
        for field in provider.metadata.fields:
            if (
                not cleaned_credentials.get(
                    field.id,
                    ""
                )
                and existing.provider_id == provider_id
            ):
                cleaned_credentials[field.id] = (
                    existing.credentials.get(
                        field.id,
                        "",
                    )
                )

    provider.test_credentials(
        cleaned_credentials
    )

    account = ProviderAccount(
        id=(
            existing.id
            if existing is not None
            else uuid.uuid4().hex
        ),
        provider_id=provider_id,
        name=name,
        credentials=cleaned_credentials,
        enabled=enabled,
    )

    accounts = [
        item
        for item in accounts
        if item.id != account.id
    ]
    accounts.append(account)
    save_provider_accounts(accounts)
    install_update_timer()

    return (
        f"Dynamic DNS provider account {name} was saved."
    )


def delete_provider_account(
    *,
    account_id: str,
) -> str:
    hostnames = load_hostnames()

    if any(
        item.provider_account_id == account_id
        for item in hostnames
    ):
        raise ValueError(
            "This provider account is still used by one or "
            "more managed hostnames."
        )

    accounts = load_provider_accounts()
    updated = [
        item
        for item in accounts
        if item.id != account_id
    ]

    if len(updated) == len(accounts):
        raise ValueError(
            "Provider account was not found."
        )

    save_provider_accounts(updated)
    return "Dynamic DNS provider account was removed."


def list_provider_zones(
    *,
    account_id: str,
) -> list[dict[str, str]]:
    account = _account(account_id)
    provider = get_provider(
        account.provider_id
    )
    return provider.list_zones(
        account.credentials
    )


def create_hostname(
    *,
    account_id: str,
    zone: str,
    hostname: str,
    ipv4_enabled: bool,
    ipv6_enabled: bool,
    proxied: bool,
    owner_module_id: str,
    owner_reference: str,
) -> str:
    zone = _normalize_hostname_input(
        zone,
        field_name="DNS zone",
    )
    hostname = _normalize_hostname_input(
        hostname,
        field_name="hostname",
    )

    # Accept either a complete hostname or a simple subdomain label.
    # The UI asks for the complete hostname, but accepting "files"
    # makes the form more forgiving for novice users.
    if "." not in hostname:
        hostname = f"{hostname}.{zone}"

    if not _HOSTNAME_PATTERN.fullmatch(hostname):
        raise ValueError(
            "Enter a valid hostname, such as "
            f"files.{zone}. Do not include https://, a port, "
            "a path, or spaces."
        )

    if not (
        hostname == zone
        or hostname.endswith("." + zone)
    ):
        raise ValueError(
            f"The hostname must be inside the DNS zone {zone}. "
            f"For example: files.{zone}"
        )

    if not ipv4_enabled and not ipv6_enabled:
        raise ValueError(
            "Enable IPv4, IPv6, or both."
        )

    account = _account(account_id)
    provider = get_provider(
        account.provider_id
    )

    from .updater import detect_public_ip

    ipv4 = (
        detect_public_ip(4)
        if ipv4_enabled
        else ""
    )
    ipv6 = (
        detect_public_ip(6)
        if ipv6_enabled
        else ""
    )

    provider.ensure_hostname(
        credentials=account.credentials,
        zone=zone,
        hostname=hostname,
        ipv4=ipv4,
        ipv6=ipv6,
        proxied=proxied,
    )

    values = [
        item
        for item in load_hostnames()
        if item.hostname != hostname
    ]
    values.append(
        ManagedHostname(
            id=uuid.uuid4().hex,
            provider_account_id=account_id,
            zone=zone,
            hostname=hostname,
            ipv4_enabled=ipv4_enabled,
            ipv6_enabled=ipv6_enabled,
            proxied=proxied,
            enabled=True,
            owner_module_id=owner_module_id,
            owner_reference=owner_reference,
        )
    )
    save_hostnames(values)
    install_update_timer()
    update_all(force=True)

    return f"Dynamic hostname {hostname} was created."


def delete_hostname(
    *,
    hostname_id: str,
    delete_remote: bool,
) -> str:
    values = load_hostnames()
    item = next(
        (
            value
            for value in values
            if value.id == hostname_id
        ),
        None,
    )

    if item is None:
        raise ValueError(
            "Managed hostname was not found."
        )

    if delete_remote:
        account = _account(
            item.provider_account_id
        )
        provider = get_provider(
            account.provider_id
        )
        provider.delete_hostname(
            credentials=account.credentials,
            zone=item.zone,
            hostname=item.hostname,
        )

    save_hostnames(
        [
            value
            for value in values
            if value.id != hostname_id
        ]
    )

    return f"Stopped managing {item.hostname}."


def update_now() -> str:
    status = update_all(force=True)

    if not status.get("success", False):
        raise RuntimeError(
            "\n".join(
                status.get(
                    "errors",
                    ["Dynamic DNS update failed."],
                )
            )
        )

    return "Dynamic DNS records were updated."


def install_update_timer() -> str:
    interpreter = Path(sys.executable).resolve()
    updater = Path(__file__).with_name(
        "updater.py"
    ).resolve()
    package_root = updater.parents[3]

    write_text(
        module_id=MODULE_ID,
        destination=SERVICE_PATH,
        text=(
            "[Unit]\n"
            "Description=Linux Easy Config Dynamic DNS update\n"
            "Wants=network-online.target\n"
            "After=network-online.target\n\n"
            "[Service]\n"
            "Type=oneshot\n"
            f"Environment=PYTHONPATH={package_root}\n"
            f"ExecStart={interpreter} -m "
            "linuxeasyconfig.modules.dynamic_dns.updater\n"
        ),
        mode=0o644,
    )

    write_text(
        module_id=MODULE_ID,
        destination=TIMER_PATH,
        text=(
            "[Unit]\n"
            "Description=Run Linux Easy Config Dynamic DNS updates\n\n"
            "[Timer]\n"
            "OnBootSec=2min\n"
            "OnUnitActiveSec=5min\n"
            "Persistent=true\n"
            "RandomizedDelaySec=30\n\n"
            "[Install]\n"
            "WantedBy=timers.target\n"
        ),
        mode=0o644,
    )

    _run(
        ["systemctl", "daemon-reload"]
    )
    _run(
        [
            "systemctl",
            "enable",
            "--now",
            "lec-dynamic-dns.timer",
        ]
    )

    return (
        "Dynamic DNS automatic updates are installed "
        "and scheduled every five minutes."
    )



def _normalize_hostname_input(
    value: str,
    *,
    field_name: str,
) -> str:
    normalized = value.strip().lower()

    if not normalized:
        raise ValueError(
            f"{field_name} is required."
        )

    # Be forgiving when a user pastes a URL rather than a hostname.
    if "://" in normalized:
        parsed = urlsplit(normalized)
        normalized = parsed.hostname or ""
    else:
        # Reject ports and paths while producing a clearer message.
        normalized = normalized.rstrip(".")

    if (
        not normalized
        or "/" in normalized
        or ":" in normalized
        or any(character.isspace() for character in normalized)
    ):
        raise ValueError(
            f"{field_name} must contain only a DNS name. "
            "Do not include a port, path, or spaces."
        )

    return normalized.rstrip(".")

def _account(
    account_id: str,
) -> ProviderAccount:
    account = next(
        (
            item
            for item in load_provider_accounts()
            if item.id == account_id
        ),
        None,
    )

    if account is None:
        raise ValueError(
            "Provider account was not found."
        )

    return account


def _run(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"{' '.join(command)} failed."
        )
