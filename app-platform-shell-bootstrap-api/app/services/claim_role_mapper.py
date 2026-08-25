from __future__ import annotations

from typing import Any

from app.core.config import Settings


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized in seen:
            continue

        seen.add(normalized)
        result.append(normalized)

    return result


def _extract_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    return []


def roles_from_claims(payload: dict[str, Any], settings: Settings) -> list[str]:
    """
    Extract platform roles directly from the configured JWT roles claim.

    Production strategy:

        Entra app role value == platform permission

    Examples:

        orders.view
        orders.create
        catalog.view
        platform.admin

    Bootstrap intentionally does not map:

        scope -> role
        group -> role
        role  -> permission

    Scopes still matter for token/API access validation elsewhere, but scopes do
    not create application permissions.
    """

    roles = _extract_string_list(payload.get(settings.auth_roles_claim))
    return _dedupe_keep_order(roles)