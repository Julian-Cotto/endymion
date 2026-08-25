from app.schemas.registry_manifest import RegistryManifest


def test_registry_manifest_contract_accepts_expected_shape() -> None:
    manifest = RegistryManifest.model_validate(
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
        }
    )

    assert manifest.featureKey == "catalog"
    assert manifest.frontend.entryUrl == "http://localhost:3300/src/bootstrap-entry.tsx"
    assert manifest.backend.apiBaseUrl == "http://localhost:8200/api/catalog"