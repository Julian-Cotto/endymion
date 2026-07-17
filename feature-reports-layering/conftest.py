"""Shared pytest setup for backend + jobs + workers.

Runs everything offline: a throwaway SQLite metadata DB, mock auth (debug
headers), and Snowflake in mock mode (synthetic snapshot rows). Applied to
the whole `scripts/validate.sh` run, which invokes one pytest process over
backend/tests and each job/worker package.
"""
from __future__ import annotations

import os
import tempfile

import pytest

_DB_PATH = os.path.join(tempfile.gettempdir(), "reports_layering_test.db")

# Must be set before any `app.*` import binds the SQLAlchemy engine.
os.environ.setdefault("APP_ENVIRONMENT", "local")
os.environ.setdefault("AUTH_MODE", "mock")
os.environ.setdefault("AUTH_DEBUG_HEADERS_ENABLED", "true")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_PATH}")
# Force Snowflake mock so tests never hit a real warehouse even if the
# developer's .env has live DATABASE_* creds (SnowflakeSettings reads .env).
os.environ["DATABASE_MODE_OVERRIDE"] = "mock"

# Fresh DB each run.
if os.path.exists(_DB_PATH):
    os.remove(_DB_PATH)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    from app.platform.database.base import Base
    from app.platform.database.session import engine
    import app.models  # noqa: F401 — register ORM tables

    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _fresh_settings():
    """Clear the cached Settings so tests that monkeypatch env are isolated."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
