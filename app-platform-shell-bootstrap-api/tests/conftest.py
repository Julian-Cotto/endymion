import os

import pytest

os.environ["APP_ENV"] = "local"
os.environ["BOOTSTRAP_MODE"] = "mock"
os.environ["REQUIRE_AUTH"] = "false"
os.environ["AUTH_MODE"] = "local"
os.environ["LOCAL_JWT_SECRET"] = "test-secret"
os.environ["LOCAL_JWT_ALGORITHM"] = "HS256"
os.environ["AUTH_ISSUER"] = "https://issuer.example.com"
os.environ["AUTH_AUDIENCE"] = "api://shell-bootstrap"
os.environ["AUTH_ALLOWED_ALGS_CSV"] = "HS256"
os.environ["AUTH_JWKS_URL"] = ""


class TestSettings:
    require_auth = True
    bootstrap_mode = "registry"
    auth_mode = "local"

    local_jwt_secret = "test-secret"
    local_jwt_algorithm = "HS256"

    auth_issuer = "https://issuer.example.com"
    auth_audience = "api://shell-bootstrap"
    auth_allowed_algs = ["HS256"]

    auth_roles_claim = "roles"
    auth_groups_claim = "groups"
    auth_scope_claim = "scp"
    auth_wids_claim = "wids"
    auth_user_id_claim = "sub"
    auth_user_name_claim = "name"
    auth_email_claim = "email"
    auth_jwks_url = ""

    direct_role_allow_list = ["developer", "admin", "orders.view", "catalog.view"]
    group_role_map = {}
    scope_role_map = {}
    wid_role_map = {}
    role_permission_map = {
        "developer": ["orders.view", "catalog.view"],
        "orders.view": ["orders.view"],
        "catalog.view": ["catalog.view"],
        "admin": ["*"],
    }
    default_permissions = []

    @property
    def is_local_auth(self):
        return self.auth_mode == "local"

    @property
    def is_entra_auth(self):
        return self.auth_mode == "entra"


@pytest.fixture(autouse=True)
def clear_settings_caches():
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()
    except Exception:
        pass

    yield

    try:
        from app.core.config import get_settings

        get_settings.cache_clear()
    except Exception:
        pass