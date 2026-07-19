from __future__ import annotations

import datetime as dt
import decimal
import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import ReportDefinition, ReportSnapshot, ReportSource
from app.platform.database.snowflake import get_snowflake_client, run_query
from app.events import reports_events
from app.services.reports import datasets
from app.services.reports.blend import blend_sources

logger = logging.getLogger("reports.snapshots")


def _json_safe(value: Any) -> Any:
    """Coerce a Snowflake cell into a JSON-serializable value.

    Snowflake returns native date/datetime/Decimal/bytes; the snapshot JSON
    column can't encode those. Dates -> ISO strings, Decimals -> int/float,
    bytes -> text; everything else passes through.
    """
    if isinstance(value, (dt.date, dt.datetime, dt.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        # keep integers integer, otherwise float for the renderer/exports
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", "replace")
    return value


def _sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: _json_safe(v) for k, v in row.items()} for row in rows]

_MOCK_ROW_COUNT = 8


def _mock_columns(defn: ReportDefinition) -> list[str]:
    if defn.columns:
        return list(defn.columns.keys())
    chart = defn.chart or {}
    cols = [c for c in (chart.get("x"), chart.get("y")) if isinstance(c, str)]
    if isinstance(chart.get("y"), list):
        cols.extend(chart["y"])
    return cols or ["category", "value"]


def _mock_value(defn: ReportDefinition, key: str, i: int, pos: int) -> Any:
    """One deterministic placeholder cell, shaped off the column's format."""
    fmt = (defn.columns.get(key) or {}).get("format") if defn.columns else None
    if fmt in {"int"}:
        return (i + 1) * 100 + pos
    if fmt in {"float", "currency"}:
        return round((i + 1) * 1234.5 + pos, 2)
    if fmt in {"percent"}:
        return round(((i + 1) / _MOCK_ROW_COUNT), 3)
    if fmt in {"date", "datetime"}:
        return f"2026-0{(i % 9) + 1}-15"
    if pos == 0:
        return f"Sample {chr(65 + i)}"
    return (i + 1) * (pos + 1)


def _mock_rows(defn: ReportDefinition) -> list[dict[str, Any]]:
    """Deterministic placeholder rows for local/dev (no Snowflake creds).

    Shapes values off each column's declared `format` so the renderer has
    realistic-looking data to lay out. Never used in live mode.
    """
    cols = _mock_columns(defn)
    return [
        {key: _mock_value(defn, key, i, pos) for pos, key in enumerate(cols)}
        for i in range(_MOCK_ROW_COUNT)
    ]


def _source_key_columns(combine: dict[str, Any] | None, source_name: str) -> list[str]:
    """Join-key columns a given source contributes, in declaration order."""
    out: list[str] = []
    if combine and combine.get("op") == "join":
        for join in combine.get("joins", []):
            for lcol, rcol in join.get("on", []):
                if join.get("left") == source_name and lcol not in out:
                    out.append(lcol)
                if join.get("right") == source_name and rcol not in out:
                    out.append(rcol)
    return out


def _mock_source_rows(defn: ReportDefinition, src: ReportSource) -> list[dict[str, Any]]:
    """Synthesize joinable/stackable rows for one source in mock mode.

    For unions, every source mirrors the final column shape so rows stack. For
    joins, each source emits its shared key columns (aligned integer domain, so
    the join actually matches) plus one value column named for the source.
    """
    combine = defn.combine or {}
    if combine.get("op") == "union":
        cols = _mock_columns(defn)
        return [
            {key: _mock_value(defn, key, i, pos) for pos, key in enumerate(cols)}
            for i in range(_MOCK_ROW_COUNT)
        ]
    keys = _source_key_columns(combine, src.name)
    rows: list[dict[str, Any]] = []
    for i in range(_MOCK_ROW_COUNT):
        row: dict[str, Any] = {kc: i for kc in keys}
        row[f"{src.name}_value"] = (i + 1) * 10
        rows.append(row)
    return rows


def _wrap_limit(sql: str, limit: int) -> str:
    """Bound a read-only SELECT to at most `limit` rows (for dry-run preview)."""
    return f"SELECT * FROM (\n{sql}\n) AS _preview LIMIT {int(limit)}"


