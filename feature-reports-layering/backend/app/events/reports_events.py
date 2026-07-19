"""Build + publish reports-layering domain events from ORM objects."""
from __future__ import annotations

from app.events import publisher
from app.models.report import ReportDefinition, ReportSnapshot

REPORT_PUBLISHED = "reports-layering.report-published"
SNAPSHOT_REFRESHED = "reports-layering.snapshot-refreshed"


def _source_summary(defn: ReportDefinition) -> tuple[int, list[str]]:
    sources = defn.sources or []
    if sources:
        return len(sources), sorted({s.source_type for s in sources})
    # Legacy single inline SQL counts as one sql source.
    return (1, ["sql"]) if defn.sql_text else (0, [])


def report_published(defn: ReportDefinition, *, actor: str | None = None) -> None:
    count, types = _source_summary(defn)
    publisher.publish_event(
        REPORT_PUBLISHED,
        {
            "slug": defn.slug,
            "title": defn.title,
            "version": defn.version,
            "status": defn.status,
            "source_count": count,
            "source_types": types,
            "has_combine": defn.combine is not None,
            "actor": actor,
        },
    )


def snapshot_refreshed(defn: ReportDefinition, snap: ReportSnapshot) -> None:
    count, types = _source_summary(defn)
    publisher.publish_event(
        SNAPSHOT_REFRESHED,
        {
            "slug": defn.slug,
            "snapshot_status": snap.status,
            "row_count": snap.row_count,
            "elapsed_ms": snap.elapsed_ms,
            "source_count": count,
            "source_types": types,
        },
    )
