from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import RecoveryRepository
from .views import RecoveryView


class RecoveryModule(LECModule):
    def __init__(self) -> None:
        self._repository = RecoveryRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="recovery.main",
                title="LEC Recovery",
                target_type="view",
                target_id="recovery.main",
                description=(
                    "Review and restore files changed by Linux Easy Config."
                ),
                category="System",
                icon="document-revert",
                keywords=(
                    "recovery",
                    "restore",
                    "rollback",
                    "backup",
                    "revision",
                    "undo",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="recovery.main",
                title="LEC Recovery",
                view_type="custom",
                data={
                    "factory": lambda: RecoveryView(
                        self._repository
                    ),
                },
            )
        ]
