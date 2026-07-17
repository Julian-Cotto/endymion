from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class JobSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REPORTS_LAYERING_", extra="ignore")
    feature_key: str = "reports-layering"
    job_name: str = "refresh-report-snapshots"
    schedule: str = "0 * * * *"
    log_level: str = "INFO"

@lru_cache(maxsize=1)
def get_job_settings() -> JobSettings:
    return JobSettings()