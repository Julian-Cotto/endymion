"""PostGIS persistence for the four models.

Thin data-access layer over SQLAlchemy sessions: the service owns the
transaction (one commit per scoring run), repositories only build and stage
statements. Bulk paths use PostgreSQL upserts because POIs and tracts are
shared caches re-fetched across searches — insert-or-refresh, never duplicate.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from geoalchemy2.shape import from_shape
from shapely.geometry.base import BaseGeometry
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.domain.scoring import CellScore
from app.infrastructure import geo
from app.infrastructure.sources.base import PoiRecord, TractDemographics
from app.models.census_tract import CensusTract
from app.models.hex_cell import HexCell
from app.models.lead_search import LeadSearch, SearchStatus
from app.models.poi import Poi


class SearchRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        query_raw: str,
        query_kind: str,
        requested_by: str | None,
        h3_resolution: int,
    ) -> LeadSearch:
        search = LeadSearch(
            query_raw=query_raw,
            query_kind=query_kind,
            requested_by=requested_by,
            h3_resolution=h3_resolution,
            status=SearchStatus.PENDING,
        )
        self._db.add(search)
        self._db.flush()  # populate id without ending the transaction
        return search

    def get(self, search_id: uuid.UUID) -> LeadSearch | None:
        return self._db.get(LeadSearch, search_id)

    def set_status(
        self, search: LeadSearch, status: SearchStatus, error: str | None = None
    ) -> None:
        search.status = status
        search.error = error

    def set_resolved_area(
        self,
        search: LeadSearch,
        *,
        display_name: str,
        state_fips: str | None,
        county_fips: str | None,
        boundary: BaseGeometry | None,
        bbox: BaseGeometry,
        center: BaseGeometry,
        h3_resolution: int,
    ) -> None:
        search.display_name = display_name
        search.state_fips = state_fips
        search.county_fips = county_fips
        if boundary is not None:
            search.boundary = from_shape(boundary, srid=4326)
        search.bbox = from_shape(bbox, srid=4326)
        search.center = from_shape(center, srid=4326)
        search.h3_resolution = h3_resolution

    def complete(
        self, search: LeadSearch, *, cell_count: int, poi_count: int
    ) -> None:
        search.status = SearchStatus.COMPLETE
        search.cell_count = cell_count
        search.poi_count = poi_count
        search.completed_at = datetime.now(timezone.utc)


class PoiRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_many(self, pois: list[PoiRecord]) -> int:
        """Insert or refresh by (source, source_id). Returns rows written."""
        if not pois:
            return 0
        rows = [
            {
                "id": uuid.uuid4(),
                "source": p.source,
                "source_id": p.source_id,
                "name": p.name,
                "category": p.category.value,
                "geometry": from_shape(geo.latlon_point(p.lat, p.lon), srid=4326),
                "tags": p.tags,
                "fetched_at": datetime.now(timezone.utc),
            }
            for p in pois
        ]
        stmt = pg_insert(Poi).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_pois_source_id",
            set_={
                "name": stmt.excluded.name,
                "category": stmt.excluded.category,
                "geometry": stmt.excluded.geometry,
                "tags": stmt.excluded.tags,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        self._db.execute(stmt)
        return len(rows)

    def in_bbox(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> list[Poi]:
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        return list(
            self._db.execute(
                select(Poi).where(func.ST_Intersects(Poi.geometry, envelope))
            ).scalars()
        )


class TractRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_many(
        self,
        demographics: dict[str, TractDemographics],
        geometries: dict[str, dict],
        *,
        state_fips: str,
        county_fips: str,
    ) -> int:
        """Merge ACS values with TIGER geometry, keyed by GEOID.

        The two sources don't perfectly align (ACS may report a tract TIGER
        omits and vice versa); the union is stored, with whichever half is
        present. area_land_sq_m comes only from TIGER.
        """
        geoids = set(demographics) | set(geometries)
        if not geoids:
            return 0

        rows = []
        now = datetime.now(timezone.utc)
        for geoid in geoids:
            demo = demographics.get(geoid)
            geom = geometries.get(geoid)
            multipolygon = None
            area = None
            if geom and geom.get("rings"):
                multipolygon = from_shape(
                    geo.rings_to_multipolygon(geom["rings"]), srid=4326
                )
                area = geom.get("area_land_sq_m")
            rows.append(
                {
                    "geoid": geoid,
                    "state_fips": geoid[:2] if len(geoid) >= 2 else state_fips,
                    "county_fips": geoid[2:5] if len(geoid) >= 5 else county_fips,
                    "geometry": multipolygon,
                    "population": demo.population if demo else None,
                    "median_household_income": (
                        demo.median_household_income if demo else None
                    ),
                    "households": demo.households if demo else None,
                    "area_land_sq_m": area,
                    "acs_year": demo.acs_year if demo else 0,
                    "fetched_at": now,
                }
            )

        stmt = pg_insert(CensusTract).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["geoid"],
            set_={
                "geometry": stmt.excluded.geometry,
                "population": stmt.excluded.population,
                "median_household_income": stmt.excluded.median_household_income,
                "households": stmt.excluded.households,
                "area_land_sq_m": stmt.excluded.area_land_sq_m,
                "acs_year": stmt.excluded.acs_year,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        self._db.execute(stmt)
        return len(rows)


class HexCellRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def replace_for_search(
        self, search_id: uuid.UUID, scores: list[CellScore], resolution: int
    ) -> int:
        """Delete any prior cells for the search, then bulk insert the new set.

        Replace rather than upsert: a re-score with different weights produces a
        wholly new ranking, and stale cells from a previous run must not linger.
        """
        self._db.query(HexCell).filter(HexCell.search_id == search_id).delete()
        if not scores:
            return 0

        rows = [
            {
                "id": uuid.uuid4(),
                "search_id": search_id,
                "h3_index": cs.h3_index,
                "resolution": resolution,
                "geometry": from_shape(geo.cell_polygon(cs.h3_index), srid=4326),
                "centroid": from_shape(geo.cell_point(cs.h3_index), srid=4326),
                "score": cs.score,
                "rank": cs.rank,
                "traffic_proxy": cs.traffic_proxy,
                "demand": cs.demand,
                "saturation": cs.saturation,
                "anchor_pull": cs.anchor_pull,
                "score_breakdown": cs.breakdown,
            }
            for cs in scores
        ]
        self._db.execute(pg_insert(HexCell), rows)
        return len(rows)

    def for_search(
        self, search_id: uuid.UUID, limit: int | None = None
    ) -> list[HexCell]:
        stmt = (
            select(HexCell)
            .where(HexCell.search_id == search_id)
            .order_by(HexCell.rank)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self._db.execute(stmt).scalars())

    def get_cell(self, search_id: uuid.UUID, h3_index: str) -> HexCell | None:
        return self._db.execute(
            select(HexCell).where(
                HexCell.search_id == search_id, HexCell.h3_index == h3_index
            )
        ).scalar_one_or_none()
