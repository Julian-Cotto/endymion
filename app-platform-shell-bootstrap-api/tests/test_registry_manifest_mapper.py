from app.schemas.registry_manifest import RegistryManifest
from app.services.registry_manifest_mapper import (
    registry_manifest_to_bootstrap_feature,
    registry_manifest_to_runtime_feature,
)


def _sample_manifest() -> RegistryManifest:
    return RegistryManifest.model_validate(
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
        }
    )


def test_registry_manifest_to_bootstrap_feature() -> None:
    manifest = _sample_manifest()

    result = registry_manifest_to_bootstrap_feature(manifest)

    assert result.featureKey == "orders"
    assert result.displayName == "Orders"
    assert result.route == "/orders"
    assert result.frontend.entryUrl == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert result.backend.apiBaseUrl == "http://localhost:8100/api/orders"
    assert result.authorization.requiredPermissions == ["orders.view"]


def test_registry_manifest_to_runtime_feature() -> None:
    manifest = _sample_manifest()

    result = registry_manifest_to_runtime_feature(manifest)

    assert result.featureKey == "orders"
    assert result.displayName == "Orders"
    assert result.route == "/orders"
    assert result.frontend.entryUrl == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert result.backend.apiBaseUrl == "http://localhost:8100/api/orders"
    assert result.authorization.requiredFlags == ["orders.enabled"]