import jwt
import pytest
from fastapi import HTTPException

from app.core.jwt_auth import decode_bearer_token


class LocalHsSettings:
    auth_mode = "local"
    local_jwt_secret = "test-secret"
    local_jwt_algorithm = "HS256"

    auth_issuer = "https://issuer.example.com"
    auth_audience = "api://shell-bootstrap"
    auth_allowed_algs = ["HS256"]
    auth_jwks_url = ""

    @property
    def is_local_auth(self):
        return True

    @property
    def is_entra_auth(self):
        return False


class ProdRsSettings:
    auth_mode = "entra"

    local_jwt_secret = "test-secret"
    local_jwt_algorithm = "HS256"

    auth_issuer = "https://login.microsoftonline.com/tenant-id/v2.0"
    auth_audience = "api://api-client-id"
    auth_allowed_algs = ["RS256"]
    auth_jwks_url = "https://login.microsoftonline.com/tenant-id/discovery/v2.0/keys"

    @property
    def is_local_auth(self):
        return False

    @property
    def is_entra_auth(self):
        return True


def test_local_hs256_token_is_allowed_without_jwks():
    token = jwt.encode(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["developer"],
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        },
        "test-secret",
        algorithm="HS256",
    )

    payload = decode_bearer_token(token, LocalHsSettings())

    assert payload["sub"] == "u1"


def test_local_rejects_token_signed_with_wrong_secret():
    token = jwt.encode(
        {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "roles": ["developer"],
            "iss": "https://issuer.example.com",
            "aud": "api://shell-bootstrap",
        },
        "wrong-secret",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc:
        decode_bearer_token(token, LocalHsSettings())

    assert exc.value.status_code == 401


def test_local_rejects_non_hs256_algorithm(monkeypatch):
    monkeypatch.setattr(
        "app.core.jwt_auth.jwt.get_unverified_header",
        lambda raw_token: {"alg": "none"},
    )

    with pytest.raises(HTTPException) as exc:
        decode_bearer_token("header.payload.signature", LocalHsSettings())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid local token algorithm."


def test_prod_rs256_requires_jwks(monkeypatch):
    token = "header.payload.signature"

    class FakeSigningKey:
        key = "public-key"

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, raw_token):
            assert raw_token == token
            return FakeSigningKey()

    monkeypatch.setattr(
        "app.core.jwt_auth._get_jwks_client",
        lambda url: FakeJwksClient(),
    )

    monkeypatch.setattr(
        "app.core.jwt_auth.jwt.get_unverified_header",
        lambda raw_token: {"alg": "RS256"},
    )

    def fake_decode(
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
        assert audience == "api://api-client-id"
        assert issuer == "https://login.microsoftonline.com/tenant-id/v2.0"
        assert options["verify_signature"] is True
        return {
            "sub": "u1",
            "name": "Boris",
            "email": "boris@example.com",
            "iss": "https://login.microsoftonline.com/tenant-id/v2.0",
            "aud": "api://api-client-id",
        }

    monkeypatch.setattr("app.core.jwt_auth.jwt.decode", fake_decode)

    payload = decode_bearer_token(token, ProdRsSettings())

    assert payload["sub"] == "u1"


def test_prod_rejects_non_rs256_algorithm(monkeypatch):
    monkeypatch.setattr(
        "app.core.jwt_auth.jwt.get_unverified_header",
        lambda raw_token: {"alg": "HS256"},
    )

    with pytest.raises(HTTPException) as exc:
        decode_bearer_token("header.payload.signature", ProdRsSettings())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid Entra token algorithm."


def test_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        decode_bearer_token("not-a-jwt", LocalHsSettings())

    assert exc.value.status_code == 401