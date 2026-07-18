from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import SystemLogsRepository
from .views import SystemLogsView


class SystemLogsModule(LECModule):
    def __init__(self) -> None:
        self._repository = SystemLogsRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="system_logs.main",
                title="System Logs",
                target_type="view",
                target_id="system_logs.main",
                description=(
                    "Browse and interpret system, service, kernel, "
                    "authentication, and application logs."
                ),
                category="System",
                icon="utilities-log-viewer",
                keywords=(
                    "logs",
                    "journal",
                    "journalctl",
                    "errors",
                    "warnings",
                    "troubleshooting",
                    "kernel",
                    "authentication",
                    "security",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="system_logs.main",
                title="System Logs",
                view_type="custom",
                data={
                    "factory": lambda: SystemLogsView(
                        self._repository
                    )
                },
            )
        ]
