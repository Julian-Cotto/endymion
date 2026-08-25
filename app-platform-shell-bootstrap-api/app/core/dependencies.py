from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.appconfig_service import AppConfigFlagService
from app.services.bootstrap_service import BootstrapService
from app.services.cache import InMemoryCache, RedisCache
from app.services.permissions import PermissionService
from app.services.registry_client import RegistryClient


class NoopRegistryClient:
    async def get_active_features(self, environment: str) -> list[dict]:
        return []


# ✅ LOCAL DEV: enable all flags
class NoopFlagService:
    async def resolve_flags(self, keys: list[str]) -> dict[str, bool]:
        return {key: True for key in keys}


@lru_cache(maxsize=1)
def cache_backend_dependency():
    settings = get_settings()

    if settings.cache_backend == "redis":
        redis_url = getattr(settings, "redis_url", "")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required when CACHE_BACKEND=redis.")
        return RedisCache(redis_url)

    return InMemoryCache()


@lru_cache(maxsize=1)
def permission_service_dependency() -> PermissionService:
    return PermissionService(get_settings())


@lru_cache(maxsize=1)
def registry_client_dependency():
    settings = get_settings()

    if settings.bootstrap_mode == "mock":
        return NoopRegistryClient()

    if not settings.registry_base_url:
        raise RuntimeError(
            "REGISTRY_BASE_URL is required when BOOTSTRAP_MODE=registry."
        )

    return RegistryClient(
        base_url=settings.registry_base_url,
        read_token=getattr(settings, "registry_read_token", None),
    )


@lru_cache(maxsize=1)
def flag_service_dependency():
    settings = get_settings()

    # ✅ ALWAYS enable flags locally unless explicitly using AppConfig
    if not settings.app_configuration_endpoint:
        return NoopFlagService()

    return AppConfigFlagService(
        endpoint=settings.app_configuration_endpoint,
        label=settings.app_configuration_label,
        cache=cache_backend_dependency(),
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )


@lru_cache(maxsize=1)
def bootstrap_service_dependency() -> BootstrapService:
    settings = get_settings()

    return BootstrapService(
        registry_client=registry_client_dependency(),
        flag_service=flag_service_dependency(),
        permission_service=permission_service_dependency(),
        cache=cache_backend_dependency(),
        cache_ttl_seconds=settings.cache_ttl_seconds,
        include_flag_prefixes=settings.bootstrap_include_flag_prefix_list,
        app_env=settings.app_env,
        settings=settings,
    )