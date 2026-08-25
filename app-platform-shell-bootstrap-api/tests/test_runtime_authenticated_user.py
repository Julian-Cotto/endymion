import jwt
import pytest
from fastapi import HTTPException

from app.api.auth_runtime import runtime_authenticated_user


def _make_token(payload: dict) -> str:
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.mark.asyncio
async def test_runtime_authenticated_user_uses_debug_headers_in_mock_mode(monkeypatch):
    class FakeSettings:
        bootstrap_mode = "mock"
        auth_jwks_url = ""

    monkeypatch.setattr(
        "app.api.auth_runtime.get_settings",
        lambda: FakeSettings(),
    )

    user = await runtime_authenticated_user(
        authorization=None,
        x_debug_user_id="u1",
        x_debug_user_name="Boris",
        x_debug_email="boris@example.com",
        x_debug_roles="orders.view,catalog.view",
    )

    assert user.id == "u1"
    assert user.display_name == "Boris"
    assert user.email == "boris@example.com"
    assert user.roles == ["orders.view", "catalog.view"]


@pytest.mark.asyncio
async def test_runtime_authenticated_user_defaults_in_mock_mode(monkeypatch):
    class FakeSettings:
        bootstrap_mode = "mock"
        auth_jwks_url = ""

    monkeypatch.setattr(
        "app.api.auth_runtime.get_settings",
        lambda: FakeSettings(),
    )

    user = await runtime_authenticated_user()

    assert user.id == "local-dev"
    assert user.display_name == "Local Developer"
    assert user.email == "dev@local"
    assert user.roles == ["orders.view", "catalog.view"]


@pytest.mark.asyncio
async def test_runtime_authenticated_user_requires_bearer_token_in_registry_mode(monkeypatch):
    class FakeSettings:
        bootstrap_mode = "registry"
        auth_issuer = "https://issuer.example.com"
        auth_audience = "api://shell-bootstrap"
        auth_allowed_algs = ["HS256"]
        auth_roles_claim = "roles"
        auth_groups_claim = "groups"
        auth_scope_claim = "scp"
        auth_wids_claim = "wids"
        auth_user_id_claim = "sub"
        auth_user_name_claim = "name"
        auth_email_claim = "email"
        auth_jwks_url = ""

    monkeypatch.setattr(
        "app.api.auth_runtime.get_settings",
        lambda: FakeSettings(),
    )

    with pytest.raises(HTTPException) as exc:
        await runtime_authenticated_user()

    assert exc.value.status_code == 401
    assert exc.value.detail == "Missing bearer token."


@pytest.mark.asyncio
async def test_runtime_authenticated_user_accepts_bearer_token_in_registry_mode(monkeypatch):
    class FakeSettings:
        bootstrap_mode = "registry"
        auth_issuer = "https://issuer.example.com"
        auth_audience = "api://shell-bootstrap"
        auth_allowed_algs = ["HS256"]
        auth_roles_claim = "roles"
        auth_groups_claim = "groups"
        auth_scope_claim = "scp"
        auth_wids_claim = "wids"
        auth_user_id_claim = "sub"
        auth_user_name_claim = "name"
        auth_email_claim = "email"
        auth_jwks_url = ""

    monkeypatch.setattr(
        "app.api.auth_runtime.get_settings",
        lambda: FakeSettings(),
    )

    token = _make_token(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view", "catalog.view"],
            "groups": ["group-orders"],
            "scp": "orders.read",
            "wids": ["wid-admin"],
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        }
    )

    user = await runtime_authenticated_user(
        authorization=f"Bearer {token}",
    )

    assert user.id == "u1"
    assert user.display_name == "Boris"
    assert user.email == "boris@example.com"
    assert user.roles == ["orders.view", "catalog.view"]
    assert user.claims["sub"] == "u1"