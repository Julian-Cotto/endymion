from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.platform.auth_context import AuthContext
from app.platform.permissions import require_permissions

router = APIRouter()

# NOTE: this module used to define a second GET /health returning camelCase
# keys. It was dead code: main.py includes health_router before feature_router
# under the same prefix, so app/api/health.py's snake_case HealthResponse
# always shadowed it. The frontend reads `feature_key` and matches the
# surviving route. Removed rather than left to rot, since the scaffold's
# test_health was asserting against the unreachable one.


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