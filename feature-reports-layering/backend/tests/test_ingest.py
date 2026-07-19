"""Unit tests for CSV/XLSX ingestion (no DB involved)."""
from __future__ import annotations

import io

import pandas as pd
import pytest

from app.services.reports.ingest import IngestError, parse_file


def test_parse_csv_infers_types_and_keys():
    content = b"Region,Count,Ratio,As Of\nWest,10,0.5,2026-01-15\nEast,20,0.25,2026-02-15\n"
    parsed = parse_file("book.csv", content)

    assert parsed.row_count == 2
    assert set(parsed.columns) == {"region", "count", "ratio", "as_of"}
    assert parsed.columns["region"]["format"] == "text"
    assert parsed.columns["count"]["format"] == "int"
    assert parsed.columns["ratio"]["format"] == "float"
    assert parsed.columns["as_of"]["format"] == "date"
    # Original header preserved as the label.
    assert parsed.columns["as_of"]["label"] == "As Of"
    assert parsed.rows[0] == {"region": "West", "count": 10, "ratio": 0.5, "as_of": "2026-01-15"}


def test_parse_xlsx():
    df = pd.DataFrame({"Name": ["A", "B"], "Qty": [3, 4]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)

    parsed = parse_file("sheet.xlsx", buf.getvalue())
    assert parsed.row_count == 2
    assert parsed.columns["qty"]["format"] == "int"
    assert parsed.rows == [{"name": "A", "qty": 3}, {"name": "B", "qty": 4}]


def test_duplicate_headers_get_unique_keys():
    parsed = parse_file("dupes.csv", b"A,A\n1,2\n")
    assert list(parsed.columns) == ["a", "a_1"]


def test_unsupported_extension_rejected():
    with pytest.raises(IngestError):
        parse_file("notes.txt", b"hello")


def test_empty_file_rejected():
    with pytest.raises(IngestError):
        parse_file("empty.csv", b"")
