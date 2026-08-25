import jwt
import pytest
from fastapi import HTTPException

from app.api.auth_runtime import runtime_authenticated_user
from app.core.config import get_settings
from app.main import app


class BaseTestSettings:
    require_auth = True
    bootstrap_mode = "registry"
    auth_mode = "local"

    local_jwt_secret = "test-secret"
    local_jwt_algorithm = "HS256"

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

    dev_allow_debug_headers = True
    dev_default_roles = ["orders.view", "catalog.view"]

    @property
    def is_mock_auth(self):
        return self.auth_mode == "mock"

    @property
    def is_local_auth(self):
        return self.auth_mode == "local"

    @property
    def is_entra_auth(self):
        return self.auth_mode == "entra"


class LocalRegistrySettings(BaseTestSettings):
    pass


class LocalMockSettings(BaseTestSettings):
    bootstrap_mode = "mock"


class NoAuthSettings(BaseTestSettings):
    require_auth = False


class EntraSettings(BaseTestSettings):
    auth_mode = "entra"
    auth_allowed_algs = ["RS256"]
    auth_jwks_url = "https://login.microsoftonline.com/tenant/discovery/v2.0/keys"

    @property
    def is_local_auth(self):
        return False

    @property
    def is_entra_auth(self):
        return True


def _token() -> str:
    return jwt.encode(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view"],
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        },
        "test-secret",
        algorithm="HS256",
    )


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_runtime_user_requires_bearer_token_when_auth_enabled():
    app.dependency_overrides[get_settings] = lambda: LocalRegistrySettings()

    with pytest.raises(HTTPException) as exc:
        await runtime_authenticated_user(authorization=None)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Missing bearer token."


@pytest.mark.anyio
async def test_runtime_user_accepts_local_hs256_token():
    app.dependency_overrides[get_settings] = lambda: LocalRegistrySettings()

    user = await runtime_authenticated_user(
        authorization=f"Bearer {_token()}",
    )

    assert user.id == "u1"
    assert user.roles == ["orders.view"]


@pytest.mark.anyio
async def test_runtime_user_allows_local_debug_overrides_only_in_local_auth():
    app.dependency_overrides[get_settings] = lambda: LocalRegistrySettings()

    user = await runtime_authenticated_user(
        authorization=f"Bearer {_token()}",
        x_debug_user_id="debug-user",
        x_debug_roles="catalog.view",
    )

    assert user.id == "debug-user"
    assert user.roles == ["catalog.view"]


@pytest.mark.anyio
async def test_runtime_user_uses_mock_user_when_bootstrap_mock_and_local_auth():
    app.dependency_overrides[get_settings] = lambda: LocalMockSettings()

    user = await runtime_authenticated_user(
        authorization=None,
    )

    assert user.id == "local-dev"
    assert user.roles == ["orders.view", "catalog.view"]


@pytest.mark.anyio
async def test_runtime_user_uses_mock_user_when_auth_disabled():
    app.dependency_overrides[get_settings] = lambda: NoAuthSettings()

    user = await runtime_authenticated_user(
        authorization=None,
        x_debug_user_id="local-test",
        x_debug_roles="orders.view,catalog.view",
    )

    assert user.id == "local-test"
    assert user.roles == ["orders.view", "catalog.view"]


@pytest.mark.anyio
async def test_entra_mode_does_not_allow_debug_overrides(monkeypatch):
    app.dependency_overrides[get_settings] = lambda: EntraSettings()

    monkeypatch.setattr(
        "app.api.auth_runtime.decode_bearer_token",
        lambda token, settings: {
            "sub": "entra-user",
            "name": "Entra User",
            "email": "entra@example.com",
            "roles": ["orders.view"],
        },
    )

    with pytest.raises(HTTPException) as exc:
        await runtime_authenticated_user(
            authorization="Bearer fake-rs256-token",
            x_debug_user_id="debug-user",
            x_debug_roles="catalog.view",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Debug identity headers are not allowed when AUTH_MODE=entra."