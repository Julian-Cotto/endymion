import pytest

from app.core.config import Settings


def test_local_auth_settings_are_valid():
    settings = Settings(
        app_env="local",
        auth_mode="local",
        local_jwt_secret="local-dev-secret",
        local_jwt_algorithm="HS256",
    )

    settings.validate_auth_config()

    assert settings.is_local_auth is True
    assert settings.is_entra_auth is False


def test_local_auth_rejects_non_hs256():
    settings = Settings(
        app_env="local",
        auth_mode="local",
        local_jwt_secret="local-dev-secret",
        local_jwt_algorithm="RS256",
    )

    with pytest.raises(ValueError, match="Local auth must use HS256"):
        settings.validate_auth_config()


def test_local_auth_requires_secret():
    settings = Settings(
        app_env="local",
        auth_mode="local",
        local_jwt_secret="",
        local_jwt_algorithm="HS256",
    )

    with pytest.raises(ValueError, match="LOCAL_JWT_SECRET is required"):
        settings.validate_auth_config()


def test_invalid_auth_mode_is_rejected():
    settings = Settings(
        app_env="local",
        auth_mode="invalid",
    )

    with pytest.raises(ValueError, match="AUTH_MODE must be one of: mock, local, entra"):
        settings.validate_auth_config()


def test_entra_auth_requires_required_settings():
    settings = Settings(
        app_env="prod",
        auth_mode="entra",
        dev_allow_debug_headers=False,
        auth_issuer="",
        auth_audience="",
        auth_jwks_url="",
    )

    with pytest.raises(ValueError, match="Missing required Entra auth settings"):
        settings.validate_auth_config()


def test_entra_auth_rejects_non_rs256():
    tenant_id = "00000000-0000-0000-0000-000000000000"

    settings = Settings(
        app_env="prod",
        auth_mode="entra",
        dev_allow_debug_headers=False,
        auth_issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        auth_audience="api://bootstrap-api",
        auth_jwks_url=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        auth_allowed_algs_csv="HS256",
    )

    with pytest.raises(ValueError, match="Entra auth must use RS256 only"):
        settings.validate_auth_config()


def test_entra_auth_settings_are_valid():
    tenant_id = "00000000-0000-0000-0000-000000000000"

    settings = Settings(
        app_env="prod",
        auth_mode="entra",
        dev_allow_debug_headers=False,
        auth_issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        auth_audience="api://bootstrap-api",
        auth_jwks_url=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        auth_allowed_algs_csv="RS256",
    )

    settings.validate_auth_config()

    assert settings.is_entra_auth is True
    assert settings.is_local_auth is False