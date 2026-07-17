from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REPORTS_LAYERING_", extra="ignore")
    feature_key: str = "reports-layering"
    worker_name: str = "snapshot-on-publish"
    trigger_kind: str = "topic-subscription"
    topic_name: str = "reports-layering"
    subscription_name: str = "snapshot-on-publish"
    queue_name: str = ""
    event_name: str = "ReportDefinitionPublished"
    dead_letter_enabled: bool = True
    max_concurrency: int = 2
    max_retries: int = 3
    retry_backoff: str = "exponential"

@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()