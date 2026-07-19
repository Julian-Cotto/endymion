"""Blend multiple report sources into one result set with pandas.

Each source resolves to a list of JSON-safe dict rows (from Snowflake in live
mode, or synthesized in mock mode). This module combines them per the report's
`combine` spec — a join across named sources, or a union (concatenation).

Kept pure and dependency-free of the DB/Snowflake layers so it can be unit
tested directly with fabricated frames.
"""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

Rows = list[dict[str, Any]]


class BlendError(ValueError):
    """Raised when sources cannot be combined as specified."""


def _to_records(df: pd.DataFrame) -> Rows:
    # Round-trip through JSON so numpy scalars and NaN become plain
    # JSON-serializable values (NaN -> null) that the snapshot column can store.
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _merge_pair(left: pd.DataFrame, right: pd.DataFrame, join: dict[str, Any], right_name: str) -> pd.DataFrame:
    how = join.get("how", "inner")
    on_pairs = join.get("on") or []
    if not on_pairs:
        raise BlendError("A join needs at least one 'on' key pair.")
    left_on = [p[0] for p in on_pairs]
    right_on = [p[1] for p in on_pairs]
    for col, side in [(c, "left") for c in left_on] + [(c, "right") for c in right_on]:
        frame = left if side == "left" else right
        if col not in frame.columns:
            raise BlendError(f"Join key '{col}' not found in {side} source columns.")
    # When both sides name the key identically, collapse to a single key column.
    if left_on == right_on:
        return left.merge(right, how=how, on=left_on, suffixes=("", f"_{right_name}"))
    return left.merge(
        right, how=how, left_on=left_on, right_on=right_on, suffixes=("", f"_{right_name}")
    )


def blend_sources(frames: dict[str, Rows], combine: dict[str, Any] | None) -> Rows:
    """Combine named source frames into one list of rows.

    - No combine (single source): returns that source's rows unchanged.
    - op "union": concatenate all sources (outer column set); `distinct` drops
      fully-duplicate rows.
    - op "join": iteratively merge sources per the `joins` list, left-to-right.
    """
    names = list(frames)
    if not names:
        return []

    dfs = {name: pd.DataFrame(rows) for name, rows in frames.items()}

    if not combine:
        if len(names) != 1:
            raise BlendError("Multiple sources require a combine spec.")
        return _to_records(dfs[names[0]])

    op = combine.get("op")
    if op == "union":
        out = pd.concat([dfs[n] for n in names], ignore_index=True, sort=False)
        if combine.get("distinct"):
            out = out.drop_duplicates(ignore_index=True)
        return _to_records(out)

    if op == "join":
        joins = combine.get("joins") or []
        if not joins:
            raise BlendError("combine.op 'join' requires at least one join.")
        result: pd.DataFrame | None = None
        merged: set[str] = set()
        for join in joins:
            left_name, right_name = join["left"], join["right"]
            for n in (left_name, right_name):
                if n not in dfs:
                    raise BlendError(f"Join references unknown source '{n}'.")
            left_df = result if (result is not None and left_name in merged) else dfs[left_name]
            result = _merge_pair(left_df, dfs[right_name], join, right_name)
            merged.update({left_name, right_name})
        assert result is not None
        return _to_records(result)

    raise BlendError(f"Unknown combine op: {op!r}.")
