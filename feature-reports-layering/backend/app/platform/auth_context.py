from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger("auth")


@dataclass(slots=True)
class AuthContext:
    is_authenticated: bool
    user_id: str | None = None
    user_name: str | None = None
    email: str | None = None
    roles: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    raw_token: str | None = None
    auth_mode: str = "none"
    claims: dict[str, Any] = field(default_factory=dict)


# Backward-compatible alias for older generated code/tests.
RequestAuthContext = AuthContext


def _log_auth_event(event: str, context: AuthContext, **extra: Any) -> None:
    logger.info(
        event,
        extra={
            "event": event,
            "user_id": context.user_id,
            "user_name": context.user_name,
            "email": context.email,
            "roles": context.roles,
            "groups": context.groups,
            "auth_mode": context.auth_mode,
            **extra,
        },
    )


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized in seen:
            continue

        seen.add(normalized)
        result.append(normalized)

    return result


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None

    prefix = "bearer "
    if not authorization_header.lower().startswith(prefix):
        return None

    token = authorization_header[len(prefix):].strip()
    return token or None


def _normalize_roles(claims: dict[str, Any]) -> list[str]:
    """
    Extract permission-shaped roles from token claims.

    Platform rule:

        Entra app role value == platform permission

    Example:
        roles: ["{{ names.feature_key }}.view", "{{ names.feature_key }}.edit"]

    Scopes are intentionally not converted into roles.
    """
    raw_roles = claims.get("roles")

    if not isinstance(raw_roles, list):
        return []

    return _dedupe(
        [str(item).strip() for item in raw_roles if str(item).strip()]
    )


def _normalize_groups(claims: dict[str, Any]) -> list[str]:
    raw_groups = claims.get("groups")

    if not isinstance(raw_groups, list):
        return []

    return _dedupe(
        [str(item).strip() for item in raw_groups if str(item).strip()]
    )


def _build_context_from_claims(
    *,
    claims: dict[str, Any],
    raw_token: str,
    auth_mode: str,
) -> AuthContext:
    roles = _normalize_roles(claims)

    user_id = (
        claims.get("oid")
        or claims.get("sub")
        or claims.get("preferred_username")
        or claims.get("unique_name")
        or claims.get("appid")
    )
    user_name = (
        claims.get("name")
        or claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("unique_name")
        or claims.get("appid")
    )
    email = (
        claims.get("preferred_username")
        or claims.get("email")
        or claims.get("upn")
        or claims.get("unique_name")
    )

    return AuthContext(
        is_authenticated=True,
        user_id=str(user_id) if user_id else None,
        user_name=str(user_name) if user_name else None,
        email=str(email) if email else None,
        roles=roles,
        groups=_normalize_groups(claims),
        raw_token=raw_token,
        auth_mode=auth_mode,
        claims=claims,
    )


def _extract_none_context() -> AuthContext:
    ctx = AuthContext(
        is_authenticated=True,
        user_id="anonymous",
        user_name="anonymous",
        auth_mode="none",
    )
    _log_auth_event("auth_context_created_none", ctx)
    return ctx


def _extract_mock_context(
    *,
    authorization_header: str | None,
    debug_user_id: str | None,
    debug_user_name: str | None,
    debug_email: str | None,
    debug_roles: str | None,
) -> AuthContext:
    settings = get_settings()
    token = _extract_bearer_token(authorization_header)

    if settings.auth_debug_headers_enabled:
        user_id = debug_user_id or settings.auth_default_dev_user_id
        user_name = debug_user_name or settings.auth_default_dev_user_name
        email = debug_email or settings.auth_default_dev_email
        roles = _split_csv(debug_roles) or settings.auth_default_dev_roles
    else:
        user_id = settings.auth_default_dev_user_id
        user_name = settings.auth_default_dev_user_name
        email = settings.auth_default_dev_email
        roles = settings.auth_default_dev_roles

    claims = {
        "dev_mode": True,
        "roles": roles,
    }

    ctx = AuthContext(
        is_authenticated=True,
        user_id=user_id,
        user_name=user_name,
        email=email,
        roles=_dedupe(roles),
        groups=[],
        raw_token=token,
        auth_mode="mock",
        claims=claims,
    )
    _log_auth_event("auth_context_created_mock", ctx)
    return ctx


