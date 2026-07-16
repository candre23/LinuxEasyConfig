from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    LocalServiceDefinition,
    ModuleContext,
    ViewDefinition,
)

from .repository import RemoteAccessRepository
from .views import RemoteAccessView


class RemoteAccessModule(LECModule):
    def __init__(self) -> None:
        self._repository = RemoteAccessRepository()
        self._context: ModuleContext | None = None

    def bind_context(self, context: ModuleContext) -> None:
        super().bind_context(context)
        self._context = context

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="remote_access.main",
                title="Remote Access",
                target_type="view",
                target_id="remote_access.main",
                description=(
                    "Install and manage secure remote access "
                    "to this computer."
                ),
                category="System",
                icon="network-workgroup",
                keywords=(
                    "ssh",
                    "remote",
                    "openssh",
                    "terminal",
                    "authorized keys",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="remote_access.main",
                title="Remote Access",
                view_type="custom",
                data={
                    "factory": lambda: RemoteAccessView(
                        self._repository,
                        self._context,
                    )
                },
            )
        ]

    def service_definitions(self) -> list[LocalServiceDefinition]:
        snapshot = self._repository.snapshot()
        if not bool(snapshot.get("installed", False)):
            return []

        return [
            LocalServiceDefinition(
                id="service.ssh",
                provider_module_id=(
                    "org.linuxeasyconfig.remote_access"
                ),
                title="Secure Shell",
                protocol="tcp",
                host="127.0.0.1",
                port=int(snapshot.get("port", 22)),
                category="remote-access",
                description=(
                    "OpenSSH remote terminal access."
                ),
                metadata={
                    "active": bool(
                        snapshot.get("active", False)
                    ),
                    "reverse_proxy_compatible": False,
                },
            )
        ]
