from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderField:
    id: str
    label: str
    field_type: str = "text"
    required: bool = True
    help: str = ""
    placeholder: str = ""


@dataclass(frozen=True)
class ProviderMetadata:
    id: str
    name: str
    description: str
    homepage: str
    fields: tuple[ProviderField, ...]
    supports_hostname_creation: bool
    supports_ipv4: bool = True
    supports_ipv6: bool = True


class DynamicDNSProvider(Protocol):
    metadata: ProviderMetadata

    def test_credentials(
        self,
        credentials: dict[str, str],
    ) -> str:
        ...

    def list_zones(
        self,
        credentials: dict[str, str],
    ) -> list[dict[str, str]]:
        ...

    def ensure_hostname(
        self,
        *,
        credentials: dict[str, str],
        zone: str,
        hostname: str,
        ipv4: str,
        ipv6: str,
        proxied: bool,
    ) -> dict[str, Any]:
        ...

    def delete_hostname(
        self,
        *,
        credentials: dict[str, str],
        zone: str,
        hostname: str,
    ) -> str:
        ...

    def update_hostname(
        self,
        *,
        credentials: dict[str, str],
        zone: str,
        hostname: str,
        ipv4: str,
        ipv6: str,
        proxied: bool,
    ) -> dict[str, Any]:
        ...
