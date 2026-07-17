from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.report import Group, GroupMembership
from app.schemas.report import GroupIn, MembershipIn
from app.services.reports.slugs import unique_slug


class GroupError(ValueError):
    """Raised on invalid group operations."""


def list_groups(db: Session) -> list[tuple[Group, int]]:
    stmt = (
        select(Group, func.count(GroupMembership.id))
        .outerjoin(GroupMembership, GroupMembership.group_id == Group.id)
        .group_by(Group.id)
        .order_by(Group.name.asc())
    )
    return [(g, n) for g, n in db.execute(stmt).all()]


def create_group(db: Session, payload: GroupIn) -> Group:
    slug = unique_slug(db, Group, payload.slug or payload.name)
    group = Group(slug=slug, name=payload.name, description=payload.description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def get_group(db: Session, slug: str) -> Group | None:
    return db.execute(select(Group).where(Group.slug == slug)).scalar_one_or_none()


def add_member(db: Session, group: Group, payload: MembershipIn) -> GroupMembership:
    key = payload.user_key.strip().lower()
    existing = db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group.id,
            GroupMembership.user_key == key,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    member = GroupMembership(
        group_id=group.id, user_key=key, display_name=payload.display_name
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_member(db: Session, group: Group, user_key: str) -> bool:
    key = user_key.strip().lower()
    member = db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group.id,
            GroupMembership.user_key == key,
        )
    ).scalar_one_or_none()
    if not member:
        return False
    db.delete(member)
    db.commit()
    return True
