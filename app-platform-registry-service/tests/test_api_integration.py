from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app

from tests.factories import sample_manifest_dict


def test_publish_release(client):
    r = client.post("/api/releases", json=sample_manifest_dict())
    assert r.status_code == 200
    body = r.json()
    assert body["featureKey"] == "orders"
    assert body["version"] == "1.0.0"
    assert body["status"] == "candidate"
    assert "id" in body


def test_publish_release_duplicate_returns_same(client):
    client.post("/api/releases", json=sample_manifest_dict())
    r2 = client.post("/api/releases", json=sample_manifest_dict())
    assert r2.status_code == 200
    r1 = client.post("/api/releases", json=sample_manifest_dict())
    assert r1.json()["id"] == r2.json()["id"]


def test_publish_release_manifest_validation_400(client):
    bad = sample_manifest_dict(version="not-semver")
    r = client.post("/api/releases", json=bad)
    assert r.status_code == 400
    assert "semver" in r.json()["detail"].lower()


def test_publish_release_pydantic_422(client):
    bad = sample_manifest_dict(featureKey="INVALID")
    r = client.post("/api/releases", json=bad)
    assert r.status_code == 422


def test_activate_release(client):
    client.post("/api/releases", json=sample_manifest_dict())
    r = client.post(
        "/api/admin/features/orders/versions/1.0.0/activate",
        params={"environment": "local"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "active"
    assert body["activatedAt"] is not None


def test_activate_release_not_found(client):
    r = client.post(
        "/api/admin/features/orders/versions/9.9.9/activate",
        params={"environment": "local"},
    )
    assert r.status_code == 404


def test_runtime_features_after_activation(client):
    client.post("/api/releases", json=sample_manifest_dict())
    client.post(
        "/api/admin/features/orders/versions/1.0.0/activate",
        params={"environment": "local"},
    )
    r = client.get("/api/runtime/features", params={"environment": "local"})
    assert r.status_code == 200
    data = r.json()
    assert data["environment"] == "local"
    assert len(data["features"]) == 1
    assert data["features"][0]["featureKey"] == "orders"
    assert data["features"][0]["auth"]["mode"] == "entra"
    assert data["features"][0]["auth"]["tokenForwarding"] is True
    assert data["features"][0]["auth"]["tokenStrategy"] == "forwarded-bearer"


def test_runtime_features_empty(client):
    r = client.get("/api/runtime/features", params={"environment": "staging"})
    assert r.status_code == 200
    assert r.json()["features"] == []


def test_publish_feature_scope_forbidden(db_session, monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            body = sample_manifest_dict(featureKey="catalog")
            r = client.post(
                "/api/releases",
                json=body,
                headers={"Authorization": "Bearer pipeline-write-token"},
            )
        assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
