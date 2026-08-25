from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core platform ---
    bootstrap_mode: str = "mock"
    app_env: str = "local"

    registry_base_url: str = ""
    app_configuration_endpoint: str = ""
    app_configuration_label: str = ""

    # --- Cache ---
    cache_backend: str = "memory"
    cache_ttl_seconds: int = 30
    redis_url: str = ""

    # --- Flags ---
    include_flag_prefixes_csv: str = "shell.,orders.,catalog."

    # --- Mock features ---
    mock_features_json: str = "[]"

    # --- CORS ---
    cors_allow_origins_csv: str = (
        "http://localhost:3000,"
        "http://localhost:3200,"
        "http://localhost:3300,"
        "http://localhost:5173"
    )

    # --- Auth ---
    #
    # Supported values:
    #   mock  - local/dev identity, optional debug headers
    #   local - local signed JWT validation, optional debug headers
    #   entra - production Entra/JWKS validation, no debug overrides
    auth_mode: str = "mock"
    require_auth: bool = True

    # --- Mock/local dev auth controls ---
    #
    # These are intentionally allowed only for AUTH_MODE=mock or AUTH_MODE=local.
    # They must never be enabled for AUTH_MODE=entra.
    dev_default_roles_csv: str = "orders.view,catalog.view"
    dev_allow_debug_headers: bool = True

    # --- Local JWT validation ---
    local_jwt_secret: str = "local-dev-secret"
    local_jwt_algorithm: str = "HS256"

    # --- Entra / JWT validation ---
    auth_issuer: str = ""
    auth_audience: str = ""
    auth_allowed_algs_csv: str = "RS256"
    auth_roles_claim: str = "roles"
    auth_groups_claim: str = "groups"
    auth_scope_claim: str = "scp"
    auth_wids_claim: str = "wids"
    auth_user_id_claim: str = "sub"
    auth_user_name_claim: str = "name"
    auth_email_claim: str = "email"
    auth_jwks_url: str = ""

    # --- Permission naming convention ---
    #
    # Entra app roles are permission-shaped:
    #   orders.view
    #   catalog.view
    #   platform.admin
    #
    # Bootstrap does not store role -> permission mappings.
    # Bootstrap treats token roles directly as permissions.
    platform_admin_role: str = "platform.admin"

    @property
    def normalized_auth_mode(self) -> str:
        return self.auth_mode.lower().strip()

    @property
    def is_mock_auth(self) -> bool:
        return self.normalized_auth_mode == "mock"

    @property
    def is_local_auth(self) -> bool:
        return self.normalized_auth_mode == "local"

    @property
    def is_entra_auth(self) -> bool:
        return self.normalized_auth_mode == "entra"

    @property
    def include_flag_prefixes(self) -> list[str]:
        return [
            item.strip()
            for item in self.include_flag_prefixes_csv.split(",")
            if item.strip()
        ]

    @property
    def bootstrap_include_flag_prefix_list(self) -> list[str]:
        return self.include_flag_prefixes

    @property
    def mock_features(self) -> list[dict]:
        if not self.mock_features_json.strip():
            return []
        return json.loads(self.mock_features_json)

    @property
    def auth_allowed_algs(self) -> list[str]:
        return [
            item.strip()
            for item in self.auth_allowed_algs_csv.split(",")
            if item.strip()
        ]

    @property
    def cors_allow_origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.cors_allow_origins_csv.split(",")
            if item.strip()
        ]

    @property
    def dev_default_roles(self) -> list[str]:
        return [
            item.strip()
            for item in self.dev_default_roles_csv.split(",")
            if item.strip()
        ]

    def validate_auth_config(self) -> None:
        auth_mode = self.normalized_auth_mode

        if auth_mode not in {"mock", "local", "entra"}:
            raise ValueError("AUTH_MODE must be one of: mock, local, entra")

        if auth_mode == "mock":
            return

        if auth_mode == "local":
            if self.local_jwt_algorithm != "HS256":
                raise ValueError("Local auth must use HS256")

            if not self.local_jwt_secret:
                raise ValueError("LOCAL_JWT_SECRET is required for local auth")

            return

        # AUTH_MODE=entra is production-grade token validation.
        # Debug overrides and legacy mapping variables are intentionally rejected.
        if self.dev_allow_debug_headers:
            raise ValueError(
                "DEV_ALLOW_DEBUG_HEADERS must be false when AUTH_MODE=entra"
            )

        legacy_mapping_values = {
            "SCOPE_ROLE_MAP_JSON": getattr(self, "scope_role_map_json", None),
            "ROLE_PERMISSION_MAP_JSON": getattr(self, "role_permission_map_json", None),
            "GROUP_ROLE_MAP_JSON": getattr(self, "group_role_map_json", None),
            "WID_ROLE_MAP_JSON": getattr(self, "wid_role_map_json", None),
            "DIRECT_ROLE_ALLOW_LIST_CSV": getattr(self, "direct_role_allow_list_csv", None),
            "DEFAULT_PERMISSIONS_CSV": getattr(self, "default_permissions_csv", None),
        }

        configured_legacy_values = [
            name
            for name, value in legacy_mapping_values.items()
            if isinstance(value, str) and value.strip() not in {"", "{}"}
        ]

        if configured_legacy_values:
            raise ValueError(
                "Legacy role/permission mapping is not allowed when AUTH_MODE=entra: "
                + ", ".join(configured_legacy_values)
            )

        missing = [
            name
            for name, value in {
                "AUTH_ISSUER": self.auth_issuer,
                "AUTH_AUDIENCE": self.auth_audience,
                "AUTH_JWKS_URL": self.auth_jwks_url,
            }.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "Missing required Entra auth settings: " + ", ".join(missing)
            )

        if self.auth_allowed_algs != ["RS256"]:
            raise ValueError("Entra auth must use RS256 only")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_auth_config()
    return settings