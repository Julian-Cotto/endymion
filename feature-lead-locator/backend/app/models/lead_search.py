"""A user's search for leads in an area, and its lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base


class SearchStatus(StrEnum):
    PENDING = "pending"
    SCORING = "scoring"
    COMPLETE = "complete"
    FAILED = "failed"


class LeadSearch(Base):
    """One "score me 90210 at res 8" request.

    Stored rather than computed live because scoring an area means dozens of
    Overpass/ACS calls — far too slow for a request cycle. The API creates the
    row, the worker fills it in, the map reads it back.
    """

    __tablename__ = "lead_searches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    query_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    query_kind: Mapped[str] = mapped_column(String(16), nullable=False)

    display_name: Mapped[str | None] = mapped_column(String(255))
    state_fips: Mapped[str | None] = mapped_column(String(2))
    county_fips: Mapped[str | None] = mapped_column(String(3))

    # The resolved area. `boundary` is the true ZCTA/place polygon; `bbox` is
    # kept alongside it for cheap map-fitting without parsing the polygon.
    boundary: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False)
    )
    bbox: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False)
    )
    center: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
    )

    h3_resolution: Mapped[int] = mapped_column(Integer, nullable=False, default=8)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=SearchStatus.PENDING, index=True
    )
    error: Mapped[str | None] = mapped_column(Text)

    cell_count: Mapped[int | None] = mapped_column(Integer)
    poi_count: Mapped[int | None] = mapped_column(Integer)

    requested_by: Mapped[str | None] = mapped_column(String(255), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "h3_resolution BETWEEN 5 AND 11", name="ck_lead_searches_h3_resolution"
        ),
        CheckConstraint(
            "status IN ('pending','scoring','complete','failed')",
            name="ck_lead_searches_status",
        ),
        Index("ix_lead_searches_created_at", "created_at"),
    )
