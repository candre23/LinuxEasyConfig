from __future__ import annotations

from typing import Any

from linuxeasyconfig.core.privileged.arguments import required_string

from .manager import (
    create_hostname,
    delete_hostname,
    delete_provider_account,
    install_update_timer,
    list_provider_zones,
    save_provider_account,
    update_now,
)


def _save_provider(
    arguments: dict[str, Any],
) -> str:
    credentials = arguments.get("credentials")

    if not isinstance(credentials, dict):
        raise ValueError(
            "Provider credentials are missing."
        )

    return save_provider_account(
        original_id=str(
            arguments.get("original_id", "")
        ),
        provider_id=required_string(
            arguments,
            "provider_id",
        ),
        name=required_string(
            arguments,
            "name",
        ),
        credentials={
            str(key): str(value)
            for key, value in credentials.items()
        },
        enabled=bool(
            arguments.get("enabled", True)
        ),
    )


def _delete_provider(
    arguments: dict[str, Any],
) -> str:
    return delete_provider_account(
        account_id=required_string(
            arguments,
            "account_id",
        )
    )


def _list_zones(
    arguments: dict[str, Any],
) -> list[dict[str, str]]:
    return list_provider_zones(
        account_id=required_string(
            arguments,
            "account_id",
        )
    )


def _create_hostname(
    arguments: dict[str, Any],
) -> str:
    return create_hostname(
        account_id=required_string(
            arguments,
            "account_id",
        ),
        zone=required_string(
            arguments,
            "zone",
        ),
        hostname=required_string(
            arguments,
            "hostname",
        ),
        ipv4_enabled=bool(
            arguments.get(
                "ipv4_enabled",
                True,
            )
        ),
        ipv6_enabled=bool(
            arguments.get(
                "ipv6_enabled",
                False,
            )
        ),
        proxied=bool(
            arguments.get("proxied", False)
        ),
        owner_module_id=str(
            arguments.get(
                "owner_module_id",
                "",
            )
        ),
        owner_reference=str(
            arguments.get(
                "owner_reference",
                "",
            )
        ),
    )


def _delete_hostname(
    arguments: dict[str, Any],
) -> str:
    return delete_hostname(
        hostname_id=required_string(
            arguments,
            "hostname_id",
        ),
        delete_remote=bool(
            arguments.get(
                "delete_remote",
                False,
            )
        ),
    )


def _update_now(
    arguments: dict[str, Any],
) -> str:
    del arguments
    return update_now()


def _install_timer(
    arguments: dict[str, Any],
) -> str:
    del arguments
    return install_update_timer()


PRIVILEGED_TASKS = {
    "dynamic_dns.provider_save": _save_provider,
    "dynamic_dns.provider_delete": _delete_provider,
    "dynamic_dns.list_zones": _list_zones,
    "dynamic_dns.hostname_create": _create_hostname,
    "dynamic_dns.hostname_delete": _delete_hostname,
    "dynamic_dns.update_now": _update_now,
    "dynamic_dns.install_timer": _install_timer,
}
