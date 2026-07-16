from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .collector import HardwareCollector
from .views import HardwareMonitorView


class HardwareMonitorModule(LECModule):
    def __init__(self) -> None:
        self._collector = HardwareCollector()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="hardware_monitor.main",
                title="Hardware Monitor",
                target_type="view",
                target_id="hardware_monitor.main",
                description=(
                    "View live CPU, memory, storage, network, "
                    "temperature, and physical disk health information."
                ),
                category="System",
                icon="utilities-system-monitor",
                keywords=(
                    "hardware",
                    "monitor",
                    "cpu",
                    "memory",
                    "ram",
                    "swap",
                    "network",
                    "disk",
                    "temperature",
                    "sensors",
                    "SMART",
                    "NVMe",
                    "disk health",
                    "self-test",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="hardware_monitor.main",
                title="Hardware Monitor",
                view_type="custom",
                data={
                    "factory": lambda: HardwareMonitorView(
                        self._collector
                    ),
                },
            )
        ]
