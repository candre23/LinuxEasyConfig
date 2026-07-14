from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)


class ExampleModule(LECModule):
    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="example.main",
                title="Example Module",
                target_type="view",
                target_id="example.main",
                description="Verify that LEC can load and display an installed module.",
                category="Examples",
                icon="applications-system",
                keywords=("example", "test", "module"),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="example.main",
                title="Example Module",
                view_type="message",
                data={
                    "heading": "Example Module",
                    "message": "The LEC module system is working.",
                },
            )
        ]
