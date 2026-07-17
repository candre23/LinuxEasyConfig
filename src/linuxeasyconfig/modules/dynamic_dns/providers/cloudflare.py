from __future__ import annotations

from typing import Any

from .base import ProviderField, ProviderMetadata
from .http import query_string, request_json


API = "https://api.cloudflare.com/client/v4"


class Provider:
    metadata = ProviderMetadata(
        id="cloudflare",
        name="Cloudflare",
        description=(
            "DNS hosting for domains already added to a "
            "Cloudflare account."
        ),
        homepage="https://www.cloudflare.com/",
        fields=(
            ProviderField(
                id="token",
                label="API token",
                field_type="password",
                help=(
                    "Use a token limited to Zone DNS Read and "
                    "Zone DNS Edit for the intended zones."
                ),
            ),
        ),
        supports_hostname_creation=True,
    )

    def test_credentials(
        self,
        credentials: dict[str, str],
    ) -> str:
        zones = self.list_zones(credentials)
        return (
            f"Connected to Cloudflare. "
            f"{len(zones)} zone(s) available."
        )

    def list_zones(
        self,
        credentials: dict[str, str],
    ) -> list[dict[str, str]]:
        value = _request(
            credentials,
            f"{API}/zones?per_page=50",
        )
        result = value.get("result", [])

        if not isinstance(result, list):
            raise RuntimeError(
                "Cloudflare returned an unexpected zone list."
            )

        return [
            {
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "")),
            }
            for item in result
            if isinstance(item, dict)
            and item.get("id")
            and item.get("name")
        ]

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
        zone_id = self._zone_id(credentials, zone)

        for record_type, value in (
            ("A", ipv4),
            ("AAAA", ipv6),
        ):
            self._upsert_record(
                credentials=credentials,
                zone_id=zone_id,
                hostname=hostname,
                record_type=record_type,
                value=value,
                proxied=proxied,
            )

        return {
            "hostname": hostname,
            "zone": zone,
            "zone_id": zone_id,
        }

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
        zone_id = self._zone_id(credentials, zone)

        for record_type in ("A", "AAAA"):
            record = self._find_record(
                credentials,
                zone_id,
                hostname,
                record_type,
            )

            if record is None:
                continue

            _request(
                credentials,
                (
                    f"{API}/zones/{zone_id}/dns_records/"
                    f"{record['id']}"
                ),
                method="DELETE",
            )

        return f"Removed {hostname} from Cloudflare."

    def _zone_id(
        self,
        credentials: dict[str, str],
        zone: str,
    ) -> str:
        value = _request(
            credentials,
            (
                f"{API}/zones?"
                + query_string(
                    {
                        "name": zone,
                        "status": "active",
                    }
                )
            ),
        )
        result = value.get("result", [])

        if (
            not isinstance(result, list)
            or not result
            or not isinstance(result[0], dict)
        ):
            raise ValueError(
                f"Cloudflare zone {zone} was not found."
            )

        return str(result[0]["id"])

    def _find_record(
        self,
        credentials: dict[str, str],
        zone_id: str,
        hostname: str,
        record_type: str,
    ) -> dict[str, Any] | None:
        value = _request(
            credentials,
            (
                f"{API}/zones/{zone_id}/dns_records?"
                + query_string(
                    {
                        "name": hostname,
                        "type": record_type,
                    }
                )
            ),
        )
        result = value.get("result", [])

        if isinstance(result, list) and result:
            item = result[0]
            return item if isinstance(item, dict) else None

        return None

    def _upsert_record(
        self,
        *,
        credentials: dict[str, str],
        zone_id: str,
        hostname: str,
        record_type: str,
        value: str,
        proxied: bool,
    ) -> None:
        existing = self._find_record(
            credentials,
            zone_id,
            hostname,
            record_type,
        )

        if not value:
            if existing is not None:
                _request(
                    credentials,
                    (
                        f"{API}/zones/{zone_id}/dns_records/"
                        f"{existing['id']}"
                    ),
                    method="DELETE",
                )
            return

        payload = {
            "type": record_type,
            "name": hostname,
            "content": value,
            "ttl": 1,
            "proxied": proxied,
            "comment": "Managed by Linux Easy Config",
        }

        if existing is None:
            _request(
                credentials,
                f"{API}/zones/{zone_id}/dns_records",
                method="POST",
                payload=payload,
            )
        else:
            _request(
                credentials,
                (
                    f"{API}/zones/{zone_id}/dns_records/"
                    f"{existing['id']}"
                ),
                method="PUT",
                payload=payload,
            )


def _request(
    credentials: dict[str, str],
    url: str,
    *,
    method: str = "GET",
    payload: Any = None,
) -> dict[str, Any]:
    token = credentials.get("token", "").strip()

    if not token:
        raise ValueError(
            "A Cloudflare API token is required."
        )

    value = request_json(
        url=url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
        },
        payload=payload,
    )

    if not isinstance(value, dict):
        raise RuntimeError(
            "Cloudflare returned an unexpected response."
        )

    if not value.get("success", False):
        raise RuntimeError(
            "Cloudflare API operation failed: "
            + str(value.get("errors", value))
        )

    return value
