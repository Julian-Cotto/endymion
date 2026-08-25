from fastapi.testclient import TestClient

from app.main import create_app


def test_health_ok():
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "service" in body
    assert body["environment"] == "local"
