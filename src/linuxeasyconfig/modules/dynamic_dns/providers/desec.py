from __future__ import annotations

from typing import Any

from .base import ProviderField, ProviderMetadata
from .http import request_json


API = "https://desec.io/api/v1"


class Provider:
    metadata = ProviderMetadata(
        id="desec",
        name="deSEC",
        description=(
            "Free nonprofit DNS hosting with API-managed zones "
            "and dynamic A/AAAA records."
        ),
        homepage="https://desec.io/",
        fields=(
            ProviderField(
                id="token",
                label="API token",
                field_type="password",
                help=(
                    "Use a long-lived deSEC API token with access "
                    "to the zones and records LEC should manage."
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
            f"Connected to deSEC. "
            f"{len(zones)} zone(s) available."
        )

    def list_zones(
        self,
        credentials: dict[str, str],
    ) -> list[dict[str, str]]:
        value = request_json(
            url=f"{API}/domains/",
            headers=_headers(credentials),
        )

        if not isinstance(value, list):
            raise RuntimeError(
                "deSEC returned an unexpected zone list."
            )

        result: list[dict[str, str]] = []

        for item in value:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if name:
                result.append(
                    {
                        "id": name,
                        "name": name,
                    }
                )

        return result

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
        del proxied
        self._upsert_rrset(
            credentials=credentials,
            zone=zone,
            hostname=hostname,
            record_type="A",
            value=ipv4,
        )
        self._upsert_rrset(
            credentials=credentials,
            zone=zone,
            hostname=hostname,
            record_type="AAAA",
            value=ipv6,
        )
        return {
            "hostname": hostname,
            "zone": zone,
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
        subname = _subname(zone, hostname)

        for record_type in ("A", "AAAA"):
            request_json(
                url=(
                    f"{API}/domains/{zone}/rrsets/"
                    f"{subname}/{record_type}/"
                ),
                method="DELETE",
                headers=_headers(credentials),
            )

        return f"Removed {hostname} from deSEC."

    def _upsert_rrset(
        self,
        *,
        credentials: dict[str, str],
        zone: str,
        hostname: str,
        record_type: str,
        value: str,
    ) -> None:
        subname = _subname(zone, hostname)
        url = (
            f"{API}/domains/{zone}/rrsets/"
            f"{subname}/{record_type}/"
        )

        if not value:
            try:
                request_json(
                    url=url,
                    method="DELETE",
                    headers=_headers(credentials),
                )
            except RuntimeError as exc:
                if "404" not in str(exc):
                    raise
            return

        payload = {
            "subname": subname,
            "type": record_type,
            "ttl": 3600,
            "records": [value],
        }

        try:
            request_json(
                url=url,
                method="GET",
                headers=_headers(credentials),
            )
        except RuntimeError as exc:
            if "HTTP 404" not in str(exc):
                raise

            # A specific-RRset PUT only replaces an existing RRset.
            # New RRsets must be created through the zone collection.
            request_json(
                url=(
                    f"{API}/domains/{zone}/rrsets/"
                ),
                method="POST",
                headers=_headers(credentials),
                payload=payload,
            )
        else:
            request_json(
                url=url,
                method="PUT",
                headers=_headers(credentials),
                payload=payload,
            )


def _headers(
    credentials: dict[str, str],
) -> dict[str, str]:
    token = credentials.get("token", "").strip()

    if not token:
        raise ValueError(
            "A deSEC API token is required."
        )

    return {
        "Authorization": f"Token {token}",
    }


def _subname(zone: str, hostname: str) -> str:
    zone = zone.rstrip(".").lower()
    hostname = hostname.rstrip(".").lower()

    if hostname == zone:
        return "@"

    suffix = "." + zone

    if not hostname.endswith(suffix):
        raise ValueError(
            f"{hostname} is not inside zone {zone}."
        )

    return hostname[: -len(suffix)]
