import pytest
from pydantic import ValidationError

from app.schemas.manifest import ReleaseManifestIn


def _minimal_valid() -> dict:
    return {
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
        "nav": {"label": "Orders"},
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
        "metadata": {"ownerTeam": "platform"},
    }


def test_release_manifest_in_valid():
    m = ReleaseManifestIn.model_validate(_minimal_valid())
    assert m.featureKey == "orders"
    assert m.environment == "local"
    assert m.auth.mode == "entra"
    assert m.auth.tokenForwarding is True


def test_release_manifest_defaults_auth_for_backward_compatibility():
    data = _minimal_valid()
    data.pop("auth")

    m = ReleaseManifestIn.model_validate(data)

    assert m.auth.mode == "mock"
    assert m.auth.tokenForwarding is False


def test_auth_mode_invalid():
    with pytest.raises(ValidationError, match="auth.mode"):
        ReleaseManifestIn.model_validate(
            {
                **_minimal_valid(),
                "auth": {
                    "required": True,
                    "mode": "invalid",
                    "shellAuthRequired": True,
                    "tokenForwarding": True,
                    "tokenStrategy": "forwarded-bearer",
                    "allowedDevModes": ["mock"],
                    "roles": [],
                },
            }
        )


def test_feature_key_invalid():
    with pytest.raises(ValidationError, match="featureKey"):
        ReleaseManifestIn.model_validate({**_minimal_valid(), "featureKey": "Bad_Key"})


def test_environment_invalid():
    with pytest.raises(ValidationError, match="environment"):
        ReleaseManifestIn.model_validate({**_minimal_valid(), "environment": "space"})


def test_route_must_start_with_slash():
    with pytest.raises(ValidationError, match="route"):
        ReleaseManifestIn.model_validate({**_minimal_valid(), "route": "no-slash"})


def test_authorization_permissions_format():
    with pytest.raises(ValidationError, match="requiredPermissions"):
        ReleaseManifestIn.model_validate(
            {
                **_minimal_valid(),
                "authorization": {
                    "requiredPermissions": ["INVALID"],
                    "requiredFlags": ["orders.enabled"],
                },
            }
        )


def test_authorization_flags_format():
    with pytest.raises(ValidationError, match="requiredFlags"):
        ReleaseManifestIn.model_validate(
            {
                **_minimal_valid(),
                "authorization": {
                    "requiredPermissions": ["orders.view"],
                    "requiredFlags": ["BADFLAG"],
                },
            }
        )


def test_authorization_empty_permissions_rejected():
    with pytest.raises(ValidationError):
        ReleaseManifestIn.model_validate(
            {
                **_minimal_valid(),
                "authorization": {"requiredPermissions": [], "requiredFlags": ["orders.enabled"]},
            }
        )


def test_authorization_empty_flags_rejected_by_model_validator():
    with pytest.raises(ValidationError, match="requiredFlags"):
        ReleaseManifestIn.model_validate(
            {
                **_minimal_valid(),
                "authorization": {
                    "requiredPermissions": ["orders.view"],
                    "requiredFlags": [],
                },
            }
        )


def test_dedupe_permissions_and_flags():
    m = ReleaseManifestIn.model_validate(
        {
            **_minimal_valid(),
            "authorization": {
                "requiredPermissions": ["orders.view", " orders.view ", ""],
                "requiredFlags": ["orders.enabled", "orders.enabled"],
            },
        }
    )
    assert m.authorization.requiredPermissions == ["orders.view"]
    assert m.authorization.requiredFlags == ["orders.enabled"]