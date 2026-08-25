import pytest

from app.core.auth import AuthenticatedUser
from app.services.bootstrap_service import BootstrapService


class DummyRegistryClient:
    async def get_active_features(self, environment: str):
        assert environment == "test"
        return [
            {
                "featureKey": "orders",
                "displayName": "Orders",
                "route": "/orders",
                "version": "1.0.0",
                "nav": {"label": "Orders", "icon": "package"},
                "frontend": {
                    "enabled": True,
                    "entryUrl": "http://localhost:3200/src/bootstrap-entry.tsx",
                    "mountFunction": "mount",
                },
                "backend": {
                    "enabled": True,
                    "apiBaseUrl": "http://localhost:8100/api/orders",
                    "healthEndpoint": "/health",
                },
                "authorization": {
                    "requiredPermissions": ["orders.view"],
                    "requiredFlags": ["orders.enabled"],
                },
                "auth": {
                    "required": True,
                    "mode": "mock",
                    "shellAuthRequired": True,
                    "tokenForwarding": False,
                },
            }
        ]


class DummyFlagService:
    async def resolve_flags(self, required_flags: list[str]):
        return {
            "orders.enabled": True,
            "shell.debug": True,
        }


class DummyPermissionService:
    def get_permissions(self, user):
        return ["orders.view"]


class DummyCache:
    async def get_or_set(self, key, ttl, factory):
        return await factory()


@pytest.mark.asyncio
async def test_build_bootstrap_registry_mode(monkeypatch):
    class FakeSettings:
        bootstrap_mode = "registry"
        mock_features = []

    monkeypatch.setattr(
        "app.services.bootstrap_service.get_settings",
        lambda: FakeSettings(),
    )

    service = BootstrapService(
        registry_client=DummyRegistryClient(),
        flag_service=DummyFlagService(),
        permission_service=DummyPermissionService(),
        cache=DummyCache(),
        cache_ttl_seconds=30,
        include_flag_prefixes=["orders.", "shell."],
        app_env="test",
    )

    user = AuthenticatedUser(
        id="u1",
        display_name="Test User",
        email="test@example.com",
        roles=["orders.view"],
        claims={},
    )

    payload = await service.build_bootstrap(user)

    assert payload.environment == "test"
    assert payload.permissions == ["orders.view"]
    assert payload.flags["orders.enabled"] is True
    assert len(payload.features) == 1
    assert payload.features[0].featureKey == "orders"
    assert payload.features[0].frontend.entryUrl == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert payload.features[0].backend.apiBaseUrl == "http://localhost:8100/api/orders"
    assert payload.metadata.source == "bootstrap-service-registry"