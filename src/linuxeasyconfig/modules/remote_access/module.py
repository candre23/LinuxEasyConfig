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
                    "VNC",
                    "TigerVNC",
                    "Guacamole",
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
        services: list[LocalServiceDefinition] = []

        ssh = self._repository.snapshot()
        if bool(ssh.get("installed", False)):
            services.append(
                LocalServiceDefinition(
                    id="service.ssh",
                    provider_module_id=(
                        "org.linuxeasyconfig.remote_access"
                    ),
                    title="Secure Shell",
                    protocol="tcp",
                    host="127.0.0.1",
                    port=int(ssh.get("port", 22)),
                    category="remote-access",
                    description=(
                        "OpenSSH remote terminal access."
                    ),
                    metadata={
                        "active": bool(
                            ssh.get("active", False)
                        ),
                        "reverse_proxy_compatible": False,
                    },
                )
            )

        vnc = self._repository.vnc_snapshot()
        configuration = vnc.get("configuration")
        if (
            bool(vnc.get("installed", False))
            and isinstance(configuration, dict)
        ):
            services.append(
                LocalServiceDefinition(
                    id="service.vnc",
                    provider_module_id=(
                        "org.linuxeasyconfig.remote_access"
                    ),
                    title="TigerVNC",
                    protocol="tcp",
                    host="127.0.0.1",
                    port=int(
                        configuration.get("port", 5901)
                    ),
                    category="remote-access",
                    description=(
                        "TigerVNC virtual desktop access."
                    ),
                    metadata={
                        "active": bool(
                            vnc.get("active", False)
                        ),
                        "reverse_proxy_compatible": False,
                        "guacamole_compatible": True,
                    },
                )
            )

        return services
