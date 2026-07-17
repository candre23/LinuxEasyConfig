from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CONFIG_DIR = Path(
    "/etc/linuxeasyconfig/dynamic_dns"
)
PROVIDERS_PATH = CONFIG_DIR / "providers.json"
PROVIDERS_PUBLIC_PATH = Path(
    "/var/lib/linuxeasyconfig/dynamic-dns/providers.json"
)
HOSTNAMES_PATH = CONFIG_DIR / "hostnames.json"
HOSTNAMES_PUBLIC_PATH = Path(
    "/var/lib/linuxeasyconfig/dynamic-dns/hostnames.json"
)
STATUS_PATH = Path(
    "/var/lib/linuxeasyconfig/dynamic-dns/status.json"
)


@dataclass
class ProviderAccount:
    id: str
    provider_id: str
    name: str
    credentials: dict[str, str]
    enabled: bool = True


@dataclass
class ManagedHostname:
    id: str
    provider_account_id: str
    zone: str
    hostname: str
    ipv4_enabled: bool = True
    ipv6_enabled: bool = False
    proxied: bool = False
    enabled: bool = True
    owner_module_id: str = ""
    owner_reference: str = ""


def load_provider_accounts() -> list[ProviderAccount]:
    return [
        ProviderAccount(**item)
        for item in _load_list(PROVIDERS_PATH)
    ]


def save_provider_accounts(
    values: list[ProviderAccount],
) -> None:
    _save(
        PROVIDERS_PATH,
        [asdict(item) for item in values],
        mode=0o600,
    )
    _save(
        PROVIDERS_PUBLIC_PATH,
        [
            {
                "id": item.id,
                "provider_id": item.provider_id,
                "name": item.name,
                "enabled": item.enabled,
            }
            for item in values
        ],
        mode=0o644,
    )


def load_hostnames() -> list[ManagedHostname]:
    return [
        ManagedHostname(**item)
        for item in _load_list(HOSTNAMES_PATH)
    ]


def save_hostnames(
    values: list[ManagedHostname],
) -> None:
    _save(
        HOSTNAMES_PATH,
        [asdict(item) for item in values],
        mode=0o600,
    )
    _save(
        HOSTNAMES_PUBLIC_PATH,
        [asdict(item) for item in values],
        mode=0o644,
    )


def load_status() -> dict[str, Any]:
    if not STATUS_PATH.is_file():
        return {}

    try:
        value = json.loads(
            STATUS_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        return {}

    return value if isinstance(value, dict) else {}


def save_status(value: dict[str, Any]) -> None:
    _save(
        STATUS_PATH,
        value,
        mode=0o644,
    )


def public_provider_accounts() -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "provider_id": item.provider_id,
            "name": item.name,
            "enabled": item.enabled,
        }
        for item in load_provider_accounts()
    ]



def load_public_provider_accounts() -> list[dict[str, Any]]:
    return _load_list(PROVIDERS_PUBLIC_PATH)


def load_public_hostnames() -> list[dict[str, Any]]:
    return _load_list(HOSTNAMES_PUBLIC_PATH)

def _load_list(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(value, list):
        return []

    return [
        item
        for item in value
        if isinstance(item, dict)
    ]


def _save(
    path: Path,
    value: Any,
    *,
    mode: int,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.parent.chmod(0o755)

    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.chmod(mode)
    temporary.replace(path)
    path.chmod(mode)
