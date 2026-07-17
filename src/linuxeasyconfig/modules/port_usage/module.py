from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import PortUsageRepository
from .views import PortUsageView


class PortUsageModule(LECModule):
    def __init__(self) -> None:
        self._repository = PortUsageRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="port_usage.main",
                title="Port Usage",
                target_type="view",
                target_id="port_usage.main",
                description=(
                    "Show listening ports, applications, firewall "
                    "access, Docker translations, and Caddy exposure."
                ),
                category="System",
                icon="network-server",
                keywords=(
                    "ports",
                    "listeners",
                    "firewall",
                    "caddy",
                    "docker",
                    "network",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="port_usage.main",
                title="Port Usage",
                view_type="custom",
                data={
                    "factory": lambda: PortUsageView(
                        self._repository
                    )
                },
            )
        ]
