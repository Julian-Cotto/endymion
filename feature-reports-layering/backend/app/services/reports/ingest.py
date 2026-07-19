"""Parse an uploaded CSV/XLSX into JSON-safe rows + inferred column config.

Turns a spreadsheet a BA uploads into the same row/column shape the rest of the
reporting layer speaks (list[dict] rows + a `columns` map of {key: {label,
format}}), so a file source drops straight into the snapshot pipeline and the
renderer alongside SQL sources.
"""
from __future__ import annotations

import io
import json
import re
import warnings
from dataclasses import dataclass
from typing import Any

import pandas as pd

# Guard rails — a report-sized upload, not a data lake.
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 50_000
MAX_COLS = 200

_CSV_EXTS = {".csv"}
_XLSX_EXTS = {".xlsx", ".xlsm"}


class IngestError(ValueError):
    """Raised when an uploaded file can't be parsed into a clean table."""


@dataclass(slots=True)
class ParsedFile:
    columns: dict[str, dict[str, str]]  # {key: {label, format}}
    rows: list[dict[str, Any]]
    row_count: int


def _ext(filename: str) -> str:
    m = re.search(r"(\.[A-Za-z0-9]+)$", filename or "")
    return m.group(1).lower() if m else ""


def _column_key(raw: str, taken: set[str]) -> str:
    key = re.sub(r"[^0-9a-zA-Z]+", "_", str(raw).strip().lower()).strip("_") or "col"
    if key[0].isdigit():
        key = f"c_{key}"
    candidate, n = key, 2
    while candidate in taken:
        candidate = f"{key}_{n}"
        n += 1
    taken.add(candidate)
    return candidate


def _infer_format(series: pd.Series) -> str:
    """Map a parsed column to one of the renderer's format hints."""
    non_null = series.dropna()
    if non_null.empty:
        return "text"
    if pd.api.types.is_bool_dtype(series):
        return "text"
    if pd.api.types.is_integer_dtype(series):
        return "int"
    if pd.api.types.is_float_dtype(series):
        # Whole-valued floats (common when a column has blanks) read as ints.
        return "int" if (non_null == non_null.round()).all() else "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        has_time = (non_null.dt.time != pd.Timestamp("00:00:00").time()).any()
        return "datetime" if has_time else "date"
    # object/string: try to recognise dates, else free text. Suppress pandas'
    # "could not infer format" chatter — falling back to per-element parsing is
    # exactly what we want for heterogeneous BA spreadsheets.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(non_null, errors="coerce")
    if parsed.notna().all():
        has_time = (parsed.dt.time != pd.Timestamp("00:00:00").time()).any()
        return "datetime" if has_time else "date"
    return "text"


def parse_file(filename: str, content: bytes) -> ParsedFile:
    if not content:
        raise IngestError("Uploaded file is empty.")
    if len(content) > MAX_BYTES:
        raise IngestError(f"File exceeds the {MAX_BYTES // (1024 * 1024)} MB limit.")

    ext = _ext(filename)
    try:
        if ext in _CSV_EXTS:
            df = pd.read_csv(io.BytesIO(content))
        elif ext in _XLSX_EXTS:
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        else:
            raise IngestError(f"Unsupported file type '{ext or '?'}'. Upload a .csv or .xlsx.")
    except IngestError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface a clean parse error to the author
        raise IngestError(f"Could not parse the file: {exc}") from exc

    if df.shape[1] == 0:
        raise IngestError("No columns found in the file.")
    if df.shape[1] > MAX_COLS:
        raise IngestError(f"Too many columns ({df.shape[1]} > {MAX_COLS}).")
    if len(df) > MAX_ROWS:
        raise IngestError(f"Too many rows ({len(df)} > {MAX_ROWS}).")

    columns: dict[str, dict[str, str]] = {}
    taken: set[str] = set()
    rename: dict[Any, str] = {}
    for original in df.columns:
        key = _column_key(original, taken)
        rename[original] = key
        columns[key] = {"label": str(original).strip(), "format": _infer_format(df[original])}

    df = df.rename(columns=rename)
    # Round-trip through JSON so numpy/NaN/Timestamp become plain JSON values.
    rows = json.loads(df.to_json(orient="records", date_format="iso"))
    return ParsedFile(columns=columns, rows=rows, row_count=len(rows))
