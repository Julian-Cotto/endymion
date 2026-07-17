import logging

from .config import JobSettings
from app.runtime.database import db_session
from app.services.reports import definitions, snapshots

logger = logging.getLogger("reports.job.refresh")


def run_job(settings: JobSettings) -> dict:
    """Refresh a cached snapshot for every active report definition.

    Each report is refreshed independently — a failing query is captured as an
    error snapshot (see refresh_snapshot) and never aborts the batch.
    """
    logger.info(
        "job_start",
        extra={"event": "job_start", "feature_key": settings.feature_key,
               "job": settings.job_name, "schedule": settings.schedule},
    )
    ok = failed = 0
    with db_session() as db:
        for defn in definitions.list_definitions(db):
            if defn.status != "active":
                continue
            snap = snapshots.refresh_snapshot(db, defn)
            snapshots.prune_snapshots(db, defn.id)
            if snap.status == "ok":
                ok += 1
            else:
                failed += 1
                logger.warning(
                    "snapshot_error",
                    extra={"event": "snapshot_error", "slug": defn.slug, "error": snap.error},
                )

    result = {"refreshed": ok, "failed": failed}
    logger.info("job_done", extra={"event": "job_done", **result})
    return result
