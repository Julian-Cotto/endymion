import pytest
from fastapi.testclient import TestClient

from app.main import app
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
                "nav": {
                    "label": "Orders",
                    "icon": "package",
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
                    "required": True,
                    "mode": "mock",
                    "shellAuthRequired": True,
                    "tokenForwarding": False,
                },
            },
            {
                "featureKey": "catalog",
                "displayName": "Catalog",
                "route": "/catalog",
                "version": "1.0.0",
                "nav": {
                    "label": "Catalog",
                    "icon": "boxes",
                },
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
                    "mode": "mock",
                    "shellAuthRequired": True,
                    "tokenForwarding": False,
                },
            },
        ]


class DummyFlagService:
    async def resolve_flags(self, required_flags: list[str]):
        return {
            "orders.enabled": True,
            "catalog.enabled": False,
            "shell.debug": True,
        }


class DummyPermissionService:
    def get_permissions(self, user):
        return ["orders.view"]


class DummyCache:
    async def get_or_set(self, key, ttl, factory):
        return await factory()


@pytest.mark.asyncio
async def test_bootstrap_service_registry_mode_end_to_end(monkeypatch):
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
        include_flag_prefixes=["orders.", "catalog.", "shell."],
        app_env="test",
    )

    user = AuthenticatedUser(
        id="u1",
        display_name="Test User",
        email="test@example.com",
        roles=["orders.view"],
        claims={},
    )

    bootstrap_payload = await service.build_bootstrap(user)
    runtime_payload = await service.build_runtime_features(user)

    assert bootstrap_payload.environment == "test"
    assert runtime_payload.environment == "test"

    assert len(bootstrap_payload.features) == 1
    assert len(runtime_payload.features) == 1

    assert bootstrap_payload.features[0].featureKey == "orders"
    assert runtime_payload.features[0].featureKey == "orders"

    assert bootstrap_payload.features[0].frontend.entryUrl == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert runtime_payload.features[0].frontend.entryUrl == "http://localhost:3200/src/bootstrap-entry.tsx"

    assert bootstrap_payload.features[0].backend.apiBaseUrl == "http://localhost:8100/api/orders"
    assert runtime_payload.features[0].backend.apiBaseUrl == "http://localhost:8100/api/orders"

    assert bootstrap_payload.flags["orders.enabled"] is True
    assert runtime_payload.flags["orders.enabled"] is True

    assert bootstrap_payload.metadata.source == "bootstrap-service-registry"
    assert runtime_payload.metadata.source == "runtime-service-registry"


def test_runtime_and_bootstrap_routes_exist():
    client = TestClient(app)

    bootstrap_response = client.get("/api/shell/bootstrap")
    runtime_response = client.get("/api/runtime/features")

    assert bootstrap_response.status_code == 200
    assert runtime_response.status_code == 200

    bootstrap_payload = bootstrap_response.json()
    runtime_payload = runtime_response.json()

    assert "environment" in bootstrap_payload
    assert "features" in bootstrap_payload
    assert "flags" in bootstrap_payload
    assert "metadata" in bootstrap_payload

    assert "environment" in runtime_payload
    assert "features" in runtime_payload
    assert "flags" in runtime_payload
    assert "metadata" in runtime_payload