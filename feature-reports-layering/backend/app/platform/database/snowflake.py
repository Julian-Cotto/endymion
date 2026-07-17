"""Snowflake access for the reporting layer.

Thin wrapper over the shared `platform-snowflake-client` library. That lib
owns the wire layer (connection, mock-vs-live, raw query execution); this
feature owns its own SQL, which comes from BA-uploaded report definitions.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from platform_snowflake import SnowflakeClient


@lru_cache(maxsize=1)
def get_snowflake_client() -> SnowflakeClient:
    # Auto-selects mock vs live from env (mock in local/dev without creds).
    return SnowflakeClient.from_env()


def run_query(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a read-only report query and return dict rows."""
    return get_snowflake_client().query(sql, params or {})