def _get_signing_key_for_token(raw_token: str):
    settings = get_settings()
    jwks_url = settings.effective_entra_jwks_url

    if not jwks_url:
        logger.error("auth_entra_jwks_missing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entra JWKS configuration is missing.",
        )

    jwk_client = jwt.PyJWKClient(jwks_url)
    return jwk_client.get_signing_key_from_jwt(raw_token).key


def _validate_issuer(claims: dict[str, Any]) -> None:
    settings = get_settings()
    allowed_issuers = settings.effective_entra_issuers

    if not allowed_issuers:
        logger.error("auth_entra_issuer_missing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entra issuer configuration is missing.",
        )

    issuer = claims.get("iss")
    if issuer not in allowed_issuers:
        logger.warning(
            "auth_entra_invalid_issuer",
            extra={
                "issuer": issuer,
                "allowed_issuers": allowed_issuers,
            },
        )
        raise jwt.InvalidIssuerError("Access token issuer is invalid.")


def _validate_entra_token(raw_token: str) -> dict[str, Any]:
    settings = get_settings()

    audiences = settings.effective_entra_audiences
    if not audiences:
        logger.error("auth_entra_audience_missing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entra audience configuration is missing.",
        )

    try:
        signing_key = _get_signing_key_for_token(raw_token)

        claims = jwt.decode(
            raw_token,
            signing_key,
            algorithms=["RS256"],
            audience=audiences,
            leeway=settings.entra_clock_skew_seconds,
            options={
                "require": ["exp", "iat", "iss", "aud"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": False,
            },
        )

        _validate_issuer(claims)
        return claims

    except jwt.ExpiredSignatureError as exc:
        logger.warning("auth_entra_token_expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
        ) from exc
    except jwt.InvalidAudienceError as exc:
        logger.warning("auth_entra_invalid_audience")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token audience is invalid.",
        ) from exc
    except jwt.InvalidIssuerError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token issuer is invalid.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("auth_entra_invalid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is invalid.",
        ) from exc


def _extract_entra_context(authorization_header: str | None) -> AuthContext:
    raw_token = _extract_bearer_token(authorization_header)

    if not raw_token:
        logger.warning("auth_entra_missing_bearer_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required.",
        )

    claims = _validate_entra_token(raw_token)

    ctx = _build_context_from_claims(
        claims=claims,
        raw_token=raw_token,
        auth_mode="entra",
    )
    _log_auth_event("auth_context_created_entra", ctx)
    return ctx


def extract_auth_context(
    *,
    authorization_header: str | None,
    debug_user_id: str | None = None,
    debug_user_name: str | None = None,
    debug_email: str | None = None,
    debug_roles: str | None = None,
) -> AuthContext:
    mode = get_settings().auth_mode.strip().lower()

    if mode == "none":
        return _extract_none_context()

    if mode == "mock":
        return _extract_mock_context(
            authorization_header=authorization_header,
            debug_user_id=debug_user_id,
            debug_user_name=debug_user_name,
            debug_email=debug_email,
            debug_roles=debug_roles,
        )

    if mode == "entra":
        if debug_user_id or debug_user_name or debug_email or debug_roles:
            logger.warning("auth_entra_debug_headers_rejected")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debug identity headers are not allowed when AUTH_MODE=entra.",
            )

        return _extract_entra_context(authorization_header)

    logger.error("auth_unsupported_mode", extra={"auth_mode": mode})
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unsupported auth mode: {mode}",
    )


def require_authenticated_user(
    auth_context: AuthContext,
) -> AuthContext:
    if not auth_context.is_authenticated:
        logger.warning("auth_denied_unauthenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )

    _log_auth_event("auth_authenticated", auth_context)
    return auth_context