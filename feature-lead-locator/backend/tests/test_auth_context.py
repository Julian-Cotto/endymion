import pytest

from app.platform.auth_context import extract_auth_context
from app.config import get_settings


@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    # Force mock mode for tests
    monkeypatch.setenv("AUTH_MODE", "mock")
    monkeypatch.setenv("AUTH_DEBUG_HEADERS_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEFAULT_DEV_ROLES_RAW", "lead-locator.view")


def test_mock_context_defaults():
    ctx = extract_auth_context(
        authorization_header=None,
    )

    assert ctx.is_authenticated is True
    assert ctx.user_id == "dev-user"
    assert ctx.user_name == "Local Dev User"
    assert "lead-locator.view" in ctx.roles


def test_debug_roles_override():
    ctx = extract_auth_context(
        authorization_header=None,
        debug_roles="lead-locator.view,lead-locator.edit",
    )

    assert ctx.is_authenticated is True
    assert "lead-locator.view" in ctx.roles
    assert "lead-locator.edit" in ctx.roles


def test_roles_are_permission_shaped():
    ctx = extract_auth_context(
        authorization_header=None,
        debug_roles="lead-locator.view",
    )

    # No mapping should happen
    assert ctx.roles == ["lead-locator.view"]


def test_no_scope_to_role_mapping():
    # There is intentionally no scope → role conversion anymore
    ctx = extract_auth_context(
        authorization_header=None,
        debug_roles="lead-locator.view",
    )

    assert "access_as_user" not in ctx.roles


def test_platform_admin_passthrough():
    ctx = extract_auth_context(
        authorization_header=None,
        debug_roles="platform.admin",
    )

    assert ctx.roles == ["platform.admin"]