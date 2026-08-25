"""Cached OSM points of interest."""

from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Index, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base


class Poi(Base):
    """A point of interest, cached from Overpass.

    Global rather than per-search: Overpass is a shared free endpoint that
    rate-limits aggressively, so re-fetching the same city for every search
    would get us throttled. Rows are keyed by OSM identity and refreshed by
    the refresh-source-caches job.
    """

    __tablename__ = "pois"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="osm")
    # OSM element identity, e.g. "node/1234" — unique per source.
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)

    name: Mapped[str | None] = mapped_column(String(255))
    # Normalized PoiCategory value; OSM's raw tags are kept in `tags`.
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )

    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_pois_source_id"),
        # Every scoring pass is "POIs near this cell" — a GiST index on the
        # point is what makes that not a seq scan.
        Index("ix_pois_geometry", "geometry", postgresql_using="gist"),
        Index("ix_pois_category_geometry", "category", "geometry"),
    )
