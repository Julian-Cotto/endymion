"""LeadSearchService orchestration.

Integration test: the service writes PostGIS geometry, which SQLite cannot
fake, so it needs a real PostGIS. Skips (not fails) when one is unreachable, so
CI without Docker stays green while a local run with the DB up gets full
coverage. All *external* sources are faked — no network, deterministic.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("psycopg2")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.infrastructure.sources.base import (
    BoundingBox,
    PoiCategory,
    PoiRecord,
    QueryKind,
    ResolvedArea,
    TractDemographics,
    TrafficSignal,
)
from app.models.lead_search import SearchStatus
from app.services.lead_search_service import LeadSearchService

DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://leads:leads@localhost:5435/lead_locator"
)


def _pg_available() -> bool:
    try:
        eng = create_engine(DB_URL)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_available(), reason=f"PostGIS not reachable at {DB_URL}"
)


# --- fakes ------------------------------------------------------------------

_BBOX = BoundingBox(min_lat=34.06, max_lat=34.08, min_lon=-118.41, max_lon=-118.39)
_SQUARE = ((34.06, -118.41), (34.08, -118.41), (34.08, -118.39), (34.06, -118.39))


class FakeGeocoder:
    def resolve(self, query: str) -> ResolvedArea:
        return ResolvedArea(
            query_raw=query, query_kind=QueryKind.ZIP, display_name="Test Area, CA",
            bbox=_BBOX, center_lat=34.07, center_lon=-118.40,
            state_fips="06", county_fips="037", boundary_rings=(_SQUARE,),
        )


class FakePoiSource:
    def __init__(self, n: int = 50) -> None:
        self._n = n

    def fetch_pois(self, bbox: BoundingBox) -> list[PoiRecord]:
        import random
        rng = random.Random(7)
        cats = list(PoiCategory)
        return [
            PoiRecord(source="fake", source_id=f"node/{i}", name=f"p{i}",
                      category=rng.choice(cats),
                      lat=rng.uniform(bbox.min_lat, bbox.max_lat),
                      lon=rng.uniform(bbox.min_lon, bbox.max_lon))
            for i in range(self._n)
        ]


class FakeTrafficSource:
    is_measured = False

    def estimate(self, cells, pois):
        return [TrafficSignal(h3_index=c, value=float(i + 1), is_measured=False,
                              components={"retail": float(i + 1)})
                for i, c in enumerate(cells)]


class FakeDemographics:
    def __init__(self, available: bool = True) -> None:
        self._available = available

    def fetch_tracts(self, state_fips, county_fips):
        if not self._available:
            from app.infrastructure.sources.census_acs import MissingCensusKeyError
            raise MissingCensusKeyError()
        return [TractDemographics(geoid="06037700600", population=4000,
                                  median_household_income=90000, households=1500,
                                  acs_year=2023)]


class FakeTractGeometry:
    def fetch_geometries(self, state_fips, county_fips):
        # One big tract covering the whole test bbox.
        return {
            "06037700600": {
                "rings": [[(34.05, -118.42), (34.09, -118.42),
                           (34.09, -118.38), (34.05, -118.38)]],
                "area_land_sq_m": 2_000_000,
            }
        }


@pytest.fixture
def session():
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def service(session):
    return LeadSearchService(
        session,
        geocoder=FakeGeocoder(),
        poi_source=FakePoiSource(),
        traffic_source=FakeTrafficSource(),
        demographics_source=FakeDemographics(available=True),
        tract_geometry_source=FakeTractGeometry(),
    )


def _cleanup(session, search_id) -> None:
    session.execute(text("DELETE FROM hex_cells WHERE search_id=:i"),
                    {"i": str(search_id)})
    session.execute(text("DELETE FROM lead_searches WHERE id=:i"),
                    {"i": str(search_id)})
    session.commit()


class TestScoreSearch:
    def test_full_pipeline_persists_and_completes(self, service, session) -> None:
        search = service.create_search("90210", requested_by="tester", resolution=8)
        try:
            outcome = service.score_search(search.id)

            assert outcome.cell_count > 0
            assert outcome.poi_count == 50
            assert outcome.demographics_available is True

            row = session.execute(
                text("SELECT status, cell_count FROM lead_searches WHERE id=:i"),
                {"i": str(search.id)},
            ).one()
            assert row[0] == SearchStatus.COMPLETE.value
            assert row[1] == outcome.cell_count

            n_cells = session.execute(
                text("SELECT count(*) FROM hex_cells WHERE search_id=:i"),
                {"i": str(search.id)},
            ).scalar()
            assert n_cells == outcome.cell_count

            # Geometry landed as SRID-4326 polygons.
            srid = session.execute(
                text("SELECT DISTINCT ST_SRID(geometry) FROM hex_cells "
                     "WHERE search_id=:i"),
                {"i": str(search.id)},
            ).scalar()
            assert srid == 4326
        finally:
            _cleanup(session, search.id)

    def test_ranks_are_dense_and_ordered(self, service, session) -> None:
        search = service.create_search("90210", requested_by="t", resolution=8)
        try:
            service.score_search(search.id)
            ranks = [c.rank for c in service.cells.for_search(search.id)]
            assert ranks == list(range(1, len(ranks) + 1))
        finally:
            _cleanup(session, search.id)

    def test_rescore_replaces_not_duplicates(self, service, session) -> None:
        search = service.create_search("90210", requested_by="t", resolution=8)
        try:
            service.score_search(search.id)
            first = session.execute(
                text("SELECT count(*) FROM hex_cells WHERE search_id=:i"),
                {"i": str(search.id)},
            ).scalar()
            service.score_search(search.id)
            second = session.execute(
                text("SELECT count(*) FROM hex_cells WHERE search_id=:i"),
                {"i": str(search.id)},
            ).scalar()
            assert first == second
        finally:
            _cleanup(session, search.id)

    def test_missing_census_key_degrades_gracefully(self, session) -> None:
        service = LeadSearchService(
            session,
            geocoder=FakeGeocoder(),
            poi_source=FakePoiSource(),
            traffic_source=FakeTrafficSource(),
            demographics_source=FakeDemographics(available=False),
            tract_geometry_source=FakeTractGeometry(),
        )
        search = service.create_search("90210", requested_by="t", resolution=8)
        try:
            outcome = service.score_search(search.id)
            # Search still completes; demand simply absent.
            assert outcome.demographics_available is False
            assert outcome.cell_count > 0
            row = session.execute(
                text("SELECT status FROM lead_searches WHERE id=:i"),
                {"i": str(search.id)},
            ).scalar()
            assert row == SearchStatus.COMPLETE.value
        finally:
            _cleanup(session, search.id)

    def test_pipeline_failure_marks_search_failed(self, session) -> None:
        class BoomPoiSource:
            def fetch_pois(self, bbox):
                raise RuntimeError("overpass down")

        service = LeadSearchService(
            session,
            geocoder=FakeGeocoder(),
            poi_source=BoomPoiSource(),
            traffic_source=FakeTrafficSource(),
            demographics_source=FakeDemographics(),
            tract_geometry_source=FakeTractGeometry(),
        )
        search = service.create_search("90210", requested_by="t", resolution=8)
        try:
            with pytest.raises(RuntimeError, match="overpass down"):
                service.score_search(search.id)
            row = session.execute(
                text("SELECT status, error FROM lead_searches WHERE id=:i"),
                {"i": str(search.id)},
            ).one()
            assert row[0] == SearchStatus.FAILED.value
            assert "overpass down" in row[1]
        finally:
            _cleanup(session, search.id)
