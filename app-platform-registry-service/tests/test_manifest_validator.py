import pytest

from app.schemas.manifest import ReleaseManifestIn
from app.services.manifest_validator import ManifestValidationError, ManifestValidator


def _manifest(**overrides) -> ReleaseManifestIn:
    data = {
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
        "metadata": {"ownerTeam": "platform"},
    }
    data.update(overrides)
    return ReleaseManifestIn.model_validate(data)


def test_validate_ok():
    v = ManifestValidator({"localhost"}, {"localhost"})
    v.validate(_manifest())


def test_invalid_semver():
    v = ManifestValidator({"localhost"}, {"localhost"})
    m = _manifest(version="2.x")
    with pytest.raises(ManifestValidationError, match="semver"):
        v.validate(m)


def test_frontend_host_not_allowed():
    v = ManifestValidator({"localhost"}, {"localhost"})
    m = _manifest(
        frontend={"type": "module", "entryUrl": "http://evil.com/x.js"},
        backend={"apiBaseUrl": "http://localhost:8100/api"},
    )
    with pytest.raises(ManifestValidationError, match="frontend host"):
        v.validate(m)


def test_api_host_not_allowed():
    v = ManifestValidator({"localhost"}, {"localhost"})
    m = _manifest(
        frontend={"type": "module", "entryUrl": "http://localhost:3200/x.js"},
        backend={"apiBaseUrl": "http://evil.com/api"},
    )
    with pytest.raises(ManifestValidationError, match="api host"):
        v.validate(m)


def test_frontend_type_not_module():
    v = ManifestValidator({"localhost"}, {"localhost"})
    m = _manifest(frontend={"type": "iframe", "entryUrl": "http://localhost:3200/x.js"})
    with pytest.raises(ManifestValidationError, match="module"):
        v.validate(m)


def test_invalid_permission_pattern():
    v = ManifestValidator({"localhost"}, {"localhost"})
    m = _manifest()
    m.authorization.requiredPermissions = ["bad"]
    with pytest.raises(ManifestValidationError, match="permission"):
        v.validate(m)


def test_invalid_flag_pattern():
    v = ManifestValidator({"localhost"}, {"localhost"})
    m = _manifest()
    m.authorization.requiredFlags = ["bad"]
    with pytest.raises(ManifestValidationError, match="flag"):
        v.validate(m)


def test_empty_permissions_after_mutate():
    v = ManifestValidator({"localhost"}, {"localhost"})
    m = _manifest()
    m.authorization.requiredPermissions = []
    with pytest.raises(ManifestValidationError, match="requiredPermissions"):
        v.validate(m)


def test_empty_flags_after_mutate():
    v = ManifestValidator({"localhost"}, {"localhost"})
    m = _manifest()
    m.authorization.requiredFlags = []
    with pytest.raises(ManifestValidationError, match="requiredFlags"):
        v.validate(m)
