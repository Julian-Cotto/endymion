import pytest

from app.schemas.registry_manifest import RegistryManifest
from app.services.registry_client import RegistryClient


class FakeSettings:
    registry_base_url = "http://registry.local"


@pytest.mark.asyncio
async def test_extract_feature_list_from_top_level_list():
    client = RegistryClient(FakeSettings())

    payload = [
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
        }
    ]

    result = client._extract_feature_list(payload)
    assert isinstance(result, list)
    assert result[0]["featureKey"] == "orders"


@pytest.mark.asyncio
async def test_extract_feature_list_from_features_envelope():
    client = RegistryClient(FakeSettings())

    payload = {
        "features": [
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
            }
        ]
    }

    result = client._extract_feature_list(payload)
    assert isinstance(result, list)
    assert result[0]["featureKey"] == "catalog"


@pytest.mark.asyncio
async def test_extract_feature_list_raises_for_unknown_shape():
    client = RegistryClient(FakeSettings())

    with pytest.raises(ValueError):
        client._extract_feature_list({"unexpected": []})


def test_registry_manifest_validation_accepts_valid_shape():
    payload = {
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
    }

    manifest = RegistryManifest.model_validate(payload)
    assert manifest.featureKey == "orders"