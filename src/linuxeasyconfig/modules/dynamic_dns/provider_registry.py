from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any

from .providers.base import DynamicDNSProvider, ProviderMetadata


BUILTIN_PROVIDER_MODULES = (
    "linuxeasyconfig.modules.dynamic_dns.providers.desec",
    "linuxeasyconfig.modules.dynamic_dns.providers.cloudflare",
)

USER_PROVIDER_DIR = (
    Path.home()
    / ".local"
    / "share"
    / "linuxeasyconfig"
    / "dynamic-dns-providers"
)


def load_providers() -> dict[str, DynamicDNSProvider]:
    providers: dict[str, DynamicDNSProvider] = {}

    for module_name in BUILTIN_PROVIDER_MODULES:
        module = importlib.import_module(module_name)
        provider = module.Provider()
        providers[provider.metadata.id] = provider

    if USER_PROVIDER_DIR.is_dir():
        for path in sorted(
            USER_PROVIDER_DIR.glob("*.py")
        ):
            provider = _load_external_provider(path)
            providers[provider.metadata.id] = provider

    return providers


def provider_metadata() -> list[ProviderMetadata]:
    return sorted(
        (
            provider.metadata
            for provider in load_providers().values()
        ),
        key=lambda item: item.name.lower(),
    )


def get_provider(
    provider_id: str,
) -> DynamicDNSProvider:
    providers = load_providers()

    try:
        return providers[provider_id]
    except KeyError as exc:
        raise ValueError(
            f"Dynamic DNS provider {provider_id!r} "
            "is not installed."
        ) from exc


def _load_external_provider(
    path: Path,
) -> DynamicDNSProvider:
    module_name = (
        "lec_dynamic_dns_provider_"
        + path.stem.replace("-", "_")
    )
    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Could not load provider plugin {path.name}."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    provider_class = getattr(
        module,
        "Provider",
        None,
    )

    if provider_class is None:
        raise RuntimeError(
            f"{path.name} does not define Provider."
        )

    provider = provider_class()
    metadata = getattr(
        provider,
        "metadata",
        None,
    )

    if metadata is None or not metadata.id:
        raise RuntimeError(
            f"{path.name} has invalid provider metadata."
        )

    return provider
