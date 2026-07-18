from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .overview_repository import OverviewRepository
from .repository import RecoveryRepository
from .views import LECSettingsView


class LECSettingsModule(LECModule):
    def __init__(self) -> None:
        self._overview_repository = OverviewRepository()
        self._recovery_repository = RecoveryRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="lec_settings.main",
                title="LEC Settings",
                target_type="view",
                target_id="lec_settings.main",
                description=(
                    "View LEC information, configure application "
                    "preferences, and recover configuration revisions."
                ),
                category="System",
                icon="preferences-system",
                keywords=(
                    "settings",
                    "preferences",
                    "overview",
                    "version",
                    "modules",
                    "recovery",
                    "restore",
                    "rollback",
                    "backup",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="lec_settings.main",
                title="LEC Settings",
                view_type="custom",
                data={
                    "factory": lambda: LECSettingsView(
                        self._overview_repository,
                        self._recovery_repository,
                    ),
                },
            )
        ]
