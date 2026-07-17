from __future__ import annotations

import re

# Reports are read-only views over Snowflake. The BA supplies SELECT logic
# only; anything that writes, changes schema, or runs procedural code is
# rejected before it can ever reach the driver.

_FORBIDDEN = {
    "insert", "update", "delete", "merge", "upsert",
    "drop", "alter", "create", "truncate", "rename",
    "grant", "revoke",
    "call", "exec", "execute",
    "copy", "put", "remove", "unload",
    "use", "set", "comment",
    "begin", "commit", "rollback",
}

# strip /* */ and -- comments so they can't smuggle keywords/semicolons
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\n]*")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class SqlValidationError(ValueError):
    """Raised when uploaded SQL is not a safe, single read-only statement."""


def _strip_comments(sql: str) -> str:
    sql = _BLOCK_COMMENT.sub(" ", sql)
    sql = _LINE_COMMENT.sub(" ", sql)
    return sql


def validate_read_only(sql: str) -> str:
    """Validate + normalize BA-uploaded SQL. Returns cleaned single statement.

    Raises SqlValidationError on anything that isn't exactly one SELECT/CTE.
    """
    if not sql or not sql.strip():
        raise SqlValidationError("SQL is empty.")

    cleaned = _strip_comments(sql).strip()

    # single statement only: allow one optional trailing semicolon
    body = cleaned.rstrip(";").strip()
    if ";" in body:
        raise SqlValidationError("Only a single SQL statement is allowed.")

    lowered = body.lower()
    first = lowered.split(None, 1)[0] if lowered.split() else ""
    if first not in {"select", "with"}:
        raise SqlValidationError(
            "Report SQL must be a SELECT (or WITH ... SELECT) query."
        )

    words = {w.lower() for w in _WORD.findall(lowered)}
    hits = words & _FORBIDDEN
    if hits:
        raise SqlValidationError(
            f"Disallowed keyword(s) in report SQL: {', '.join(sorted(hits))}."
        )

    return body


def extract_param_names(sql: str) -> set[str]:
    """Return :named bind params referenced in the SQL."""
    return set(re.findall(r"(?<![:\w]):([A-Za-z_][A-Za-z0-9_]*)", sql))
