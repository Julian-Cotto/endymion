import jwt
import pytest

from app.api.auth_runtime import runtime_authenticated_user
from app.services.bootstrap_service import BootstrapService


def _make_token(payload: dict) -> str:
    return jwt.encode(payload, "test-secret", algorithm="HS256")


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
                    "mode": "entra",
                    "shellAuthRequired": True,
                    "tokenForwarding": True,
                    "tokenStrategy": "forwarded-bearer",
                    "allowedDevModes": ["mock"],
                    "roles": [],
                },
            },
            {
                "featureKey": "catalog",
                "displayName": "Catalog",
                "route": "/catalog",
                "version": "1.0.0",
                "nav": {"label": "Catalog", "icon": "boxes"},
                "frontend": {
                    "enabled": True,
                    "entryUrl": "http://localhost:3300/src/bootstrap-entry.tsx",
                    "mountFunction": "mount",
                },
                "backend": {
                    "enabled": True,
                    "apiBaseUrl": "http://localhost:8200/api/catalog",
                    "healthEndpoint": "/health",
                },
                "authorization": {
                    "requiredPermissions": ["catalog.view"],
                    "requiredFlags": ["catalog.enabled"],
                },
                "auth": {
                    "required": True,
                    "mode": "entra",
                    "shellAuthRequired": True,
                    "tokenForwarding": True,
                    "tokenStrategy": "forwarded-bearer",
                    "allowedDevModes": ["mock"],
                    "roles": [],
                },
            },
        ]


class DummyFlagService:
    async def resolve_flags(self, required_flags: list[str]):
        return {
            "orders.enabled": True,
            "catalog.enabled": True,
            "shell.debug": True,
        }


class DummyCache:
    async def get_or_set(self, key, ttl, factory):
        return await factory()


class BaseFakeSettings:
    bootstrap_mode = "registry"
    auth_issuer = "https://issuer.example.com"
    auth_audience = "api://shell-bootstrap"
    auth_allowed_algs = ["HS256"]
    auth_roles_claim = "roles"
    auth_groups_claim = "groups"
    auth_scope_claim = "scp"
    auth_wids_claim = "wids"
    auth_user_id_claim = "sub"
    auth_user_name_claim = "name"
    auth_email_claim = "email"
    auth_jwks_url = ""
    platform_admin_role = "platform.admin"


def _build_service(flag_service, settings):
    from app.services.permissions import PermissionService

    return BootstrapService(
        registry_client=DummyRegistryClient(),
        flag_service=flag_service,
        permission_service=PermissionService(settings),
        cache=DummyCache(),
        cache_ttl_seconds=30,
        include_flag_prefixes=["orders.", "catalog.", "shell."],
        app_env="test",
        settings=settings,
    )


@pytest.mark.asyncio
async def test_orders_role_yields_orders_feature_only(monkeypatch):
    settings = BaseFakeSettings()

    monkeypatch.setattr("app.api.auth_runtime.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.bootstrap_service.get_settings", lambda: settings)

    token = _make_token(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view"],
            "scp": "access_as_user",
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        }
    )

    user = await runtime_authenticated_user(authorization=f"Bearer {token}")

    service = _build_service(DummyFlagService(), settings)

    bootstrap_payload = await service.build_bootstrap(user)
    runtime_payload = await service.build_runtime_features(user)

    assert user.roles == ["orders.view"]
    assert bootstrap_payload.permissions == ["orders.view"]
    assert runtime_payload.permissions == ["orders.view"]

    assert len(bootstrap_payload.features) == 1
    assert len(runtime_payload.features) == 1

    assert bootstrap_payload.features[0].featureKey == "orders"
    assert runtime_payload.features[0].featureKey == "orders"


@pytest.mark.asyncio
async def test_orders_and_catalog_roles_yield_both_features(monkeypatch):
    settings = BaseFakeSettings()

    monkeypatch.setattr("app.api.auth_runtime.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.bootstrap_service.get_settings", lambda: settings)

    token = _make_token(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view", "catalog.view"],
            "scp": "access_as_user",
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        }
    )

    user = await runtime_authenticated_user(authorization=f"Bearer {token}")

    service = _build_service(DummyFlagService(), settings)

    bootstrap_payload = await service.build_bootstrap(user)
    runtime_payload = await service.build_runtime_features(user)

    assert user.roles == ["orders.view", "catalog.view"]
    assert bootstrap_payload.permissions == ["orders.view", "catalog.view"]
    assert runtime_payload.permissions == ["orders.view", "catalog.view"]

    assert len(bootstrap_payload.features) == 2
    assert len(runtime_payload.features) == 2

    assert {feature.featureKey for feature in bootstrap_payload.features} == {
        "orders",
        "catalog",
    }
    assert {feature.featureKey for feature in runtime_payload.features} == {
        "orders",
        "catalog",
    }


@pytest.mark.asyncio
async def test_catalog_feature_hidden_when_flag_disabled(monkeypatch):
    settings = BaseFakeSettings()

    class FlagServiceWithCatalogDisabled:
        async def resolve_flags(self, required_flags: list[str]):
            return {
                "orders.enabled": True,
                "catalog.enabled": False,
                "shell.debug": True,
            }

    monkeypatch.setattr("app.api.auth_runtime.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.bootstrap_service.get_settings", lambda: settings)

    token = _make_token(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view", "catalog.view"],
            "scp": "access_as_user",
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        }
    )

    user = await runtime_authenticated_user(authorization=f"Bearer {token}")

    service = _build_service(FlagServiceWithCatalogDisabled(), settings)

    bootstrap_payload = await service.build_bootstrap(user)
    runtime_payload = await service.build_runtime_features(user)

    assert bootstrap_payload.permissions == ["orders.view", "catalog.view"]
    assert runtime_payload.permissions == ["orders.view", "catalog.view"]

    assert len(bootstrap_payload.features) == 1
    assert len(runtime_payload.features) == 1

    assert bootstrap_payload.features[0].featureKey == "orders"
    assert runtime_payload.features[0].featureKey == "orders"