import pytest
from jsonschema import ValidationError

from feature_scaffold.manifest_validator import validate_manifest_dict


def test_manifest_schema_rejects_invalid_version() -> None:
    manifest = {
        "featureKey": "orders",
        "version": "v1",
        "displayName": "Orders",
        "description": "",
        "basePath": "/orders",
        "navigation": {
            "label": "Orders",
            "icon": "package"
        },
        "frontend": {
            "enabled": True,
            "entryStrategy": "vite-dynamic-import",
            "entryUrl": "/features/orders/assets/bootstrap.js",
            "mountFunction": "mount"
        },
        "backend": {
            "enabled": True,
            "baseUrl": "/api/orders",
            "healthEndpoint": "/api/orders/health"
        },
        "auth": {
            "required": True,
            "mode": "mock",
            "tokenStrategy": "forwarded-bearer"
        },
        "registry": {
            "enabled": True,
            "mode": "rest"
        },
        "events": {
            "publishes": [],
            "consumes": []
        },
        "workers": {
            "scheduledJobs": [],
            "eventDrivenJobs": [],
            "eventListeners": []
        }
    }

    with pytest.raises(ValidationError):
        validate_manifest_dict(manifest)