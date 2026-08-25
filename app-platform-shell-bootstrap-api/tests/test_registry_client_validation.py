import pytest
from pydantic import ValidationError

from app.schemas.registry_manifest import RegistryManifest
from app.services.registry_client import RegistryClient


class FakeSettings:
    registry_base_url = "http://registry.local"


def test_registry_client_rejects_invalid_manifest_shape():
    client = RegistryClient(FakeSettings())

    raw_features = [
        {
            "featureKey": "orders",
            # displayName missing on purpose
            "route": "/orders",
            "version": "1.0.0",
            "nav": {"label": "Orders", "icon": "package"},
            "frontend": {
                "enabled": True,
                "entryUrl": "http://localhost:3200/src/bootstrap-entry.tsx",
            },
            "backend": {
                "enabled": True,
                "apiBaseUrl": "http://localhost:8100/api/orders",
            },
        }
    ]

    extracted = client._extract_feature_list(raw_features)

    with pytest.raises(ValidationError):
        [
            RegistryManifest.model_validate(item).model_dump()
            for item in extracted
        ]