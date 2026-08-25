from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_runtime_features_endpoint_exists() -> None:
    response = client.get("/api/runtime/features")
    assert response.status_code == 200

    payload = response.json()
    assert "environment" in payload
    assert "features" in payload
    assert "flags" in payload
    assert "metadata" in payload