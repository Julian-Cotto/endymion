from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEAD_LOCATOR_", extra="ignore")
    feature_key: str = "lead-locator"
    worker_name: str = "score-on-search"
    trigger_kind: str = "topic-subscription"
    topic_name: str = "lead-locator"
    subscription_name: str = "score-on-search"
    queue_name: str = ""
    event_name: str = "LeadSearchRequested"
    dead_letter_enabled: bool = True
    max_concurrency: int = 2
    max_retries: int = 3
    retry_backoff: str = "exponential"

@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()