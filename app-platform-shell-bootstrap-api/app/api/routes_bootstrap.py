from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.auth_runtime import runtime_authenticated_user
from app.core.auth import AuthenticatedUser
from app.core.config import get_settings
from app.core.dependencies import bootstrap_service_dependency
from app.services.bootstrap_service import BootstrapService

router = APIRouter(tags=["shell", "runtime"])


@router.get("/api/shell/bootstrap")
async def get_bootstrap(
    user: AuthenticatedUser = Depends(runtime_authenticated_user),
    service: BootstrapService = Depends(bootstrap_service_dependency),
):
    return await service.build_bootstrap(user)


@router.get("/api/runtime/features")
async def get_runtime_features(
    user: AuthenticatedUser = Depends(runtime_authenticated_user),
    service: BootstrapService = Depends(bootstrap_service_dependency),
):
    return await service.build_runtime_features(user)


@router.get("/api/shell/health")
async def health():
    return {"status": "ok", "generatedAtUtc": datetime.now(UTC).isoformat()}


@router.get("/api/shell/health/dependencies")
async def dependency_health():
    settings = get_settings()
    return {
        "status": "ok",
        "checks": {
            "bootstrapMode": settings.bootstrap_mode,
            "registry": "enabled" if settings.bootstrap_mode == "registry" else "mock-bypassed",
            "appConfiguration": "configured" if settings.app_configuration_endpoint else "not-configured",
        },
    }