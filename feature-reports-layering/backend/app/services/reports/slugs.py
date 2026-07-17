from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = _NON_ALNUM.sub("-", value.strip().lower()).strip("-")
    return slug or "report"


def unique_slug(db: Session, model, base: str, *, exclude_id: int | None = None) -> str:
    """Return `base` or `base-2`, `base-3`... ensuring uniqueness on model.slug."""
    base = slugify(base)
    candidate = base
    n = 1
    while True:
        stmt = select(model.id).where(model.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)
        if db.execute(stmt).first() is None:
            return candidate
        n += 1
        candidate = f"{base}-{n}"
