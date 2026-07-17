import logging

from .config import WorkerSettings
from .contract import WorkerEvent
from app.runtime.database import db_session
from app.services.reports import definitions, snapshots

logger = logging.getLogger("reports.worker.snapshot_on_publish")


def handle_event(event: WorkerEvent, settings: WorkerSettings) -> None:
    """On ReportDefinitionPublished, refresh that one report immediately so the
    author sees output without waiting for the scheduled batch."""
    slug = (event.payload or {}).get("slug")
    if not slug:
        logger.warning(
            "missing_slug",
            extra={"event": "missing_slug", "correlation_id": event.correlation_id},
        )
        return

    with db_session() as db:
        defn = definitions.get_by_slug(db, slug)
        if defn is None:
            logger.warning("unknown_report", extra={"event": "unknown_report", "slug": slug})
            return
        snap = snapshots.refresh_snapshot(db, defn)
        snapshots.prune_snapshots(db, defn.id)
        logger.info(
            "snapshot_refreshed",
            extra={"event": "snapshot_refreshed", "slug": slug,
                   "status": snap.status, "row_count": snap.row_count,
                   "correlation_id": event.correlation_id},
        )
