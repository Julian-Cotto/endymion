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


def test_multi_source_join_flow(client):
    # Two SQL sources joined on a shared key; mock mode synthesizes aligned
    # keys so the inner join actually matches.
    payload = {
        "title": "Blended Policies",
        "sources": [
            {"name": "a", "type": "sql", "sql": "SELECT k, x FROM ta"},
            {"name": "b", "type": "sql", "sql": "SELECT k, y FROM tb"},
        ],
        "combine": {
            "op": "join",
            "joins": [{"left": "a", "right": "b", "on": [["k", "k"]], "how": "inner"}],
        },
        "columns": {"k": {"label": "Key"}},
        "output_types": ["table"],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 201, r.text
    body = r.json()
    slug = body["slug"]
    assert body["last_snapshot_status"] == "ok"

    # Definition round-trips its sources; legacy sql_text is empty.
    d = client.get(f"{API}/definitions/{slug}", headers=_hdr(AUTHOR)).json()
    assert [s["name"] for s in d["sources"]] == ["a", "b"]
    assert d["sql_text"] is None
    assert d["combine"]["op"] == "join"

    # The view exposes the blended rows.
    view = client.get(f"{API}/reports/{slug}", headers=_hdr(AUTHOR)).json()
    assert view["row_count"] == 8
    assert set(view["result_columns"]) == {"k", "a_value", "b_value"}


def test_rejects_sources_and_sql_together(client):
    payload = {
        "title": "Both",
        "sql_text": "SELECT 1 AS n",
        "sources": [{"name": "a", "type": "sql", "sql": "SELECT 1 AS n"}],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 422


def test_rejects_multi_source_without_combine(client):
    payload = {
        "title": "NoCombine",
        "sources": [
            {"name": "a", "type": "sql", "sql": "SELECT 1 AS n"},
            {"name": "b", "type": "sql", "sql": "SELECT 2 AS n"},
        ],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 422


def test_upload_and_file_source_report(client):
    csv = b"region,n\nWest,5\nEast,7\n"
    up = client.post(
        f"{API}/uploads",
        files={"file": ("book.csv", csv, "text/csv")},
        headers=_hdr(AUTHOR),
    )
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["row_count"] == 2
    assert set(body["columns"]) == {"region", "n"}
    ref = body["file_ref"]

    payload = {
        "title": "From File",
        "sources": [{"name": "book", "type": "file", "file_ref": ref}],
        "columns": {"region": {"label": "Region"}, "n": {"label": "N", "format": "int"}},
        "output_types": ["table"],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 201, r.text
    slug = r.json()["slug"]
    assert r.json()["last_snapshot_status"] == "ok"

    view = client.get(f"{API}/reports/{slug}", headers=_hdr(AUTHOR)).json()
    assert view["row_count"] == 2
    assert view["rows"] == [{"region": "West", "n": 5}, {"region": "East", "n": 7}]


def test_two_file_sources_join(client):
    ref_a = client.post(
        f"{API}/uploads",
        files={"file": ("pol.csv", b"id,prem\n1,100\n2,200\n", "text/csv")},
        headers=_hdr(AUTHOR),
    ).json()["file_ref"]
    ref_b = client.post(
        f"{API}/uploads",
        files={"file": ("clm.csv", b"id,paid\n1,10\n3,30\n", "text/csv")},
        headers=_hdr(AUTHOR),
    ).json()["file_ref"]

    payload = {
        "title": "Joined Files",
        "sources": [
            {"name": "pol", "type": "file", "file_ref": ref_a},
            {"name": "clm", "type": "file", "file_ref": ref_b},
        ],
        "combine": {
            "op": "join",
            "joins": [{"left": "pol", "right": "clm", "on": [["id", "id"]], "how": "inner"}],
        },
        "output_types": ["table"],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 201, r.text
    slug = r.json()["slug"]

    view = client.get(f"{API}/reports/{slug}", headers=_hdr(AUTHOR)).json()
    assert view["row_count"] == 1  # inner join: only id=1 in both
    assert view["rows"] == [{"id": 1, "prem": 100, "paid": 10}]


def test_file_source_unknown_ref_rejected(client):
    payload = {
        "title": "BadRef",
        "sources": [{"name": "x", "type": "file", "file_ref": "deadbeef"}],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 422
    assert "not found" in r.json()["detail"]


def test_preview_multi_source_does_not_persist(client):
    before = len(client.get(f"{API}/definitions", headers=_hdr(AUTHOR)).json())
    payload = {
        "title": "Preview Only",
        "sources": [
            {"name": "a", "type": "sql", "sql": "SELECT k, x FROM ta"},
            {"name": "b", "type": "sql", "sql": "SELECT k, y FROM tb"},
        ],
        "combine": {
            "op": "join",
            "joins": [{"left": "a", "right": "b", "on": [["k", "k"]], "how": "inner"}],
        },
        "columns": {"k": {"label": "Key"}},
    }
    r = client.post(f"{API}/definitions/preview", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["row_count"] == 8
    assert set(body["result_columns"]) == {"k", "a_value", "b_value"}

    # Preview persists nothing: no new definition, no snapshot.
    after = len(client.get(f"{API}/definitions", headers=_hdr(AUTHOR)).json())
    assert after == before


def test_preview_rejects_bad_sql(client):
    payload = {"title": "Bad", "sql_text": "DROP TABLE policies"}
    r = client.post(f"{API}/definitions/preview", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 422


def test_events_emitted_on_create(client, monkeypatch):
    from app.events import publisher

    captured: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        publisher, "publish_event", lambda name, payload: captured.append((name, payload))
    )

    payload = {
        "title": "Event Emitter",
        "sources": [
            {"name": "a", "type": "sql", "sql": "SELECT k, x FROM ta"},
            {"name": "b", "type": "sql", "sql": "SELECT k, y FROM tb"},
        ],
        "combine": {
            "op": "join",
            "joins": [{"left": "a", "right": "b", "on": [["k", "k"]], "how": "inner"}],
        },
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 201, r.text

    names = [n for n, _ in captured]
    assert "reports-layering.snapshot-refreshed" in names
    published = next(p for n, p in captured if n == "reports-layering.report-published")
    assert published["source_count"] == 2
    assert published["source_types"] == ["sql"]
    assert published["has_combine"] is True


def test_column_renderer_hints_persist(client):
    payload = {
        "title": "Hints",
        "sql_text": "SELECT region, n FROM t",
        "columns": {
            "n": {
                "label": "N",
                "format": "int",
                "agg": "sum",
                "bar": True,
                "heat": "reverse",
                "style": "badge",
                "group": "Performance",
            }
        },
    }
    r = client.post(f"{API}/definitions", json=payload, headers=_hdr(AUTHOR))
    assert r.status_code == 201, r.text
    col = r.json()["columns"]["n"]
    assert col["agg"] == "sum"
    assert col["bar"] is True
    assert col["heat"] == "reverse"
    assert col["style"] == "badge"
    assert col["group"] == "Performance"


def test_prune_orphan_uploads(client):
    kept = client.post(
        f"{API}/uploads",
        files={"file": ("keep.csv", b"id\n1\n", "text/csv")},
        headers=_hdr(AUTHOR),
    ).json()["file_ref"]
    orphan = client.post(
        f"{API}/uploads",
        files={"file": ("orphan.csv", b"id\n2\n", "text/csv")},
        headers=_hdr(AUTHOR),
    ).json()["file_ref"]

    # Reference only `kept`.
    r = client.post(
        f"{API}/definitions",
        json={"title": "Keeps Ref", "sources": [{"name": "k", "type": "file", "file_ref": kept}]},
        headers=_hdr(AUTHOR),
    )
    assert r.status_code == 201, r.text

    # Prune everything unreferenced regardless of age.
    r = client.post(f"{API}/maintenance/prune-uploads?older_than_hours=0", headers=_hdr(AUTHOR))
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] >= 1

    # The orphan is gone (referencing it now 422s); the kept one still works.
    r_orphan = client.post(
        f"{API}/definitions",
        json={"title": "Dead Ref", "sources": [{"name": "o", "type": "file", "file_ref": orphan}]},
        headers=_hdr(AUTHOR),
    )
    assert r_orphan.status_code == 422
    r_keep = client.post(
        f"{API}/definitions",
        json={"title": "Keep Again", "sources": [{"name": "k2", "type": "file", "file_ref": kept}]},
        headers=_hdr(AUTHOR),
    )
    assert r_keep.status_code == 201, r_keep.text


AUTHOR_NONADMIN = "reports-layering.create,reports-layering.view"


def test_live_visibility_and_schedules(client):
    owner = _hdr(AUTHOR_NONADMIN, user="owner@example.local")
    payload = {
        "title": "Private Draft Report",
        "sql_text": "SELECT region, COUNT(*) AS n FROM t GROUP BY region",
        "columns": {"region": {"label": "Region"}, "n": {"format": "int"}},
        "output_types": ["table"],
        "access_groups": [],
        "is_live": False,
        "schedules": [{"cadence": "daily", "time": "08:00", "label": "Morning"}],
    }
    r = client.post(f"{API}/definitions", json=payload, headers=owner)
    assert r.status_code == 201, r.text
    slug = r.json()["slug"]
    assert r.json()["is_live"] is False
    assert r.json()["schedules"][0]["cadence"] == "daily"

    # Owner sees it (and can_manage on the view).
    v = client.get(f"{API}/reports/{slug}", headers=owner)
    assert v.status_code == 200
    assert v.json()["is_live"] is False and v.json()["can_manage"] is True

    # A different viewer cannot see a private report — 404, absent from list.
    viewer = _hdr(VIEWER, user="someone@example.local")
    assert client.get(f"{API}/reports/{slug}", headers=viewer).status_code == 404
    assert slug not in [x["slug"] for x in client.get(f"{API}/reports", headers=viewer).json()]

    # A different (non-admin) author also cannot see it.
    other_author = _hdr(AUTHOR_NONADMIN, user="other@example.local")
    assert client.get(f"{API}/reports/{slug}", headers=other_author).status_code == 404

    # Owner flips it live -> now visible to viewers (no access groups = public).
    r = client.post(f"{API}/definitions/{slug}/live", json={"is_live": True}, headers=owner)
    assert r.status_code == 200 and r.json()["is_live"] is True
    vv = client.get(f"{API}/reports/{slug}", headers=viewer)
    assert vv.status_code == 200
    assert vv.json()["can_manage"] is False  # viewer can't manage


def test_non_owner_cannot_toggle_live(client):
    owner = _hdr(AUTHOR_NONADMIN, user="owner2@example.local")
    r = client.post(
        f"{API}/definitions",
        json={"title": "Owned Report", "sql_text": "SELECT a FROM t", "output_types": ["table"]},
        headers=owner,
    )
    slug = r.json()["slug"]
    other = _hdr(AUTHOR_NONADMIN, user="intruder@example.local")
    assert client.post(f"{API}/definitions/{slug}/live", json={"is_live": False}, headers=other).status_code == 403
