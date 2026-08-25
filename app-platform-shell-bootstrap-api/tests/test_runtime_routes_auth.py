from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_runtime_features_allows_mock_mode_without_token():
    response = client.get("/api/runtime/features")
    assert response.status_code == 200


def test_shell_bootstrap_allows_mock_mode_without_token():
    response = client.get("/api/shell/bootstrap")
    assert response.status_code == 200