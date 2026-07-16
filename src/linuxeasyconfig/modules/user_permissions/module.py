from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import UserPermissionsRepository
from .views import UserPermissionsView


class UserPermissionsModule(LECModule):
    def __init__(self) -> None:
        self._repository = UserPermissionsRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="user_permissions.main",
                title="User Permissions",
                target_type="view",
                target_id="user_permissions.main",
                description=(
                    "Create service accounts and control their access."
                ),
                category="System",
                icon="system-users",
                keywords=(
                    "user",
                    "permissions",
                    "service account",
                    "groups",
                    "ACL",
                    "folder access",
                    "ownership",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="user_permissions.main",
                title="User Permissions",
                view_type="custom",
                data={
                    "factory": lambda: UserPermissionsView(
                        self._repository
                    ),
                },
            )
        ]
