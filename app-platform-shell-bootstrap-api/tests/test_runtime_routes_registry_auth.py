from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


class RegistryAuthSettings:
    require_auth = True
    bootstrap_mode = "registry"
    auth_mode = "local"

    @property
    def is_local_auth(self):
        return True

    @property
    def is_entra_auth(self):
        return False


def test_runtime_features_requires_token_in_registry_mode():
    app.dependency_overrides[get_settings] = lambda: RegistryAuthSettings()

    try:
        response = client.get("/api/runtime/features")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_shell_bootstrap_requires_token_in_registry_mode():
    app.dependency_overrides[get_settings] = lambda: RegistryAuthSettings()

    try:
        response = client.get("/api/shell/bootstrap")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()