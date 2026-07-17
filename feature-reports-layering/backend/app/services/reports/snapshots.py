from __future__ import annotations

import datetime as dt
import decimal
import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import ReportDefinition, ReportSnapshot
from app.platform.database.snowflake import get_snowflake_client, run_query

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


def _mock_rows(defn: ReportDefinition) -> list[dict[str, Any]]:
    """Deterministic placeholder rows for local/dev (no Snowflake creds).

    Shapes values off each column's declared `format` so the renderer has
    realistic-looking data to lay out. Never used in live mode.
    """
    cols = _mock_columns(defn)
    rows: list[dict[str, Any]] = []
    for i in range(_MOCK_ROW_COUNT):
        row: dict[str, Any] = {}
        for pos, key in enumerate(cols):
            fmt = (defn.columns.get(key) or {}).get("format") if defn.columns else None
            if fmt in {"int"}:
                row[key] = (i + 1) * 100 + pos
            elif fmt in {"float", "currency"}:
                row[key] = round((i + 1) * 1234.5 + pos, 2)
            elif fmt in {"percent"}:
                row[key] = round(((i + 1) / _MOCK_ROW_COUNT), 3)
            elif fmt in {"date", "datetime"}:
                row[key] = f"2026-0{(i % 9) + 1}-15"
            elif pos == 0:
                row[key] = f"Sample {chr(65 + i)}"
            else:
                row[key] = (i + 1) * (pos + 1)
        rows.append(row)
    return rows


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
        client = get_snowflake_client()
        if client.is_mock:
            # Local/dev without creds: synthesize rows so the app is usable.
            rows = _mock_rows(defn)
        else:
            rows = _sanitize_rows(run_query(defn.sql_text, bound))
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
