from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .provider import MountsTableProvider
from .views import MountsView


class MountsModule(LECModule):
    def __init__(self) -> None:
        self._provider = MountsTableProvider()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="mounts.main",
                title="Mounts & Shares",
                target_type="view",
                target_id="mounts.main",
                description="Mount storage and share local folders over the network.",
                category="System",
                icon="drive-harddisk",
                keywords=(
                    "mount",
                    "drive",
                    "storage",
                    "network share",
                    "SMB",
                    "CIFS",
                    "NFS",
                    "NAS",
                    "Samba server",
                    "host share",
                    "share folder",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="mounts.main",
                title="Mounts & Shares",
                view_type="custom",
                data={
                    "factory": lambda: MountsView(self._provider),
                },
            )
        ]
