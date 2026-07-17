from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.platform.auth_context import AuthContext
from app.platform.permissions import require_permissions

router = APIRouter()


@router.get("/me")
async def me(
    ctx: AuthContext = Depends(require_permissions(get_settings().auth_required_permissions)),
):
    return {
        "isAuthenticated": ctx.is_authenticated,
        "userId": ctx.user_id,
        "userName": ctx.user_name,
        "email": ctx.email,
        "roles": ctx.roles,
        "authMode": ctx.auth_mode,
    }


@router.get("/items")
async def list_items(
    ctx: AuthContext = Depends(require_permissions(get_settings().auth_required_permissions)),
):
    settings = get_settings()

    return {
        "featureKey": settings.feature_key,
        "items": [
            {
                "id": "sample-1",
                "name": f"{settings.feature_key} sample item",
            }
        ],
        "user": {
            "id": ctx.user_id,
            "name": ctx.user_name,
            "email": ctx.email,
        },
    }