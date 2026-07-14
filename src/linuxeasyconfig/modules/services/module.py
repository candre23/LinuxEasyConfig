from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .provider import ServicesTableProvider
from .views import ServicesView


class ServicesModule(LECModule):
    def __init__(self) -> None:
        self._provider = ServicesTableProvider()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="services.main",
                title="Background Services",
                target_type="view",
                target_id="services.main",
                description=(
                    "View, manage, and install applications that "
                    "run in the background."
                ),
                category="System",
                icon="applications-system",
                keywords=(
                    "services",
                    "startup",
                    "background",
                    "systemd",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="services.main",
                title="Background Services",
                view_type="custom",
                data={
                    "factory": lambda: ServicesView(
                        self._provider
                    ),
                },
            )
        ]
