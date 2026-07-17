from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    CapabilityDefinition,
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import DynamicDNSRepository
from .views import DynamicDNSView


class DynamicDNSModule(LECModule):
    def __init__(self) -> None:
        self._repository = DynamicDNSRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="dynamic_dns.main",
                title="Dynamic DNS",
                target_type="view",
                target_id="dynamic_dns.main",
                description=(
                    "Manage dynamic DNS providers, hostnames, "
                    "and automatic public-IP updates."
                ),
                category="System",
                icon="network-server",
                keywords=(
                    "dynamic dns",
                    "ddns",
                    "cloudflare",
                    "desec",
                    "hostname",
                    "public ip",
                    "dns",
                ),
            )
        ]

    def capability_definitions(
        self,
    ) -> list[CapabilityDefinition]:
        return [
            CapabilityDefinition(
                id="dynamic_dns.create_hostname",
                provider_module_id=(
                    "org.linuxeasyconfig.dynamic_dns"
                ),
                title="Create a dynamic DNS hostname",
                description=(
                    "Create and track an A or AAAA hostname "
                    "through a configured provider."
                ),
                privileged_task_id=(
                    "dynamic_dns.hostname_create"
                ),
                metadata={
                    "supports_ipv4": True,
                    "supports_ipv6": True,
                    "supports_subdomains": True,
                },
            ),
            CapabilityDefinition(
                id="dynamic_dns.remove_hostname",
                provider_module_id=(
                    "org.linuxeasyconfig.dynamic_dns"
                ),
                title="Remove a dynamic DNS hostname",
                description=(
                    "Stop managing or delete a provider hostname."
                ),
                privileged_task_id=(
                    "dynamic_dns.hostname_delete"
                ),
                metadata={},
            ),
            CapabilityDefinition(
                id="dynamic_dns.update_now",
                provider_module_id=(
                    "org.linuxeasyconfig.dynamic_dns"
                ),
                title="Update dynamic DNS now",
                description=(
                    "Immediately update all enabled hostnames."
                ),
                privileged_task_id="dynamic_dns.update_now",
                metadata={},
            ),
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="dynamic_dns.main",
                title="Dynamic DNS",
                view_type="custom",
                data={
                    "factory": lambda: DynamicDNSView(
                        self._repository
                    )
                },
            )
        ]
