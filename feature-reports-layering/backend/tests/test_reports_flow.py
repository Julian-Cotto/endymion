"""End-to-end smoke for the reporting layer.

Runs entirely offline: SQLite metadata DB, mock auth via debug headers, and
Snowflake in mock mode (synthetic snapshot rows). Exercises the full author
-> snapshot -> view -> export path plus access-group filtering.
"""
from __future__ import annotations

import pytest

# Env + schema come from the repo-root conftest.py (SQLite + mock auth/SF).


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


def _hdr(roles: str, user: str = "author@example.local"):
    return {
        "X-Debug-User-Id": user,
        "X-Debug-Email": user,
        "X-Debug-Roles": roles,
    }


AUTHOR = "reports-layering.create,reports-layering.view,reports-layering.admin"
VIEWER = "reports-layering.view"
API = "/api/reports/reports-layering"


def test_full_flow(client):
    # Author creates a report; an immediate snapshot is taken.
    payload = {
        "title": "Active Policies by Region",
        "description": "Count of active policies grouped by region.",
        "sql_text": "SELECT region, COUNT(*) AS n FROM policies GROUP BY region",
        "columns": {"region": {"label": "Region"}, "n": {"label": "Count", "format": "int"}},
        "chart": {"type": "bar", "x": "region", "y": "n"},
        "output_types": ["table", "chart", "kpi"],
        "access_groups": ["underwriting"],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 201, r.text
    body = r.json()
    slug = body["slug"]
    assert slug == "active-policies-by-region"
    assert body["last_snapshot_status"] == "ok"

    # Author can view rows (mock snapshot rows synthesized).
    r = client.get(f"{API}/reports/{slug}", headers=_hdr(AUTHOR))
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["row_count"] == 8
    assert set(view["result_columns"]) == {"region", "n"}

    # CSV export uses column labels as headers.
    r = client.get(f"{API}/reports/{slug}/export.csv", headers=_hdr(AUTHOR))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0] == "Region,Count"

    # Viewer NOT in the 'underwriting' group cannot see the report (404).
    viewer_hdr = _hdr(VIEWER, user="viewer@example.local")
    r = client.get(f"{API}/reports/{slug}", headers=viewer_hdr)
    assert r.status_code == 404
    assert client.get(f"{API}/reports", headers=viewer_hdr).json() == []

    # Admin creates the group and adds the viewer.
    r = client.post(f"{API}/groups", json={"name": "Underwriting", "slug": "underwriting"}, headers=_hdr(AUTHOR))
    assert r.status_code == 201, r.text
    r = client.post(
        f"{API}/groups/underwriting/members",
        json={"user_key": "viewer@example.local"},
        headers=_hdr(AUTHOR),
    )
    assert r.status_code == 201, r.text

    # Now the viewer sees exactly one report and can open it.
    listing = client.get(f"{API}/reports", headers=viewer_hdr).json()
    assert [x["slug"] for x in listing] == [slug]
    assert client.get(f"{API}/reports/{slug}", headers=viewer_hdr).status_code == 200


def test_rejects_non_select_sql(client):
    payload = {
        "title": "Bad Report",
        "sql_text": "DROP TABLE policies",
        "output_types": ["table"],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 422
    assert "SELECT" in r.json()["detail"]


def test_rejects_undeclared_param(client):
    payload = {
        "title": "Needs Param",
        "sql_text": "SELECT * FROM policies WHERE status = :status",
        "output_types": ["table"],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 422
    assert "status" in r.json()["detail"]
