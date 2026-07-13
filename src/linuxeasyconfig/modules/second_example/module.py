from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)


class SecondExampleModule(LECModule):
    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="second_example.main",
                title="Second Example",
                target_type="view",
                target_id="second_example.main",
                description="Verify that LEC can switch between independently loaded modules.",
                category="Examples",
                icon="document-new",
                keywords=("second", "example", "test"),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="second_example.main",
                title="Second Example",
                view_type="message",
                data={
                    "heading": "Second Example Module",
                    "message": (
                        "LEC successfully loaded another module and switched "
                        "to its view."
                    ),
                },
            )
        ]
