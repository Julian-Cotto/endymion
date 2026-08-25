from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import Group, GroupMembership, ReportDefinition
from app.platform.auth_context import AuthContext

# Permission strings (Entra app role value == platform permission).
PERM_VIEW = "reports-layering.view"
PERM_CREATE = "reports-layering.create"
PERM_EDIT = "reports-layering.edit"
PERM_ADMIN = "reports-layering.admin"


def user_keys(ctx: AuthContext) -> list[str]:
    """Stable identifiers a membership might be keyed on (oid + email)."""
    keys: list[str] = []
    for raw in (ctx.user_id, ctx.email):
        if raw and raw.strip():
            keys.append(raw.strip().lower())
    return list(dict.fromkeys(keys))


def is_admin(ctx: AuthContext) -> bool:
    roles = set(ctx.roles)
    return "platform.admin" in roles or PERM_ADMIN in roles


def is_author(ctx: AuthContext) -> bool:
    roles = set(ctx.roles)
    return is_admin(ctx) or PERM_CREATE in roles or PERM_EDIT in roles


def is_owner(defn: ReportDefinition, ctx: AuthContext) -> bool:
    return bool(defn.created_by) and defn.created_by.strip().lower() in user_keys(ctx)


def can_manage(defn: ReportDefinition, ctx: AuthContext) -> bool:
    """Who may toggle Live / edit visibility: the owner or an admin."""
    return is_admin(ctx) or is_owner(defn, ctx)


def user_group_slugs(db: Session, ctx: AuthContext) -> set[str]:
    keys = user_keys(ctx)
    if not keys:
        return set()
    stmt = (
        select(Group.slug)
        .join(GroupMembership, GroupMembership.group_id == Group.id)
        .where(GroupMembership.user_key.in_(keys))
    )
    return {row[0] for row in db.execute(stmt).all()}


def can_view(defn: ReportDefinition, ctx: AuthContext, group_slugs: set[str]) -> bool:
    """Visibility rules:
      * admins and the owner always see it;
      * a non-live (private) report is owner/admin only;
      * a live report is visible to authors, or to viewers whose group matches
        (or any viewer when it has no access groups).
    """
    if is_admin(ctx) or is_owner(defn, ctx):
        return True
    if not getattr(defn, "is_live", True):
        return False  # private — only owner/admin (handled above)
    if is_author(ctx):
        return True
    if not defn.access_groups:
        return True
    return bool(set(defn.access_groups) & group_slugs)
