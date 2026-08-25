from __future__ import annotations

from collections.abc import Iterable

from fastapi import Depends, HTTPException, status

from app.dependencies import get_auth_context
from app.platform.auth_context import AuthContext


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for v in values:
        v = v.strip()
        if not v:
            continue
        if v in seen:
            continue
        seen.add(v)
        result.append(v)
    return result


def resolve_permissions(ctx: AuthContext) -> list[str]:
    """
    Platform rule:

        Entra role value == permission

    Example:
        roles = ["orders.view", "orders.edit"]
        permissions = ["orders.view", "orders.edit"]

    Special case:
        platform.admin → *
    """

    roles = _dedupe(ctx.roles)

    if "platform.admin" in roles:
        return ["*"]

    return roles


def has_permission(
    user_permissions: list[str],
    required_permissions: list[str],
) -> bool:
    if not required_permissions:
        return True

    if "*" in user_permissions:
        return True

    return all(p in user_permissions for p in required_permissions)


def require_permissions(required: Iterable[str]):
    required_permissions = [p.strip() for p in required if p.strip()]

    async def dependency(
        ctx: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        permissions = resolve_permissions(ctx)

        if not has_permission(permissions, required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Insufficient permissions",
                    "requiredPermissions": required_permissions,
                },
            )

        return ctx

    return dependency


def require_any_permission(required: Iterable[str]):
    required_permissions = [p.strip() for p in required if p.strip()]

    async def dependency(
        ctx: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        permissions = resolve_permissions(ctx)

        if "*" in permissions:
            return ctx

        if any(p in permissions for p in required_permissions):
            return ctx

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Insufficient permissions",
                "requiredAnyPermission": required_permissions,
            },
        )

    return dependency