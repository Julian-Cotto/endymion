from __future__ import annotations

from fastapi import Header

from app.platform.auth_context import AuthContext, extract_auth_context


async def get_auth_context(
    authorization: str | None = Header(default=None),
    x_debug_user_id: str | None = Header(default=None),
    x_debug_user_name: str | None = Header(default=None),
    x_debug_email: str | None = Header(default=None),
    x_debug_roles: str | None = Header(default=None),
) -> AuthContext:
    return extract_auth_context(
        authorization_header=authorization,
        debug_user_id=x_debug_user_id,
        debug_user_name=x_debug_user_name,
        debug_email=x_debug_email,
        debug_roles=x_debug_roles,
    )