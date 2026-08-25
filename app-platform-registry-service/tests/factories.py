"""Test payloads shared across API and service tests."""


def sample_manifest_dict(**overrides: object) -> dict:
    data: dict = {
        "manifestVersion": "1.0",
        "featureKey": "orders",
        "displayName": "Orders",
        "version": "1.0.0",
        "environment": "local",
        "route": "/orders",
        "frontend": {
            "type": "module",
            "entryUrl": "http://localhost:3200/app.js",
        },
        "backend": {"apiBaseUrl": "http://localhost:8100/api"},
        "nav": {"label": "Orders", "icon": "package", "order": 10},
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
        "compatibility": {"shellContractMin": "v1"},
        "metadata": {"ownerTeam": "platform"},
    }
    data.update(overrides)
    return data