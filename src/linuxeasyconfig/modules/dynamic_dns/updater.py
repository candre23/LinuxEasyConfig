from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import urllib.error
import urllib.request
from typing import Any

from .provider_registry import get_provider
from .storage import (
    ManagedHostname,
    ProviderAccount,
    load_hostnames,
    load_provider_accounts,
    load_status,
    save_status,
)


PUBLIC_IPV4_URLS = (
    "https://api.ipify.org",
    "https://ipv4.icanhazip.com",
)
PUBLIC_IPV6_URLS = (
    "https://api64.ipify.org",
    "https://ipv6.icanhazip.com",
)

MAX_PROVIDER_SYNC_AGE = dt.timedelta(days=7)


def update_all(
    *,
    force: bool = False,
) -> dict[str, Any]:
    accounts = {
        item.id: item
        for item in load_provider_accounts()
        if item.enabled
    }
    hostnames = [
        item
        for item in load_hostnames()
        if item.enabled
    ]

    previous_status = load_status()
    previous_ipv4 = str(
        previous_status.get("public_ipv4", "")
    )
    previous_ipv6 = str(
        previous_status.get("public_ipv6", "")
    )
    previous_provider_sync = _parse_timestamp(
        previous_status.get("last_provider_sync", "")
    )
    now = dt.datetime.now(dt.timezone.utc)
    periodic_sync_due = (
        previous_provider_sync is None
        or now - previous_provider_sync >= MAX_PROVIDER_SYNC_AGE
    )

    need_ipv6 = any(
        item.ipv6_enabled
        for item in hostnames
    )

    # Always detect IPv4 so the Overview page can report the
    # machine's public address before any hostname is created.
    ipv4 = detect_public_ip(4)

    # IPv6 is optional on many home connections. When no managed
    # hostname requires it, detection is best-effort and must not
    # make an otherwise healthy updater run fail.
    if need_ipv6:
        ipv6 = detect_public_ip(6)
    else:
        try:
            ipv6 = detect_public_ip(6)
        except RuntimeError:
            ipv6 = ""

    address_changed = (
        ipv4 != previous_ipv4
        or ipv6 != previous_ipv6
    )

    timestamp = now.isoformat()
    record_results: list[dict[str, Any]] = []
    errors: list[str] = []
    provider_sync_attempted = False
    provider_sync_succeeded = False

    for hostname in hostnames:
        account = accounts.get(
            hostname.provider_account_id
        )

        if account is None:
            error = (
                f"{hostname.hostname}: provider account "
                "is missing or disabled."
            )
            errors.append(error)
            record_results.append(
                _record_result(
                    hostname,
                    success=False,
                    message=error,
                )
            )
            continue

        if (
            not force
            and not address_changed
            and not periodic_sync_due
        ):
            record_results.append(
                _record_result(
                    hostname,
                    success=True,
                    message=(
                        "No public IP change detected and the "
                        "weekly provider sync is not yet due."
                    ),
                )
            )
            continue

        provider_sync_attempted = True

        try:
            provider = get_provider(
                account.provider_id
            )
            provider.update_hostname(
                credentials=account.credentials,
                zone=hostname.zone,
                hostname=hostname.hostname,
                ipv4=(
                    ipv4
                    if hostname.ipv4_enabled
                    else ""
                ),
                ipv6=(
                    ipv6
                    if hostname.ipv6_enabled
                    else ""
                ),
                proxied=hostname.proxied,
            )
        except Exception as exc:
            message = str(exc)
            errors.append(
                f"{hostname.hostname}: {message}"
            )
            record_results.append(
                _record_result(
                    hostname,
                    success=False,
                    message=message,
                )
            )
        else:
            provider_sync_succeeded = True
            record_results.append(
                _record_result(
                    hostname,
                    success=True,
                    message=(
                        "DNS record synchronized."
                        if periodic_sync_due and not address_changed
                        else "DNS record updated."
                    ),
                )
            )

    status = {
        "last_run": timestamp,
        "last_success": (
            timestamp
            if not errors
            else previous_status.get(
                "last_success",
                "",
            )
        ),
        "public_ipv4": ipv4,
        "public_ipv6": ipv6,
        "address_changed": address_changed,
        "periodic_sync_due": periodic_sync_due,
        "last_provider_sync": (
            timestamp
            if provider_sync_attempted
            and provider_sync_succeeded
            and not errors
            else previous_status.get("last_provider_sync", "")
        ),
        "success": not errors,
        "errors": errors,
        "records": record_results,
    }
    save_status(status)
    return status



def _parse_timestamp(
    value: Any,
) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = dt.datetime.fromisoformat(value.strip())
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)

    return parsed.astimezone(dt.timezone.utc)

def detect_public_ip(version: int) -> str:
    urls = (
        PUBLIC_IPV4_URLS
        if version == 4
        else PUBLIC_IPV6_URLS
    )
    errors: list[str] = []

    for url in urls:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "LinuxEasyConfig/0.1",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=15,
            ) as response:
                value = response.read().decode(
                    "utf-8",
                    errors="replace",
                ).strip()
            address = ipaddress.ip_address(value)

            if address.version != version:
                raise ValueError(
                    "Address family did not match."
                )

            return str(address)
        except (
            OSError,
            ValueError,
            urllib.error.URLError,
        ) as exc:
            errors.append(str(exc))

    raise RuntimeError(
        f"Could not determine public IPv{version}: "
        + "; ".join(errors)
    )


def _record_result(
    hostname: ManagedHostname,
    *,
    success: bool,
    message: str,
) -> dict[str, Any]:
    return {
        "id": hostname.id,
        "hostname": hostname.hostname,
        "success": success,
        "message": message,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
    )
    arguments = parser.parse_args()

    try:
        status = update_all(
            force=arguments.force
        )
    except Exception as exc:
        save_status(
            {
                "last_run": dt.datetime.now(
                    dt.timezone.utc
                ).isoformat(),
                "success": False,
                "errors": [str(exc)],
                "records": [],
            }
        )
        raise

    print(json.dumps(status, indent=2))
    return 0 if status["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
