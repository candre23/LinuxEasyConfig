from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)


class MountsModule(LECModule):
    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="mounts.main",
                title="Mount Management",
                target_type="view",
                target_id="mounts.main",
                description="Connect and manage local and network storage.",
                category="System",
                icon="drive-harddisk",
                keywords=("mount", "drive", "storage", "network share"),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="mounts.main",
                title="Mount Management",
                view_type="message",
                data={
                    "heading": "Mount Management",
                    "message": (
                        "Local and network mount management will be implemented here."
                    ),
                },
            )
        ]
