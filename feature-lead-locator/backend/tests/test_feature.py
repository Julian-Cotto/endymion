from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    # Asserts the snake_case HealthResponse from app/api/health.py, which is
    # the route that actually serves: main.py includes health_router before
    # feature_router under the same prefix. This previously asserted
    # "featureKey" against a shadowed, unreachable duplicate in feature.py
    # (since removed). The frontend's BackendHealthCard reads feature_key too.
    response = client.get("/api/leads/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["feature_key"] == "lead-locator"
    assert body["service"] == "Lead Locator Service"


def test_me_allowed_with_default_mock_role(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "mock")
    monkeypatch.setenv("AUTH_DEBUG_HEADERS_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEFAULT_DEV_ROLES_RAW", "lead-locator.view")
    monkeypatch.setenv("AUTH_REQUIRED_PERMISSIONS_RAW", "lead-locator.view")

    response = client.get("/api/leads/me")

    assert response.status_code == 200
    body = response.json()
    assert body["isAuthenticated"] is True
    assert "lead-locator.view" in body["roles"]


def test_items_allowed_with_debug_role(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "mock")
    monkeypatch.setenv("AUTH_DEBUG_HEADERS_ENABLED", "true")
    monkeypatch.setenv("AUTH_REQUIRED_PERMISSIONS_RAW", "lead-locator.view")

    response = client.get(
        "/api/leads/items",
        headers={
            "X-Debug-Roles": "lead-locator.view",
        },
    )

    assert response.status_code == 200
    assert response.json()["featureKey"] == "lead-locator"


def test_items_denied_without_required_permission(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "mock")
    monkeypatch.setenv("AUTH_DEBUG_HEADERS_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEFAULT_DEV_ROLES_RAW", "other.view")
    monkeypatch.setenv("AUTH_REQUIRED_PERMISSIONS_RAW", "lead-locator.view")

    response = client.get("/api/leads/items")

    assert response.status_code == 403
    assert response.json()["detail"]["message"] == "Insufficient permissions"
    assert response.json()["detail"]["requiredPermissions"] == [
        "lead-locator.view"
    ]


def test_items_allowed_with_platform_admin(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "mock")
    monkeypatch.setenv("AUTH_DEBUG_HEADERS_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEFAULT_DEV_ROLES_RAW", "platform.admin")
    monkeypatch.setenv("AUTH_REQUIRED_PERMISSIONS_RAW", "lead-locator.view")

    response = client.get("/api/leads/items")

    assert response.status_code == 200
    assert response.json()["featureKey"] == "lead-locator"