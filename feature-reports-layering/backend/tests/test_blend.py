"""Unit tests for the pandas blend logic (no DB / Snowflake involved)."""
from __future__ import annotations

import pytest

from app.services.reports.blend import BlendError, blend_sources


def test_single_source_passthrough():
    frames = {"a": [{"x": 1}, {"x": 2}]}
    assert blend_sources(frames, None) == [{"x": 1}, {"x": 2}]


def test_inner_join_same_key_name_collapses_key():
    frames = {
        "a": [{"id": 1, "a_val": 10}, {"id": 2, "a_val": 20}],
        "b": [{"id": 1, "b_val": 100}, {"id": 3, "b_val": 300}],
    }
    combine = {"op": "join", "joins": [{"left": "a", "right": "b", "on": [["id", "id"]], "how": "inner"}]}
    assert blend_sources(frames, combine) == [{"id": 1, "a_val": 10, "b_val": 100}]


def test_left_join_fills_missing_with_none():
    frames = {
        "a": [{"id": 1, "a_val": 10}, {"id": 2, "a_val": 20}],
        "b": [{"id": 1, "b_val": 100}],
    }
    combine = {"op": "join", "joins": [{"left": "a", "right": "b", "on": [["id", "id"]], "how": "left"}]}
    out = blend_sources(frames, combine)
    # b_val is upcast to float by the NaN fill; the missing row becomes null.
    assert out == [
        {"id": 1, "a_val": 10, "b_val": 100.0},
        {"id": 2, "a_val": 20, "b_val": None},
    ]


def test_join_different_key_names_keeps_both():
    frames = {
        "orders": [{"cust": 1, "amt": 5}],
        "customers": [{"id": 1, "name": "Acme"}],
    }
    combine = {
        "op": "join",
        "joins": [{"left": "orders", "right": "customers", "on": [["cust", "id"]], "how": "inner"}],
    }
    assert blend_sources(frames, combine) == [{"cust": 1, "amt": 5, "id": 1, "name": "Acme"}]


def test_union_stacks_rows():
    frames = {"a": [{"x": 1}], "b": [{"x": 2}]}
    assert blend_sources(frames, {"op": "union"}) == [{"x": 1}, {"x": 2}]


def test_union_distinct_drops_duplicates():
    frames = {"a": [{"x": 1}], "b": [{"x": 1}]}
    assert blend_sources(frames, {"op": "union", "distinct": True}) == [{"x": 1}]


def test_unknown_source_raises():
    with pytest.raises(BlendError):
        blend_sources(
            {"a": [{"id": 1}]},
            {"op": "join", "joins": [{"left": "a", "right": "zzz", "on": [["id", "id"]]}]},
        )


def test_missing_join_key_raises():
    with pytest.raises(BlendError):
        blend_sources(
            {"a": [{"id": 1}], "b": [{"other": 1}]},
            {"op": "join", "joins": [{"left": "a", "right": "b", "on": [["id", "id"]]}]},
        )


def test_multiple_sources_without_combine_raises():
    with pytest.raises(BlendError):
        blend_sources({"a": [{"x": 1}], "b": [{"y": 2}]}, None)
