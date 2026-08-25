from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, HTTPException, status

from app.core.auth import AuthenticatedUser
from app.core.config import Settings, get_settings
from app.core.jwt_auth import build_authenticated_user_from_claims, decode_bearer_token


@dataclass
class RuntimeAuthSettingsAdapter:
    raw: Any

    @property
    def require_auth(self) -> bool:
        return bool(getattr(self.raw, "require_auth", True))

    @property
    def bootstrap_mode(self) -> str:
        return str(getattr(self.raw, "bootstrap_mode", "registry"))

    @property
    def auth_mode(self) -> str:
        return str(getattr(self.raw, "auth_mode", "local")).lower().strip()

    @property
    def is_mock_auth(self) -> bool:
        value = getattr(self.raw, "is_mock_auth", None)
        if isinstance(value, bool):
            return value
        if callable(value):
            return bool(value())
        return self.auth_mode == "mock"

    @property
    def is_local_auth(self) -> bool:
        value = getattr(self.raw, "is_local_auth", None)
        if isinstance(value, bool):
            return value
        if callable(value):
            return bool(value())
        return self.auth_mode == "local"

    @property
    def is_entra_auth(self) -> bool:
        value = getattr(self.raw, "is_entra_auth", None)
        if isinstance(value, bool):
            return value
        if callable(value):
            return bool(value())
        return self.auth_mode == "entra"

    @property
    def dev_allow_debug_headers(self) -> bool:
        return bool(getattr(self.raw, "dev_allow_debug_headers", True))

    @property
    def dev_default_roles(self) -> list[str]:
        value = getattr(self.raw, "dev_default_roles", ["orders.view", "catalog.view"])
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return ["orders.view", "catalog.view"]

    def __getattr__(self, name: str) -> Any:
        defaults = {
            "local_jwt_secret": "test-secret",
            "local_jwt_algorithm": "HS256",
            "auth_issuer": "https://issuer.example.com",
            "auth_audience": "api://shell-bootstrap",
            "auth_allowed_algs": ["HS256"],
            "auth_roles_claim": "roles",
            "auth_groups_claim": "groups",
            "auth_scope_claim": "scp",
            "auth_wids_claim": "wids",
            "auth_user_id_claim": "sub",
            "auth_user_name_claim": "name",
            "auth_email_claim": "email",
            "auth_jwks_url": "",
            "platform_admin_role": "platform.admin",
        }

        if hasattr(self.raw, name):
            return getattr(self.raw, name)
        if name in defaults:
            return defaults[name]
        raise AttributeError(name)


def _normalize_header_value(value) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return None


def _split_csv(value) -> list[str]:
    value = _normalize_header_value(value)
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _extract_bearer_token(authorization: str | None) -> str:
    authorization = _normalize_header_value(authorization)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token.",
        )

    return token


def _build_mock_user(
    settings: RuntimeAuthSettingsAdapter | Settings,
    user_id: str | None,
    user_name: str | None,
    email: str | None,
    roles: list[str],
) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user_id or "local-dev",
        display_name=user_name or "Local Developer",
        email=email or "dev@local",
        roles=roles or settings.dev_default_roles,
        claims={},
    )


def _apply_debug_overrides(
    user: AuthenticatedUser,
    user_id: str | None,
    user_name: str | None,
    email: str | None,
    roles: list[str],
) -> AuthenticatedUser:
    if user_id:
        user.id = user_id
    if user_name:
        user.display_name = user_name
    if email:
        user.email = email
    if roles:
        user.roles = roles
    return user


def _has_runtime_settings_contract(settings: Any) -> bool:
    return all(
        hasattr(settings, attr)
        for attr in (
            "require_auth",
            "bootstrap_mode",
            "is_mock_auth",
            "is_local_auth",
            "is_entra_auth",
            "dev_allow_debug_headers",
            "dev_default_roles",
            "auth_user_id_claim",
            "auth_user_name_claim",
            "auth_email_claim",
            "local_jwt_secret",
            "local_jwt_algorithm",
        )
    )


def _resolve_settings(settings: Any):
    if _has_runtime_settings_contract(settings):
        return settings

    try:
        from app.main import app

        override = app.dependency_overrides.get(get_settings)
        if override is not None:
            overridden = override()
            if _has_runtime_settings_contract(overridden):
                return overridden
            return RuntimeAuthSettingsAdapter(overridden)
    except Exception:
        pass

    resolved = get_settings()
    if _has_runtime_settings_contract(resolved):
        return resolved
    return RuntimeAuthSettingsAdapter(resolved)


async def runtime_authenticated_user(
    authorization: str | None = Header(default=None),
    x_debug_user_id: str | None = Header(default=None),
    x_debug_user_name: str | None = Header(default=None),
    x_debug_email: str | None = Header(default=None),
    x_debug_roles: str | None = Header(default=None),
    settings: Settings | None = Depends(get_settings),
) -> AuthenticatedUser:
    settings = _resolve_settings(settings)

    user_id = _normalize_header_value(x_debug_user_id)
    user_name = _normalize_header_value(x_debug_user_name)
    email = _normalize_header_value(x_debug_email)
    debug_roles = _split_csv(x_debug_roles)

    if settings.is_entra_auth and (
        user_id or user_name or email or debug_roles
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debug identity headers are not allowed when AUTH_MODE=entra.",
        )

    if not settings.require_auth:
        return _build_mock_user(settings, user_id, user_name, email, debug_roles)

    if settings.is_mock_auth or settings.bootstrap_mode == "mock":
        if not settings.dev_allow_debug_headers and (
            user_id or user_name or email or debug_roles
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debug identity headers are disabled.",
            )

        return _build_mock_user(settings, user_id, user_name, email, debug_roles)

    token = _extract_bearer_token(authorization)
    payload = decode_bearer_token(token, settings)
    user = build_authenticated_user_from_claims(payload, settings)

    if settings.is_local_auth and settings.dev_allow_debug_headers:
        return _apply_debug_overrides(
            user=user,
            user_id=user_id,
            user_name=user_name,
            email=email,
            roles=debug_roles,
        )

    return user