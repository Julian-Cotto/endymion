import jwt
import pytest
from fastapi import HTTPException

from app.core.jwt_auth import (
    _jwks_clients,
    build_authenticated_user_from_claims,
    decode_bearer_token,
)


class FakeSettings:
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

    @property
    def is_local_auth(self):
        return self.auth_mode == "local"

    @property
    def is_entra_auth(self):
        return self.auth_mode == "entra"


def _make_token(payload: dict) -> str:
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_decode_bearer_token_accepts_expected_claims_without_jwks():
    token = _make_token(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view", "catalog.view"],
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        }
    )

    payload = decode_bearer_token(token, FakeSettings())

    assert payload["sub"] == "u1"
    assert payload["name"] == "Boris"
    assert payload["email"] == "boris@example.com"


def test_decode_bearer_token_rejects_wrong_issuer():
    token = _make_token(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view"],
            "iss": "https://wrong-issuer.example.com",
            "aud": "api://shell-bootstrap",
        }
    )

    with pytest.raises(HTTPException) as exc:
        decode_bearer_token(token, FakeSettings())

    assert exc.value.status_code == 401


def test_decode_bearer_token_rejects_wrong_audience():
    token = _make_token(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view"],
            "iss": "https://issuer.example.com",
            "aud": "api://wrong-audience",
        }
    )

    with pytest.raises(HTTPException) as exc:
        decode_bearer_token(token, FakeSettings())

    assert exc.value.status_code == 401


def test_build_authenticated_user_from_claims_uses_roles_claim_only():
    payload = {
        "sub": "u1",
        "name": "Boris",
        "email": "boris@example.com",
        "roles": ["orders.view", "catalog.view"],
        "groups": ["group-orders"],
        "scp": "orders.read",
        "wids": ["wid-admin"],
    }

    user = build_authenticated_user_from_claims(payload, FakeSettings())

    assert user.id == "u1"
    assert user.display_name == "Boris"
    assert user.email == "boris@example.com"
    assert user.roles == ["orders.view", "catalog.view"]


def test_decode_bearer_token_uses_jwks_client_when_configured(monkeypatch):
    class JwksSettings(FakeSettings):
        auth_mode = "entra"
        auth_jwks_url = "https://issuer.example.com/keys"
        auth_allowed_algs = ["RS256"]

        @property
        def is_local_auth(self):
            return False

        @property
        def is_entra_auth(self):
            return True

    token = "header.payload.signature"

    class FakeSigningKey:
        key = "public-key"

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, raw_token: str):
            assert raw_token == token
            return FakeSigningKey()

    monkeypatch.setitem(_jwks_clients, JwksSettings.auth_jwks_url, FakeJwksClient())

    monkeypatch.setattr(
        "app.core.jwt_auth.jwt.get_unverified_header",
        lambda raw_token: {"alg": "RS256"},
    )

    def fake_jwt_decode(
        raw_token,
        key=None,
        algorithms=None,
        audience=None,
        issuer=None,
        options=None,
    ):
        assert raw_token == token
        assert key == "public-key"
        assert algorithms == ["RS256"]
        assert audience == "api://shell-bootstrap"
        assert issuer == "https://issuer.example.com"
        assert options["verify_signature"] is True
        return {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["orders.view"],
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        }

    monkeypatch.setattr("app.core.jwt_auth.jwt.decode", fake_jwt_decode)

    payload = decode_bearer_token(token, JwksSettings())

    assert payload["sub"] == "u1"
    assert payload["aud"] == "api://shell-bootstrap"