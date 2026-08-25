from __future__ import annotations

from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.core.config import Settings
from app.services.claim_role_mapper import roles_from_claims


_jwks_clients: dict[str, PyJWKClient] = {}


def _get_required_claim(payload: dict[str, Any], claim_name: str) -> str:
    value = payload.get(claim_name)

    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing required claim: {claim_name}",
        )

    return value.strip()


def _get_optional_claim(payload: dict[str, Any], claim_name: str) -> str | None:
    value = payload.get(claim_name)

    if not isinstance(value, str) or not value.strip():
        return None

    return value.strip()


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    client = _jwks_clients.get(jwks_url)

    if client is None:
        client = PyJWKClient(jwks_url)
        _jwks_clients[jwks_url] = client

    return client


def _token_algorithm(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid bearer token header: {exc}",
        ) from exc

    alg = header.get("alg")

    if not isinstance(alg, str) or not alg.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing JWT algorithm.",
        )

    return alg.strip()


def _decode_local_hs256(token: str, settings: Settings) -> dict[str, Any]:
    expected_alg = settings.local_jwt_algorithm or "HS256"

    if expected_alg != "HS256":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Local auth must use HS256.",
        )

    if _token_algorithm(token) != "HS256":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid local token algorithm.",
        )

    if not settings.local_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LOCAL_JWT_SECRET is required for local auth.",
        )

    return jwt.decode(
        token,
        settings.local_jwt_secret,
        algorithms=["HS256"],
        audience=settings.auth_audience or None,
        issuer=settings.auth_issuer or None,
        options={
            "verify_signature": True,
            "verify_aud": bool(settings.auth_audience),
            "verify_iss": bool(settings.auth_issuer),
        },
    )


def _decode_entra_jwks(token: str, settings: Settings) -> dict[str, Any]:
    if _token_algorithm(token) != "RS256":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Entra token algorithm.",
        )

    if settings.auth_allowed_algs != ["RS256"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Entra auth must use RS256 only.",
        )

    if not settings.auth_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="AUTH_JWKS_URL is required for Entra auth.",
        )

    signing_key = _get_jwks_client(
        settings.auth_jwks_url,
    ).get_signing_key_from_jwt(token)

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.auth_audience,
        issuer=settings.auth_issuer,
        options={
            "verify_signature": True,
            "verify_aud": True,
            "verify_iss": True,
        },
    )


def decode_bearer_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        if settings.is_entra_auth:
            return _decode_entra_jwks(token, settings)

        if settings.is_local_auth:
            return _decode_local_hs256(token, settings)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported auth mode.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid bearer token: {exc}",
        ) from exc


def build_authenticated_user_from_claims(
    payload: dict[str, Any],
    settings: Settings,
):
    """
    Build the platform user context from validated JWT claims.

    Authorization model:

        token roles claim
          -> permission-shaped platform roles
          -> Bootstrap permissions

    Examples:

        roles: ["orders.view", "catalog.view"]
        roles: ["platform.admin"]

    Scopes are intentionally not converted into roles. The scope claim is used
    by token validation / API access policy, not business authorization.
    """

    from app.core.auth import AuthenticatedUser

    user_id = _get_required_claim(payload, settings.auth_user_id_claim)

    user_name = _get_optional_claim(
        payload,
        settings.auth_user_name_claim,
    )

    email = _get_optional_claim(
        payload,
        settings.auth_email_claim,
    )

    roles = roles_from_claims(payload, settings)

    return AuthenticatedUser(
        id=user_id,
        display_name=user_name,
        email=email,
        roles=roles,
        claims=payload,
    )