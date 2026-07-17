# Linux Easy Config Dynamic DNS provider plugins

Dynamic DNS providers are Python adapters discovered by the Dynamic DNS module.

Built-in providers live in:

```text
src/linuxeasyconfig/modules/dynamic_dns/providers/
```

User-installed providers can be placed in:

```text
~/.local/share/linuxeasyconfig/dynamic-dns-providers/
```

Each plugin is a single Python file that defines a `Provider` class.

## Required metadata

```python
from linuxeasyconfig.modules.dynamic_dns.providers.base import (
    ProviderField,
    ProviderMetadata,
)

class Provider:
    metadata = ProviderMetadata(
        id="example",
        name="Example DNS",
        description="Example provider.",
        homepage="https://example.com/",
        fields=(
            ProviderField(
                id="token",
                label="API token",
                field_type="password",
            ),
        ),
        supports_hostname_creation=True,
        supports_ipv4=True,
        supports_ipv6=True,
    )
```

Provider IDs must be stable and unique.

## Required methods

```python
def test_credentials(self, credentials: dict[str, str]) -> str:
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
) -> dict:
    ...

def update_hostname(self, **kwargs) -> dict:
    ...

def delete_hostname(
    self,
    *,
    credentials: dict[str, str],
    zone: str,
    hostname: str,
) -> str:
    ...
```

`list_zones()` returns records shaped like:

```python
{"id": "provider-zone-id", "name": "example.com"}
```

The current LEC UI accepts manual zone entry, but zone enumeration is part of the interface so a later UI can provide provider-backed selection.

## Security rules

- Never log API tokens.
- Use provider-scoped or zone-scoped tokens where supported.
- Validate hostnames before sending requests.
- Use HTTPS APIs only.
- Set finite network timeouts.
- Raise clear `ValueError` messages for user input errors.
- Raise `RuntimeError` for provider or network failures.
- Do not invoke shell commands from provider plugins.
- Do not access files outside the Dynamic DNS configuration area.

User plugins execute as part of LEC's privileged update process. Only install provider plugins from trusted sources.
