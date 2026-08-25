from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class JobSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEAD_LOCATOR_", extra="ignore")
    feature_key: str = "lead-locator"
    job_name: str = "refresh-source-caches"
    schedule: str = "0 3 * * *"
    log_level: str = "INFO"

@lru_cache(maxsize=1)
def get_job_settings() -> JobSettings:
    return JobSettings()