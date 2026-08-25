from __future__ import annotations

import pytest

from app.schemas.runtime_features import RuntimeFeaturesResponse
from app.services.bootstrap_service import BootstrapService


class DummyRegistryClient:
    async def get_active_features(self, environment: str):
        return []


class DummyFlagService:
    async def resolve_flags(self, required_flags: list[str]):
        return {}


class DummyPermissionService:
    def get_permissions(self, user):
        return ["*"]


class DummyCache:
    async def get_or_set(self, key, ttl, factory):
        return await factory()


class DummyUser:
    def __init__(self):
        self.id = "local-dev"
        self.display_name = "Local Developer"
        self.email = "dev@local"


@pytest.mark.asyncio
async def test_build_runtime_features_mock_mode():
    service = BootstrapService(
        registry_client=DummyRegistryClient(),
        flag_service=DummyFlagService(),
        permission_service=DummyPermissionService(),
        cache=DummyCache(),
        cache_ttl_seconds=30,
        include_flag_prefixes=["shell.", "orders.", "catalog."],
        app_env="local",
    )

    result = await service.build_runtime_features(DummyUser())

    assert isinstance(result, RuntimeFeaturesResponse)
    assert result.environment == "local"
    assert isinstance(result.features, list)
    assert result.metadata.source == "runtime-service-mock"