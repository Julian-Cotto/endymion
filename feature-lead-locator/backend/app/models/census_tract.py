"""Cached Census ACS demographics, tract level."""

from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base


class CensusTract(Base):
    """ACS values plus TIGER geometry for one census tract.

    Two sources, one row: the ACS API returns values with no shape, TIGERweb
    returns shapes with no values. The scoring engine needs both together —
    it assigns demographics to a hex cell by finding which tract the cell's
    centroid falls in, which requires the polygon.

    Nullable measures are not an oversight: ACS suppresses estimates for
    low-population tracts, and the model must treat "withheld" as unknown
    rather than zero.
    """

    __tablename__ = "census_tracts"

    # 11-digit GEOID (state 2 + county 3 + tract 6) uniquely identifies a
    # tract nationally, so it is the natural key.
    geoid: Mapped[str] = mapped_column(String(11), primary_key=True)

    state_fips: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    county_fips: Mapped[str] = mapped_column(String(3), nullable=False)

    geometry: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False)
    )

    population: Mapped[int | None] = mapped_column(Integer)
    median_household_income: Mapped[int | None] = mapped_column(Integer)
    households: Mapped[int | None] = mapped_column(Integer)
    # Land area in m^2, from TIGER. Needed for population density, which is
    # what the demand term actually wants — raw population conflates a dense
    # tract with a huge empty one.
    area_land_sq_m: Mapped[int | None] = mapped_column(BigInteger)

    acs_year: Mapped[int] = mapped_column(Integer, nullable=False)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_census_tracts_geometry", "geometry", postgresql_using="gist"),
        Index("ix_census_tracts_state_county", "state_fips", "county_fips"),
    )
