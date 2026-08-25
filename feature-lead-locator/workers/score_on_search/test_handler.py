from .config import WorkerSettings
from .contract import WorkerEvent
from .handler import handle_event

def test_handle_event_executes_without_error() -> None:
    settings = WorkerSettings(feature_key="lead-locator", worker_name="score-on-search", trigger_kind="topic-subscription", topic_name="lead-locator", subscription_name="score-on-search", queue_name="", event_name="LeadSearchRequested", dead_letter_enabled=True, max_concurrency=2, max_retries=3, retry_backoff="exponential")
    handle_event(WorkerEvent(event_name="LeadSearchRequested", payload={"sample": True}, correlation_id="test"), settings)