from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import ReverseProxyRepository
from .views import ReverseProxyView


class ReverseProxyModule(LECModule):
    def __init__(self) -> None:
        self._repository = ReverseProxyRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="reverse_proxy.main",
                title="Reverse Proxy",
                target_type="view",
                target_id="reverse_proxy.main",
                description=(
                    "Install and manage Caddy with Fail2Ban protection."
                ),
                category="System",
                icon="network-server",
                keywords=(
                    "reverse proxy",
                    "caddy",
                    "fail2ban",
                    "https",
                    "domain",
                    "proxy",
                    "security",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="reverse_proxy.main",
                title="Reverse Proxy",
                view_type="custom",
                data={
                    "factory": lambda: ReverseProxyView(
                        self._repository
                    ),
                },
            )
        ]
