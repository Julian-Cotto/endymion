from .config import WorkerSettings
from .contract import WorkerEvent
from .handler import handle_event

from app.runtime.database import db_session
from app.schemas.report import ReportDefinitionIn
from app.services.reports import definitions, snapshots


def _settings() -> WorkerSettings:
    return WorkerSettings(
        feature_key="reports-layering",
        worker_name="snapshot-on-publish",
        trigger_kind="topic-subscription",
        topic_name="reports-layering",
        subscription_name="snapshot-on-publish",
        queue_name="",
        event_name="ReportDefinitionPublished",
        dead_letter_enabled=True,
        max_concurrency=2,
        max_retries=3,
        retry_backoff="exponential",
    )


def test_missing_slug_is_noop() -> None:
    # No slug in payload -> logs + returns, never raises.
    handle_event(
        WorkerEvent(event_name="ReportDefinitionPublished", payload={"sample": True}, correlation_id="t"),
        _settings(),
    )


def test_publish_event_refreshes_snapshot() -> None:
    slug = "worker-smoke-report"
    with db_session() as db:
        if not definitions.get_by_slug(db, slug):
            definitions.create_definition(
                db,
                ReportDefinitionIn(
                    title=slug,
                    slug=slug,
                    sql_text="SELECT a, b FROM t",
                    columns={"a": {"label": "A"}, "b": {"format": "int"}},
                    output_types=["table"],
                ),
                created_by="test",
            )

    handle_event(
        WorkerEvent(
            event_name="ReportDefinitionPublished",
            payload={"slug": slug},
            correlation_id="t",
        ),
        _settings(),
    )

    with db_session() as db:
        defn = definitions.get_by_slug(db, slug)
        snap = snapshots.latest_snapshot(db, defn.id)
        assert snap is not None
        assert snap.status == "ok"
