from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


LOCAL_ENVIRONMENTS = {"local", "dev", "development", "test"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "Reports Layering Service"
    feature_key: str = "reports-layering"
    api_base_path: str = "/api/reports"

    app_environment: str = "local"

    auth_mode: str = "entra"
    registry_mode: str = "rest"
    backend_token_strategy: str = "forwarded-bearer"

    allowed_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:3200,http://localhost:3300,http://localhost:5173"
    )

    # ------------------------------------------------------------------
    # Local/mock auth
    # ------------------------------------------------------------------
    auth_debug_headers_enabled: bool = True
    auth_default_dev_user_id: str = "dev-user"
    auth_default_dev_user_name: str = "Local Dev User"
    auth_default_dev_email: str = "dev@example.local"

    # Permission-shaped local roles.
    # These should match Entra app role values used in production.
    auth_default_dev_roles_raw: str = "reports-layering.view"

    # ------------------------------------------------------------------
    # Permission convention
    # ------------------------------------------------------------------
    # Entra app role value == platform permission.
    #
    # Examples:
    #   reports-layering.view
    #   reports-layering.create
    #   reports-layering.edit
    #   platform.admin
    #
    # No role-permission map.
    # No scope-permission map.
    platform_admin_role: str = "platform.admin"

    # Default permission used by generated sample endpoints.
    auth_required_permissions_raw: str = "reports-layering.view"

    # ------------------------------------------------------------------
    # Entra token validation
    # ------------------------------------------------------------------
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_audience: str = ""
    entra_allowed_audiences_raw: str = ""
    entra_jwks_url: str = ""
    entra_issuer: str = ""
    entra_allowed_issuers_raw: str = ""
    entra_require_https_metadata: bool = True
    entra_clock_skew_seconds: int = 60

    @property
    def normalized_app_environment(self) -> str:
        return self.app_environment.strip().lower() or "local"

    @property
    def is_local_environment(self) -> bool:
        return self.normalized_app_environment in LOCAL_ENVIRONMENTS

    @property
    def normalized_auth_mode(self) -> str:
        return self.auth_mode.strip().lower()

    @property
    def allowed_origins(self) -> list[str]:
        return [v.strip() for v in self.allowed_origins_raw.split(",") if v.strip()]

    @property
    def auth_default_dev_roles(self) -> list[str]:
        return [
            v.strip()
            for v in self.auth_default_dev_roles_raw.split(",")
            if v.strip()
        ]

    @property
    def auth_required_permissions(self) -> list[str]:
        return [
            v.strip()
            for v in self.auth_required_permissions_raw.split(",")
            if v.strip()
        ]

    @property
    def effective_entra_audiences(self) -> list[str]:
        explicit = [
            v.strip()
            for v in self.entra_allowed_audiences_raw.split(",")
            if v.strip()
        ]

        if explicit:
            return explicit

        audience = self.entra_audience.strip()
        if audience:
            return [audience]

        client_id = self.entra_client_id.strip()
        if client_id:
            return [client_id]

        return []

    @property
    def effective_entra_audience(self) -> str:
        audiences = self.effective_entra_audiences
        return audiences[0] if audiences else ""

    @property
    def effective_entra_issuers(self) -> list[str]:
        explicit = [
            v.strip()
            for v in self.entra_allowed_issuers_raw.split(",")
            if v.strip()
        ]

        if explicit:
            return explicit

        issuer = self.entra_issuer.strip()
        if issuer:
            return [issuer]

        tenant_id = self.entra_tenant_id.strip()
        if not tenant_id:
            return []

        return [
            f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            f"https://sts.windows.net/{tenant_id}/",
        ]

    @property
    def effective_entra_issuer(self) -> str:
        issuers = self.effective_entra_issuers
        return issuers[0] if issuers else ""

    @property
    def effective_entra_jwks_url(self) -> str:
        if self.entra_jwks_url.strip():
            return self.entra_jwks_url.strip()

        tenant_id = self.entra_tenant_id.strip()
        if not tenant_id:
            return ""

        return f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    def validate_runtime_safety(self) -> None:
        if self.is_local_environment:
            if self.normalized_auth_mode == "entra" and self.auth_debug_headers_enabled:
                raise ValueError(
                    "AUTH_DEBUG_HEADERS_ENABLED must be false when AUTH_MODE=entra."
                )
            return

        if self.normalized_auth_mode in {"none", "mock"}:
            raise ValueError(
                "Unsafe auth configuration: AUTH_MODE=none/mock is only allowed "
                "when APP_ENVIRONMENT is local/dev/development/test."
            )

        if self.normalized_auth_mode != "entra":
            raise ValueError(
                f"Unsupported production auth mode: {self.auth_mode}. "
                "Use AUTH_MODE=entra."
            )

        if self.auth_debug_headers_enabled:
            raise ValueError(
                "AUTH_DEBUG_HEADERS_ENABLED must be false in non-local environments."
            )

        missing = []
        if not self.effective_entra_audiences:
            missing.append("ENTRA_AUDIENCE or ENTRA_ALLOWED_AUDIENCES_RAW")
        if not self.effective_entra_issuers:
            missing.append("ENTRA_ISSUER, ENTRA_ALLOWED_ISSUERS_RAW, or ENTRA_TENANT_ID")
        if not self.effective_entra_jwks_url:
            missing.append("ENTRA_JWKS_URL or ENTRA_TENANT_ID")

        if missing:
            raise ValueError(
                "Missing required production Entra settings: "
                + ", ".join(missing)
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime_safety()
    return settings