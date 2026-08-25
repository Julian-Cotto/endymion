from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import ReportDefinition, ReportSource
from app.schemas.report import ReportDefinitionIn, SourceSpec
from app.services.reports import datasets
from app.services.reports.slugs import unique_slug
from app.services.reports.sql_guard import (
    SqlValidationError,
    extract_param_names,
    validate_read_only,
)


class DefinitionError(ValueError):
    """Raised when a report definition is invalid (bad SQL or params)."""


def _validate_sql(sql: str, declared: set[str], *, label: str = "SQL") -> str:
    """Validate + normalize one read-only SELECT; ensure its params are declared."""
    try:
        cleaned = validate_read_only(sql)
    except SqlValidationError as exc:
        raise DefinitionError(f"{label}: {exc}") from exc
    referenced = extract_param_names(cleaned)
    missing = referenced - declared
    if missing:
        raise DefinitionError(
            f"{label} references undeclared params: {', '.join(sorted(missing))}."
        )
    return cleaned


def _validate(db: Session, payload: ReportDefinitionIn) -> None:
    """Validate SQL for the legacy single source and every SQL-typed source, and
    confirm each file source points at an existing uploaded dataset.

    Mutates payload in place so persisted SQL is the cleaned/normalized form.
    """
    if payload.sources:
        for src in payload.sources:
            if src.type == "sql":
                src.sql = _validate_sql(
                    src.sql or "", set(src.params), label=f"Source '{src.name}'"
                )
            elif src.type == "file":
                if not (src.file_ref and datasets.get_dataset(db, src.file_ref)):
                    raise DefinitionError(
                        f"Source '{src.name}': uploaded dataset '{src.file_ref}' not found."
                    )
    else:
        payload.sql = _validate_sql(payload.sql, set(payload.params))


def _source_rows(sources: list[SourceSpec]) -> list[ReportSource]:
    rows: list[ReportSource] = []
    for idx, src in enumerate(sources):
        rows.append(
            ReportSource(
                name=src.name,
                source_type=src.type,
                sql_text=src.sql if src.type == "sql" else None,
                file_ref=src.file_ref if src.type == "file" else None,
                params={k: v.model_dump() for k, v in src.params.items()},
                sort_order=src.sort_order or idx,
            )
        )
    return rows


def create_definition(
    db: Session, payload: ReportDefinitionIn, *, created_by: str | None
) -> ReportDefinition:
    _validate(db, payload)

    slug = unique_slug(db, ReportDefinition, payload.slug or payload.title)
    defn = ReportDefinition(
        slug=slug,
        title=payload.title,
        description=payload.description,
        sql_text=None if payload.sources else payload.sql,
        combine=payload.combine.model_dump() if payload.combine else None,
        params={k: v.model_dump() for k, v in payload.params.items()},
        columns={k: v.model_dump() for k, v in payload.columns.items()},
        chart=payload.chart.model_dump() if payload.chart else None,
        output_types=list(payload.output_types),
        layout=[b.model_dump() for b in payload.layout] if payload.layout else None,
        access_groups=list(payload.access_groups),
        status=payload.status,
        is_live=payload.is_live,
        schedules=[s.model_dump() for s in payload.schedules] if payload.schedules else None,
        created_by=created_by,
        sources=_source_rows(payload.sources),
    )
    db.add(defn)
    db.commit()
    db.refresh(defn)
    return defn


def update_definition(
    db: Session, defn: ReportDefinition, payload: ReportDefinitionIn
) -> ReportDefinition:
    _validate(db, payload)

    if payload.slug and payload.slug != defn.slug:
        defn.slug = unique_slug(db, ReportDefinition, payload.slug, exclude_id=defn.id)

    defn.title = payload.title
    defn.description = payload.description
    defn.sql_text = None if payload.sources else payload.sql
    defn.combine = payload.combine.model_dump() if payload.combine else None
    defn.params = {k: v.model_dump() for k, v in payload.params.items()}
    defn.columns = {k: v.model_dump() for k, v in payload.columns.items()}
    defn.chart = payload.chart.model_dump() if payload.chart else None
    defn.output_types = list(payload.output_types)
    defn.layout = [b.model_dump() for b in payload.layout] if payload.layout else None
    defn.access_groups = list(payload.access_groups)
    defn.status = payload.status
    defn.is_live = payload.is_live
    defn.schedules = [s.model_dump() for s in payload.schedules] if payload.schedules else None
    defn.version += 1
    # Replace sources wholesale; delete-orphan cleans up the old rows.
    defn.sources = _source_rows(payload.sources)

    db.commit()
    db.refresh(defn)
    return defn


def build_preview_definition(db: Session, payload: ReportDefinitionIn) -> ReportDefinition:
    """Validate a payload and build a transient (unsaved) ReportDefinition for a
    dry-run preview. Never added to the session."""
    _validate(db, payload)
    return ReportDefinition(
        slug="__preview__",
        title=payload.title or "preview",
        description=payload.description,
        sql_text=None if payload.sources else payload.sql,
        combine=payload.combine.model_dump() if payload.combine else None,
        params={k: v.model_dump() for k, v in payload.params.items()},
        columns={k: v.model_dump() for k, v in payload.columns.items()},
        chart=payload.chart.model_dump() if payload.chart else None,
        output_types=list(payload.output_types),
        access_groups=[],
        status="draft",
        sources=_source_rows(payload.sources),
    )


def get_by_slug(db: Session, slug: str) -> ReportDefinition | None:
    return db.execute(
        select(ReportDefinition).where(ReportDefinition.slug == slug)
    ).scalar_one_or_none()


def list_definitions(db: Session, *, include_archived: bool = False) -> list[ReportDefinition]:
    stmt = select(ReportDefinition).order_by(ReportDefinition.title.asc())
    if not include_archived:
        stmt = stmt.where(ReportDefinition.status != "archived")
    return list(db.execute(stmt).scalars().all())
