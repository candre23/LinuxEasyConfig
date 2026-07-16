from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    LocalServiceDefinition,
    ModuleContext,
    ViewDefinition,
)

from .repository import DockerRepository
from .views import DockerView


class DockerModule(LECModule):
    def __init__(self) -> None:
        self._repository = DockerRepository()
        self._context: ModuleContext | None = None

    def bind_context(
        self,
        context: ModuleContext,
    ) -> None:
        super().bind_context(context)
        self._context = context

    def feature_definitions(
        self,
    ) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="docker.main",
                title="Docker",
                target_type="view",
                target_id="docker.main",
                description=(
                    "Install Docker and manage common "
                    "container operations."
                ),
                category="Application",
                icon="package-x-generic",
                keywords=(
                    "docker",
                    "containers",
                    "images",
                    "compose",
                    "applications",
                ),
            )
        ]

    def view_definitions(
        self,
    ) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="docker.main",
                title="Docker",
                view_type="custom",
                data={
                    "factory": lambda: DockerView(
                        self._repository,
                        self._context,
                    )
                },
            )
        ]

    def service_definitions(
        self,
    ) -> list[LocalServiceDefinition]:
        services: list[LocalServiceDefinition] = []

        for item in self._repository.managed_containers():
            if item.host_port <= 0:
                continue

            service_id = (
                "service.docker."
                + item.name.replace("_", "-")
                + "."
                + item.service_protocol
            )

            services.append(
                LocalServiceDefinition(
                    id=service_id,
                    provider_module_id=(
                        "org.linuxeasyconfig.docker"
                    ),
                    title=item.name,
                    protocol=item.service_protocol,
                    host=item.host_address,
                    port=item.host_port,
                    category="container",
                    description=(
                        f"Docker container {item.name}"
                    ),
                    metadata={
                        "container": item.name,
                        "image": item.image,
                        "container_port": (
                            item.container_port
                        ),
                        "transport_protocol": (
                            item.protocol
                        ),
                        "access_scope": (
                            item.access_scope
                        ),
                        "reverse_proxy_compatible": (
                            item.reverse_proxy_compatible
                        ),
                        "public_host": item.public_host,
                    },
                )
            )

        return services