def _resolve_source_rows(
    db,
    client,
    defn: ReportDefinition,
    src: ReportSource,
    bound: dict[str, Any],
    *,
    sql_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Resolve one source to JSON-safe rows.

    File sources read their stored dataset (same rows in mock or live — the file
    *is* the data). SQL sources hit Snowflake live, or synthesize rows in mock.
    `sql_limit` bounds live SQL for previews (ignored by mock/file).
    """
    if src.source_type == "file":
        ds = datasets.get_dataset(db, src.file_ref) if src.file_ref else None
        if ds is None:
            raise ValueError(
                f"Source '{src.name}': uploaded dataset '{src.file_ref}' not found."
            )
        return list(ds.row_data or [])
    if client.is_mock:
        return _mock_source_rows(defn, src)
    # Live: source-declared param defaults, overridden by caller-bound params.
    src_defaults = {k: (v or {}).get("default") for k, v in (src.params or {}).items()}
    src_params = {**src_defaults, **bound}
    sql = _wrap_limit(src.sql_text, sql_limit) if sql_limit else src.sql_text
    return _sanitize_rows(run_query(sql, src_params))


def _resolve_params(defn: ReportDefinition, overrides: dict[str, Any] | None) -> dict[str, Any]:
    """Bind values for the query: caller overrides win, else per-param default."""
    overrides = overrides or {}
    resolved: dict[str, Any] = {}
    for name, spec in (defn.params or {}).items():
        if name in overrides:
            resolved[name] = overrides[name]
        else:
            resolved[name] = (spec or {}).get("default")
    return resolved


def _compute_rows(
    db,
    defn: ReportDefinition,
    bound: dict[str, Any],
    *,
    sql_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Resolve a definition's rows: blend sources, or run the legacy single SQL.

    `sql_limit` bounds live SQL execution (dry-run preview only).
    """
    client = get_snowflake_client()
    if defn.sources:
        # One or more explicit sources, blended per the combine spec.
        frames = {
            src.name: _resolve_source_rows(db, client, defn, src, bound, sql_limit=sql_limit)
            for src in sorted(defn.sources, key=lambda s: s.sort_order)
        }
        return blend_sources(frames, defn.combine)
    if client.is_mock:
        # Legacy single source, local/dev without creds: synthesize rows.
        return _mock_rows(defn)
    sql = _wrap_limit(defn.sql_text, sql_limit) if sql_limit else defn.sql_text
    return _sanitize_rows(run_query(sql, bound))


def preview_definition(
    db: Session,
    defn: ReportDefinition,
    *,
    params: dict[str, Any] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Compute rows for an (unsaved) definition without persisting a snapshot.

    Powers the builder's dry-run: authors see real columns/rows before saving.
    """
    bound = _resolve_params(defn, params)
    bound = {k: _json_safe(v) for k, v in bound.items()}
    # Push LIMIT into live SQL; also slice as a safety net for mock/file rows.
    rows = _compute_rows(db, defn, bound, sql_limit=limit)
    if limit and len(rows) > limit:
        rows = rows[:limit]
    result_columns = list(rows[0].keys()) if rows else list((defn.columns or {}).keys())
    return {"result_columns": result_columns, "rows": rows, "row_count": len(rows)}


def refresh_snapshot(
    db: Session,
    defn: ReportDefinition,
    *,
    params: dict[str, Any] | None = None,
) -> ReportSnapshot:
    """Execute a definition against Snowflake and persist a snapshot.

    Failures are captured as an error snapshot rather than raised, so one bad
    report never blocks a batch refresh.
    """
    bound = _resolve_params(defn, params)
    bound = {k: _json_safe(v) for k, v in bound.items()}
    started = time.perf_counter()
    try:
        rows = _compute_rows(db, defn, bound)
        result_columns = list(rows[0].keys()) if rows else list((defn.columns or {}).keys())
        snap = ReportSnapshot(
            report_id=defn.id,
            status="ok",
            row_count=len(rows),
            result_columns=result_columns,
            row_data=rows,
            params_used=bound,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001 — capture per-report, keep batch alive
        logger.exception("snapshot_failed", extra={"slug": defn.slug})
        snap = ReportSnapshot(
            report_id=defn.id,
            status="error",
            row_count=0,
            result_columns=[],
            row_data=[],
            params_used=bound,
            error=str(exc),
            elapsed_ms=round((time.perf_counter() - started) * 1000),
        )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    reports_events.snapshot_refreshed(defn, snap)
    return snap


def latest_snapshot(db: Session, report_id: int) -> ReportSnapshot | None:
    stmt = (
        select(ReportSnapshot)
        .where(ReportSnapshot.report_id == report_id)
        .order_by(ReportSnapshot.run_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def prune_snapshots(db: Session, report_id: int, keep: int = 5) -> int:
    """Keep only the newest `keep` snapshots per report. Returns count deleted."""
    stmt = (
        select(ReportSnapshot.id)
        .where(ReportSnapshot.report_id == report_id)
        .order_by(ReportSnapshot.run_at.desc())
        .offset(keep)
    )
    stale_ids = [row[0] for row in db.execute(stmt).all()]
    if not stale_ids:
        return 0
    for snap in db.query(ReportSnapshot).filter(ReportSnapshot.id.in_(stale_ids)):
        db.delete(snap)
    db.commit()
    return len(stale_ids)
