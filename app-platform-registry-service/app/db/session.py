from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


@lru_cache(maxsize=8)
def _engine_for_url(database_url: str):
    return create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=8)
def _sessionmaker_for_url(database_url: str):
    return sessionmaker(
        bind=_engine_for_url(database_url),
        autoflush=False,
        autocommit=False,
        future=True,
    )


def SessionLocal():
    """Return a new ORM session (same call style as a sessionmaker instance)."""
    url = get_settings().database_url
    return _sessionmaker_for_url(url)()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
