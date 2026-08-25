from __future__ import annotations

from app.core.config import Settings


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized in seen:
            continue

        seen.add(normalized)
        result.append(normalized)

    return result


def permissions_from_roles(roles: list[str], settings: Settings) -> list[str]:
    """
    Convert platform roles into platform permissions.

    With the Entra naming-convention strategy, this is intentionally almost
    identity mapping:

        orders.view  -> orders.view
        orders.edit  -> orders.edit
        catalog.view -> catalog.view

    The only built-in special case is the platform admin role:

        platform.admin -> *

    No environment-based role-permission mapping is used.
    """

    normalized_roles = _dedupe_keep_order(roles)

    if settings.platform_admin_role in normalized_roles:
        return ["*"]

    return normalized_roles


def has_permission(
    user_permissions: list[str],
    required_permissions: list[str],
) -> bool:
    """
    Return True if user permissions satisfy all required permissions.

    Rules:
      - No required permissions means feature/operation is allowed.
      - Wildcard '*' grants everything.
      - Otherwise, every required permission must be present.
    """

    if not required_permissions:
        return True

    if "*" in user_permissions:
        return True

    return all(permission in user_permissions for permission in required_permissions)