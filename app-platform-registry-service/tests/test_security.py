import pytest
from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.security import (
    Principal,
    get_principal_from_request,
    require_feature_scope,
    require_role,
)


def _request(authorization: str | None = None) -> Request:
    hdrs: list[tuple[bytes, bytes]] = []
    if authorization is not None:
        hdrs.append((b"authorization", authorization.encode("ascii")))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": hdrs,
            "query_string": b"",
            "client": ("testclient", 50000),
            "server": ("test", 80),
        }
    )


@pytest.fixture(autouse=True)
def reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_principal_auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    get_settings.cache_clear()
    p = get_principal_from_request(_request())
    assert p.subject == "local-dev"
    assert "registry.runtime.read" in p.roles
    assert "*" in p.claims.get("feature_keys", [])


def test_get_principal_shell_token(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    p = get_principal_from_request(_request("Bearer shell-read-token"))
    assert p.subject == "shell-runtime"
    assert "registry.runtime.read" in p.roles


def test_get_principal_pipeline_token(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    p = get_principal_from_request(_request("Bearer pipeline-write-token"))
    assert p.subject == "feature-pipeline-orders"
    assert "orders" in p.claims.get("feature_keys", [])


def test_get_principal_missing_bearer(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        get_principal_from_request(_request())
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_principal_invalid_token(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        get_principal_from_request(_request("Bearer not-a-real-token"))
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_require_role_ok():
    p = Principal("u", ["registry.runtime.read"], [], {})
    require_role(p, "registry.runtime.read")


def test_require_role_missing():
    p = Principal("u", [], [], {})
    with pytest.raises(HTTPException) as exc:
        require_role(p, "registry.runtime.read")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_require_feature_scope_wildcard():
    p = Principal("u", [], [], {"feature_keys": ["*"]})
    require_feature_scope(p, "anything-goes")


def test_require_feature_scope_explicit():
    p = Principal("u", [], [], {"feature_keys": ["orders"]})
    require_feature_scope(p, "orders")


def test_require_feature_scope_denied():
    p = Principal("u", [], [], {"feature_keys": ["catalog"]})
    with pytest.raises(HTTPException) as exc:
        require_feature_scope(p, "orders")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
