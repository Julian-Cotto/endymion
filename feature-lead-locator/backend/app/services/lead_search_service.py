"""Orchestrates a lead search: geocode -> tile -> gather -> score -> persist.

This is the seam the API and the async worker both call. It owns one
transaction per run and flips the search's status as it goes, so a crash
mid-run leaves the row in `scoring`/`failed` rather than a half-written
`complete`.

Demographics are treated as optional throughout: no Census key, or an ACS
outage, degrades the demand term to zero and sets `demographics_available`
false — the search still resolves, tiles, and scores traffic. Everything else
failing is fatal to the run.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

import httpx

from app.domain import scoring
from app.domain.scoring import ScoreWeights
from app.domain.tiling import AreaTooLargeError, tile_area
from app.infrastructure import geo
from app.infrastructure.repositories import (
    HexCellRepository,
    PoiRepository,
    SearchRepository,
    TractRepository,
)
from app.infrastructure.sources.base import (
    AmbiguousQueryError,
    Geocoder,
    PoiRecord,
    PoiSource,
    ResolvedArea,
    TractDemographics,
    TrafficSource,
)
from app.infrastructure.sources.census_acs import (
    CensusAcsSource,
    MissingCensusKeyError,
    TigerTractGeometrySource,
    build_demographics_source,
    build_tract_geometry_source,
)
from app.infrastructure.sources.config import SourceSettings, get_source_settings
from app.infrastructure.sources.geocoder import build_geocoder
from app.infrastructure.sources.overpass import build_poi_source
from app.infrastructure.sources.traffic import build_traffic_source
from app.models.lead_search import LeadSearch, SearchStatus

logger = logging.getLogger(__name__)


class SearchNotFoundError(Exception):
    pass


@dataclass(slots=True)
class ScoreOutcome:
    search_id: uuid.UUID
    cell_count: int
    poi_count: int
    resolution: int
    coarsened: bool
    demographics_available: bool


class LeadSearchService:
    """All source adapters are injected so the service is unit-testable with
    fakes and the async worker can share one wired instance."""

    def __init__(
        self,
        db,
        *,
        geocoder: Geocoder | None = None,
        poi_source: PoiSource | None = None,
        traffic_source: TrafficSource | None = None,
        demographics_source: CensusAcsSource | None = None,
        tract_geometry_source: TigerTractGeometrySource | None = None,
        settings: SourceSettings | None = None,
    ) -> None:
        self._db = db
        self._settings = settings or get_source_settings()
        self._geocoder = geocoder or build_geocoder(self._settings)
        self._poi_source = poi_source or build_poi_source(self._settings)
        self._traffic_source = traffic_source or build_traffic_source(self._settings)
        self._demographics = demographics_source or build_demographics_source(
            self._settings
        )
        self._tract_geometry = tract_geometry_source or build_tract_geometry_source(
            self._settings
        )

        self.searches = SearchRepository(db)
        self.pois = PoiRepository(db)
        self.tracts = TractRepository(db)
        self.cells = HexCellRepository(db)

    # -- entry points --------------------------------------------------------

    def create_search(
        self, query: str, *, requested_by: str | None, resolution: int | None
    ) -> LeadSearch:
        """Resolve the query and persist a PENDING search. Raises
        AmbiguousQueryError up to the API so it can 409 with candidates."""
        area = self._geocoder.resolve(query)  # may raise AmbiguousQueryError
        if area is None:
            raise ValueError(f"Could not resolve {query!r} to a US area.")

        search = self.searches.create(
            query_raw=query,
            query_kind=area.query_kind.value,
            requested_by=requested_by,
            h3_resolution=resolution or self._settings.default_h3_resolution,
        )
        # Stash the resolved area now so a later score() need not re-geocode.
        self._persist_area(search, area, search.h3_resolution)
        self._db.commit()
        return search

    def score_search(
        self, search_id: uuid.UUID, weights: ScoreWeights | None = None
    ) -> ScoreOutcome:
        """Run the full pipeline for an existing search. Idempotent: re-scoring
        replaces the previous cell set."""
        search = self.searches.get(search_id)
        if search is None:
            raise SearchNotFoundError(str(search_id))

        self.searches.set_status(search, SearchStatus.SCORING)
        self._db.commit()

        try:
            outcome = self._run_pipeline(search, weights)
            self._db.commit()
            return outcome
        except Exception as exc:
            self._db.rollback()
            # Reload and mark failed in a fresh transaction so the error sticks.
            search = self.searches.get(search_id)
            if search is not None:
                self.searches.set_status(
                    search, SearchStatus.FAILED, error=str(exc)[:1000]
                )
                self._db.commit()
            logger.exception("score_search_failed", extra={"search_id": str(search_id)})
            raise

    # -- pipeline ------------------------------------------------------------

    def _run_pipeline(
        self, search: LeadSearch, weights: ScoreWeights | None
    ) -> ScoreOutcome:
        area = self._geocoder.resolve(search.query_raw)
        if area is None:
            raise ValueError(f"Area {search.query_raw!r} no longer resolves.")

        tiling = tile_area(area, resolution=search.h3_resolution, settings=self._settings)

        # POIs over the bbox (superset of the boundary; scoring uses rings, not
        # the exact polygon, so a slightly wider POI set is correct).
        pois = self._poi_source.fetch_pois(area.bbox)
        self.pois.upsert_many(pois)

        demographics, tract_geoms, demographics_available = self._gather_demographics(
            area
        )
        cell_to_tract = self._assign_tracts(tiling.cells, tract_geoms)
        tract_area = {g: v.get("area_land_sq_m") for g, v in tract_geoms.items()}

        self.tracts.upsert_many(
            demographics,
            tract_geoms,
            state_fips=area.state_fips or "",
            county_fips=area.county_fips or "",
        )

        traffic_signals = self._traffic_source.estimate(tiling.cells, pois)

        scores = scoring.score_cells(
            cells=tiling.cells,
            traffic_signals=traffic_signals,
            pois=pois,
            cell_to_tract=cell_to_tract,
            tracts=demographics,
            tract_area_sq_m=tract_area,
            weights=weights,
        )

        self.cells.replace_for_search(search.id, scores, tiling.resolution)
        self._persist_area(search, area, tiling.resolution)
        self.searches.complete(
            search, cell_count=len(scores), poi_count=len(pois)
        )

        return ScoreOutcome(
            search_id=search.id,
            cell_count=len(scores),
            poi_count=len(pois),
            resolution=tiling.resolution,
            coarsened=tiling.coarsened,
            demographics_available=demographics_available,
        )

    # -- helpers -------------------------------------------------------------

    def _gather_demographics(
        self, area: ResolvedArea
    ) -> tuple[dict[str, TractDemographics], dict[str, dict], bool]:
        """Fetch ACS + TIGER geometry. Degrades to geometry-only (or nothing)
        rather than failing the search."""
        if not area.state_fips or not area.county_fips:
            logger.info("demographics_skipped_no_fips")
            return {}, {}, False

        try:
            geoms = self._tract_geometry.fetch_geometries(
                area.state_fips, area.county_fips
            )
        except httpx.HTTPError as exc:
            logger.warning("tract_geometry_failed", extra={"error": str(exc)})
            geoms = {}

        try:
            demo_list = self._demographics.fetch_tracts(
                area.state_fips, area.county_fips
            )
            demographics = {t.geoid: t for t in demo_list}
            available = True
        except MissingCensusKeyError:
            # Expected when no key is configured — not an error, just no demand.
            logger.info("demographics_unavailable_no_key")
            demographics, available = {}, False
        except httpx.HTTPError as exc:
            logger.warning("acs_fetch_failed", extra={"error": str(exc)})
            demographics, available = {}, False

        return demographics, geoms, available

    def _assign_tracts(
        self, cells: list[str], tract_geoms: dict[str, dict]
    ) -> dict[str, str]:
        if not tract_geoms:
            return {}
        polygons = {
            geoid: geo.rings_to_polygon(v["rings"])
            for geoid, v in tract_geoms.items()
            if v.get("rings")
        }
        return geo.assign_cells_to_tracts(cells, polygons)

    def _persist_area(
        self, search: LeadSearch, area: ResolvedArea, resolution: int
    ) -> None:
        boundary = None
        if area.boundary_rings:
            boundary = geo.rings_to_multipolygon(
                [list(r) for r in area.boundary_rings]
            )
        bbox_poly = geo.rings_to_polygon([area.bbox.as_polygon_coords()])
        center = geo.latlon_point(area.center_lat, area.center_lon)
        self.searches.set_resolved_area(
            search,
            display_name=area.display_name,
            state_fips=area.state_fips,
            county_fips=area.county_fips,
            boundary=boundary,
            bbox=bbox_poly,
            center=center,
            h3_resolution=resolution,
        )
