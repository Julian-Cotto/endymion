import pytest

from app.core.auth import AuthenticatedUser
from app.services.bootstrap_service import BootstrapService


class TestSettings:
    bootstrap_mode = "registry"
    platform_admin_role = "platform.admin"


class DummyRegistryClient:
    async def get_active_features(self, environment: str):
        return [
            {
                "featureKey": "orders",
                "displayName": "Orders",
                "route": "/orders",
                "version": "1.0.0",
                "nav": {
                    "label": "Orders",
                    "icon": "package",
                    "group": None,
                    "order": 0,
                },
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
                    "mode": "entra",
                    "required": True,
                    "shellAuthRequired": True,
                    "tokenForwarding": True,
                    "tokenStrategy": "forwarded-bearer",
                    "allowedDevModes": ["mock"],
                    "roles": [],
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
    def get_permissions(self, user: AuthenticatedUser):
        return user.roles


class DummyCache:
    async def get_or_set(self, key, ttl, factory):
        return await factory()


@pytest.mark.asyncio
async def test_build_bootstrap():
    service = BootstrapService(
        registry_client=DummyRegistryClient(),
        flag_service=DummyFlagService(),
        permission_service=DummyPermissionService(),
        cache=DummyCache(),
        cache_ttl_seconds=30,
        include_flag_prefixes=["orders.", "shell."],
        app_env="test",
        settings=TestSettings(),
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
    assert payload.user.id == "u1"
    assert payload.permissions == ["orders.view"]

    assert len(payload.features) == 1

    feature = payload.features[0]
    assert feature.featureKey == "orders"
    assert feature.displayName == "Orders"
    assert feature.route == "/orders"
    assert feature.authorization.requiredPermissions == ["orders.view"]
    assert feature.authorization.requiredFlags == ["orders.enabled"]
    assert feature.auth.mode == "entra"
    assert feature.auth.tokenForwarding is True
    assert feature.auth.tokenStrategy == "forwarded-bearer"