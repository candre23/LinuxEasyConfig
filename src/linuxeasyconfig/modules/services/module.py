from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .provider import ServicesTableProvider


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
                description="View and manage applications that run in the background.",
                category="System",
                icon="applications-system",
                keywords=("services", "startup", "background", "systemd"),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="services.main",
                title="Background Services",
                view_type="table",
                data={
                    "heading": "Background Services",
                    "description": (
                        "Services currently installed on this system."
                    ),
                    "provider": self._provider,
                    "selectable": True,
                    "sortable": True,
                },
            )
        ]
