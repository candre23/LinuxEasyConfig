# Dynamic DNS Provider Plugins

The Dynamic DNS module supports provider plugins for DNS services that expose an HTTPS API.

Built-in providers are the best implementation references:

```text
src/linuxeasyconfig/modules/dynamic_dns/providers/desec.py
src/linuxeasyconfig/modules/dynamic_dns/providers/cloudflare.py
```

A separate example provider file is unnecessary and may be removed.

## 1. Provider Locations

Built-in providers live in:

```text
src/linuxeasyconfig/modules/dynamic_dns/providers/
```

User-installed providers are discovered from:

```text
~/.local/share/linuxeasyconfig/dynamic-dns-providers/
```

A user-installed provider is a trusted Python file loaded by LEC. Installing one is equivalent to installing software.

## 2. Provider Class

Each plugin defines a `Provider` class.

The class must expose provider metadata and implement the methods used by the Dynamic DNS module.

Start by copying the closest built-in provider and modifying only the provider-specific API behavior.

## 3. Metadata

Import the shared metadata types:

```python
from linuxeasyconfig.modules.dynamic_dns.providers.base import (
    ProviderField,
    ProviderMetadata,
)
```

Example:

```python
class Provider:
    metadata = ProviderMetadata(
        id="example",
        name="Example DNS",
        description="Manage Dynamic DNS records with Example DNS.",
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

Metadata rules:

- `id` must be stable and unique.
- `name` should match the provider's public name.
- `description` should be short and user-facing.
- `homepage` must use HTTPS.
- Secret fields must use `field_type="password"`.
- Capability flags must reflect the provider's actual API.

## 4. Required Methods

A provider implements:

```python
def test_credentials(
    self,
    credentials: dict[str, str],
) -> str:
    ...
```

Validate credentials with the provider and return a short success message.

```python
def list_zones(
    self,
    credentials: dict[str, str],
) -> list[dict[str, str]]:
    ...
```

Return zones in this form:

```python
{
    "id": "provider-zone-id",
    "name": "example.com",
}
```

```python
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
```

Create the hostname when supported, or update it when it already exists.

```python
def update_hostname(self, **kwargs) -> dict:
    ...
```

Update the provider record using the same validated inputs expected by the current built-in implementations.

```python
def delete_hostname(
    self,
    *,
    credentials: dict[str, str],
    zone: str,
    hostname: str,
) -> str:
    ...
```

Delete the managed hostname and return a short success message.

Use the current deSEC and Cloudflare providers as the authoritative reference for exact signatures and return values.

## 5. Hostname and Address Handling

Providers receive normalized hostnames from the Dynamic DNS module, but must still validate provider-specific requirements.

A provider should:

- reject empty or malformed hostnames
- distinguish the full hostname from the selected zone
- avoid creating duplicate records
- support IPv4 and IPv6 only when declared in metadata
- omit empty address families rather than sending invalid records
- preserve unrelated DNS records
- honor the provider's proxy setting only when supported

LEC currently uses a default DNS TTL of 3600 seconds for supported providers unless the provider requires different handling.

## 6. Network Behavior

Provider API calls must:

- use HTTPS
- use finite connection and response timeouts
- use the shared Dynamic DNS HTTP helper where practical
- allow the shared retry behavior to handle temporary failures
- send provider-required authentication headers
- parse error responses safely
- avoid logging credentials or authorization headers

Do not invoke shell commands from a provider plugin.

## 7. Errors

Use:

```python
raise ValueError("Clear explanation")
```

for invalid user input or missing credentials.

Use:

```python
raise RuntimeError("Clear explanation")
```

for provider, API, authentication, or network failures.

Error messages should explain what the user can correct without exposing secrets or dumping raw responses unnecessarily.

Good:

```text
The API token was rejected by the provider.
```

Avoid:

```text
Request failed.
```

## 8. Credentials and Security

Provider plugins must:

- never log API tokens
- never write credentials to status snapshots
- use provider-scoped or zone-scoped tokens where available
- request only the permissions required for DNS changes
- avoid exposing secrets in exceptions
- avoid reading files outside the Dynamic DNS configuration area
- avoid importing or executing untrusted code

Credentials are managed by the Dynamic DNS module and stored in protected LEC configuration. Providers should consume the supplied credential dictionary rather than inventing a separate storage mechanism.

## 9. Provider Output

Return structured Python dictionaries and strings, not raw HTTP response objects.

Provider results should contain only information needed by the Dynamic DNS module, such as:

- provider record identifier
- hostname
- IPv4 address
- IPv6 address
- proxy state
- confirmation message

Do not return credentials, authorization headers, or full debug responses.

## 10. Installation

To install a user provider, place the Python file in:

```text
~/.local/share/linuxeasyconfig/dynamic-dns-providers/
```

Then restart LEC so provider discovery runs again.

The filename does not define the provider ID. The stable ID comes from:

```python
Provider.metadata.id
```

Avoid using the same ID as a built-in or existing user provider.

## 11. Development Process

Recommended workflow:

1. Copy `desec.py` or `cloudflare.py`.
2. Change the metadata.
3. Replace only the provider-specific API requests and record parsing.
4. Keep shared validation and error behavior consistent.
5. Test credentials.
6. Test zone listing.
7. Test hostname creation.
8. Test updates after the public IP changes.
9. Test deletion.
10. Verify that no token appears in logs or status files.

## 12. Release Checklist

Before distributing a provider plugin, verify:

- [ ] The provider ID is unique and stable.
- [ ] Metadata accurately declares capabilities.
- [ ] All API traffic uses HTTPS.
- [ ] Requests have finite timeouts.
- [ ] Temporary failures use the shared retry behavior where applicable.
- [ ] Credentials are never logged or returned.
- [ ] IPv4-only, IPv6-only, and dual-stack cases behave correctly.
- [ ] Existing unrelated DNS records are preserved.
- [ ] Authentication failures produce clear messages.
- [ ] The plugin loads after restarting LEC.
- [ ] Create, update, and delete operations work against a test hostname.
- [ ] The implementation follows the current built-in provider interface.
