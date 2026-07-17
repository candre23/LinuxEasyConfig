from __future__ import annotations

from typing import Any

from linuxeasyconfig.modules.dynamic_dns.providers.base import (
    ProviderField,
    ProviderMetadata,
)


class Provider:
    metadata = ProviderMetadata(
        id="example",
        name="Example Provider",
        description="Template for a third-party Dynamic DNS provider.",
        homepage="https://example.com/",
        fields=(
            ProviderField(
                id="token",
                label="API token",
                field_type="password",
            ),
        ),
        supports_hostname_creation=True,
    )

    def test_credentials(
        self,
        credentials: dict[str, str],
    ) -> str:
        raise NotImplementedError

    def list_zones(
        self,
        credentials: dict[str, str],
    ) -> list[dict[str, str]]:
        raise NotImplementedError

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
        raise NotImplementedError

    def update_hostname(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.ensure_hostname(**kwargs)

    def delete_hostname(
        self,
        *,
        credentials: dict[str, str],
        zone: str,
        hostname: str,
    ) -> str:
        raise NotImplementedError
