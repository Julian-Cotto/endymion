from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import ReportDefinition
from app.schemas.report import ReportDefinitionIn
from app.services.reports.slugs import unique_slug
from app.services.reports.sql_guard import (
    SqlValidationError,
    extract_param_names,
    validate_read_only,
)


class DefinitionError(ValueError):
    """Raised when a report definition is invalid (bad SQL or params)."""


def _validate(payload: ReportDefinitionIn) -> str:
    sql = validate_read_only(payload.sql)
    referenced = extract_param_names(sql)
    declared = set(payload.params.keys())
    missing = referenced - declared
    if missing:
        raise DefinitionError(
            f"SQL references undeclared params: {', '.join(sorted(missing))}."
        )
    return sql


def create_definition(
    db: Session, payload: ReportDefinitionIn, *, created_by: str | None
) -> ReportDefinition:
    try:
        sql = _validate(payload)
    except SqlValidationError as exc:
        raise DefinitionError(str(exc)) from exc

    slug = unique_slug(db, ReportDefinition, payload.slug or payload.title)
    defn = ReportDefinition(
        slug=slug,
        title=payload.title,
        description=payload.description,
        sql_text=sql,
        params={k: v.model_dump() for k, v in payload.params.items()},
        columns={k: v.model_dump() for k, v in payload.columns.items()},
        chart=payload.chart.model_dump() if payload.chart else None,
        output_types=list(payload.output_types),
        layout=[b.model_dump() for b in payload.layout] if payload.layout else None,
        access_groups=list(payload.access_groups),
        status=payload.status,
        created_by=created_by,
    )
    db.add(defn)
    db.commit()
    db.refresh(defn)
    return defn


def update_definition(
    db: Session, defn: ReportDefinition, payload: ReportDefinitionIn
) -> ReportDefinition:
    try:
        sql = _validate(payload)
    except SqlValidationError as exc:
        raise DefinitionError(str(exc)) from exc

    if payload.slug and payload.slug != defn.slug:
        defn.slug = unique_slug(db, ReportDefinition, payload.slug, exclude_id=defn.id)

    defn.title = payload.title
    defn.description = payload.description
    defn.sql_text = sql
    defn.params = {k: v.model_dump() for k, v in payload.params.items()}
    defn.columns = {k: v.model_dump() for k, v in payload.columns.items()}
    defn.chart = payload.chart.model_dump() if payload.chart else None
    defn.output_types = list(payload.output_types)
    defn.layout = [b.model_dump() for b in payload.layout] if payload.layout else None
    defn.access_groups = list(payload.access_groups)
    defn.status = payload.status
    defn.version += 1

    db.commit()
    db.refresh(defn)
    return defn


def get_by_slug(db: Session, slug: str) -> ReportDefinition | None:
    return db.execute(
        select(ReportDefinition).where(ReportDefinition.slug == slug)
    ).scalar_one_or_none()


def list_definitions(db: Session, *, include_archived: bool = False) -> list[ReportDefinition]:
    stmt = select(ReportDefinition).order_by(ReportDefinition.title.asc())
    if not include_archived:
        stmt = stmt.where(ReportDefinition.status != "archived")
    return list(db.execute(stmt).scalars().all())
