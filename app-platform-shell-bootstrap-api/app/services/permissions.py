from __future__ import annotations

from app.core.auth import AuthenticatedUser
from app.core.config import Settings
from app.services.permission_mapper import permissions_from_roles


class PermissionService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def get_permissions(self, user: AuthenticatedUser) -> list[str]:
        """
        Resolve platform permissions from the authenticated user.

        Current production strategy:

            Entra app role value == platform permission

        Examples:

            user.roles = ["orders.view", "catalog.view"]
            permissions = ["orders.view", "catalog.view"]

            user.roles = ["platform.admin"]
            permissions = ["*"]

        No scope-role mapping.
        No role-permission mapping.
        No default production grants.
        """

        return permissions_from_roles(user.roles, self.settings)