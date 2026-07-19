from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    CapabilityDefinition,
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import FirewallRepository
from .views import FirewallView


class FirewallModule(LECModule):
    def __init__(self) -> None:
        self._repository = FirewallRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="firewall.main",
                title="Firewall",
                target_type="view",
                target_id="firewall.main",
                description=(
                    "Manage Ubuntu's UFW firewall using "
                    "plain-language rules."
                ),
                category="System",
                icon="network-server",
                keywords=(
                    "firewall",
                    "ufw",
                    "ports",
                    "security",
                    "network",
                    "allow",
                    "deny",
                ),
            )
        ]

    def capability_definitions(
        self,
    ) -> list[CapabilityDefinition]:
        return [
            CapabilityDefinition(
                id="firewall.allow_service",
                provider_module_id=(
                    "org.linuxeasyconfig.firewall"
                ),
                title=(
                    "Allow a local service through "
                    "the firewall"
                ),
                description=(
                    "Create one or more UFW rules "
                    "for a service port."
                ),
                privileged_task_id=(
                    "firewall.add_rule"
                ),
                metadata={
                    "supports_local_network": True,
                    "supports_tcp": True,
                    "supports_udp": True,
                },
            ),
            CapabilityDefinition(
                id=(
                    "firewall."
                    "allow_docker_service"
                ),
                provider_module_id=(
                    "org.linuxeasyconfig.firewall"
                ),
                title=(
                    "Allow a Docker service through "
                    "the firewall"
                ),
                description=(
                    "Create persistent local-network "
                    "firewall rules for a Docker "
                    "published port."
                ),
                privileged_task_id=(
                    "firewall."
                    "allow_docker_service"
                ),
                metadata={
                    "supports_local_network": True,
                    "supports_tcp": True,
                    "supports_udp": True,
                    "docker_aware": True,
                },
            ),
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="firewall.main",
                title="Firewall",
                view_type="custom",
                data={
                    "factory": lambda: FirewallView(
                        self._repository
                    ),
                },
            )
        ]
