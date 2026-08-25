from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.main import app


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://registry:registry@127.0.0.1:5433/portal_registry",
)


def truncate_database(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE audits, releases, features "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture(scope="session")
def postgres_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    engine.dispose()


@pytest.fixture
def db_session(postgres_engine):
    SessionLocal = sessionmaker(
        bind=postgres_engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )

    truncate_database(postgres_engine)

    session = SessionLocal()

    try:
        yield session
    finally:
        try:
            session.rollback()
        except Exception:
            pass

        session.close()
        truncate_database(postgres_engine)


@pytest.fixture
def client(postgres_engine):
    truncate_database(postgres_engine)

    with TestClient(app) as c:
        yield c

    truncate_database(postgres_engine)