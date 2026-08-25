from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Portal Registry Service"
    app_version: str = "1.0.0"
    environment_name: str = "local"
    debug: bool = False

    database_url: str = Field(
        "postgresql+psycopg://registry:registry@localhost:5433/portal_registry",
        alias="DATABASE_URL",
    )

    allowed_frontend_hosts: str = "localhost,127.0.0.1"
    allowed_api_hosts: str = "localhost,127.0.0.1"

    shell_read_audiences: str = "api://portal-registry-runtime"
    pipeline_write_audiences: str = "api://portal-registry-admin"

    auth_disabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    def frontend_hosts_set(self) -> set[str]:
        return {
            item.strip()
            for item in self.allowed_frontend_hosts.split(",")
            if item.strip()
        }

    def api_hosts_set(self) -> set[str]:
        return {
            item.strip()
            for item in self.allowed_api_hosts.split(",")
            if item.strip()
        }

    def shell_audiences_set(self) -> set[str]:
        return {
            item.strip()
            for item in self.shell_read_audiences.split(",")
            if item.strip()
        }

    def pipeline_audiences_set(self) -> set[str]:
        return {
            item.strip()
            for item in self.pipeline_write_audiences.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()