from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import FirewallRepository
from .views import FirewallView


class FirewallModule(LECModule):
    def __init__(self) -> None:
        self._repository = FirewallRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="firewall.main",
                title="Firewall",
                target_type="view",
                target_id="firewall.main",
                description=(
                    "Manage Ubuntu's UFW firewall using "
                    "plain-language rules."
                ),
                category="System",
                icon="network-server",
                keywords=(
                    "firewall",
                    "ufw",
                    "ports",
                    "security",
                    "network",
                    "allow",
                    "deny",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="firewall.main",
                title="Firewall",
                view_type="custom",
                data={
                    "factory": lambda: FirewallView(
                        self._repository
                    ),
                },
            )
        ]
