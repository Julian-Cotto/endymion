"""Shared test fixtures.

The important one is settings-cache isolation. `get_settings()` is
@lru_cache'd, so the first test to touch it freezes the config for the whole
session — every later `monkeypatch.setenv("AUTH_...")` is silently ignored.

That was not theoretical: `test_items_denied_without_required_permission` set
roles to "other.view" and expected 403, but got 200 because the cached
settings still carried `lead-locator.view` from .env. Worse,
`test_items_allowed_with_platform_admin` *passed for the wrong reason* — it
never actually exercised the platform.admin path.

Clearing the caches around every test makes the env-var monkeypatching real.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.infrastructure.sources.config import get_source_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    get_source_settings.cache_clear()
    yield
    get_settings.cache_clear()
    get_source_settings.cache_clear()
