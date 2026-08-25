"""Zip/city -> tileable area, via the Census's own TIGERweb service.

Why not Nominatim (the obvious free choice): it returns 403 for this client and
its usage policy caps automated traffic. Working around that would mean
spoofing a browser User-Agent to evade their block. TIGERweb is the better fit
regardless, since this product is US-only:

  * authoritative (it *is* the Census geography), no key, no UA policy
  * returns real ZCTA/place polygons, not a bounding rectangle
  * same source of truth as the ACS demographics we join against

Two layers of tigerWMS_Current are used:
  * layer 2  - 2020 Census ZIP Code Tabulation Areas (zip queries)
  * layer 28 - Incorporated Places (city queries)
  * layer 30 - Census Designated Places (fallback for unincorporated towns)

County FIPS still comes from the Census geocoder point lookup, because a ZCTA
does not carry one (zips straddle counties).
"""

from __future__ import annotations

import logging
import re

import httpx

from .base import (
    AmbiguousQueryError,
    BoundingBox,
    QueryKind,
    ResolvedArea,
)
from .config import SourceSettings, get_source_settings
from .states import FIPS_TO_STATE_ABBR, resolve_state_fips

logger = logging.getLogger(__name__)

_ZIP_RE = re.compile(r"^\s*(\d{5})(?:-\d{4})?\s*$")

TIGERWEB_BASE = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
    "/tigerWMS_Current/MapServer"
)
LAYER_ZCTA = 2
LAYER_INCORPORATED_PLACE = 28
LAYER_DESIGNATED_PLACE = 30

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"


def classify_query(query: str) -> QueryKind:
    return QueryKind.ZIP if _ZIP_RE.match(query) else QueryKind.CITY


def parse_city_query(query: str) -> tuple[str, str | None]:
    """"Austin, TX" -> ("Austin", "48"). Returns (city, state_fips|None)."""
    parts = [p.strip() for p in query.split(",")]
    if len(parts) >= 2:
        state_fips = resolve_state_fips(parts[-1])
        if state_fips:
            return ", ".join(parts[:-1]).strip(), state_fips
    # Also accept "Austin TX" with no comma.
    tokens = query.rsplit(None, 1)
    if len(tokens) == 2:
        state_fips = resolve_state_fips(tokens[1])
        if state_fips:
            return tokens[0].strip(), state_fips
    return query.strip(), None


def _rings_to_latlon(
    rings: list[list[list[float]]],
) -> tuple[tuple[tuple[float, float], ...], ...]:
    """Esri rings are [[lon, lat], ...]; h3 and our contract want (lat, lon)."""
    return tuple(tuple((pt[1], pt[0]) for pt in ring) for ring in rings)


def _bbox_from_rings(
    rings: tuple[tuple[tuple[float, float], ...], ...],
) -> BoundingBox:
    lats = [pt[0] for ring in rings for pt in ring]
    lons = [pt[1] for ring in rings for pt in ring]
    return BoundingBox(
        min_lat=min(lats), max_lat=max(lats), min_lon=min(lons), max_lon=max(lons)
    )


class TigerwebGeocoder:
    """Geocoder backed by Census TIGERweb. US-only by construction."""

    def __init__(
        self,
        settings: SourceSettings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or get_source_settings()
        self._client = client

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._settings.http_timeout_seconds,
                headers={"User-Agent": self._settings.geocoder_user_agent},
            )
        return self._client

    def _query_layer(
        self, layer: int, where: str, *, geometry: bool
    ) -> list[dict]:
        params = {
            # "*" rather than a field list: the layers disagree on schema —
            # ZCTAs have no STATE/CENTLAT, and naming a missing field is a 400.
            "where": where,
            "outFields": "*",
            "returnGeometry": "true" if geometry else "false",
            "outSR": "4326",
            "f": "json",
        }
        resp = self._http().get(f"{TIGERWEB_BASE}/{layer}/query", params=params)
        resp.raise_for_status()
        payload = resp.json()
        if "error" in payload:
            raise httpx.HTTPError(f"TIGERweb error: {payload['error']}")
        return payload.get("features", [])

    def resolve(self, query: str) -> ResolvedArea | None:
        query = query.strip()
        if not query:
            return None
        if classify_query(query) is QueryKind.ZIP:
            return self._resolve_zip(query)
        return self._resolve_city(query)

    def _resolve_zip(self, query: str) -> ResolvedArea | None:
        zip5 = _ZIP_RE.match(query).group(1)
        features = self._query_layer(
            LAYER_ZCTA, f"ZCTA5='{zip5}'", geometry=True
        )
        if not features:
            return None
        return self._to_area(query, QueryKind.ZIP, features[0], f"ZCTA5 {zip5}")

    def _resolve_city(self, query: str) -> ResolvedArea | None:
        city, state_fips = parse_city_query(query)
        city_escaped = city.replace("'", "''")

        for layer in (LAYER_INCORPORATED_PLACE, LAYER_DESIGNATED_PLACE):
            where = f"BASENAME='{city_escaped}'"
            if state_fips:
                where += f" AND STATE='{state_fips}'"

            features = self._query_layer(layer, where, geometry=False)
            if not features:
                continue
            if len(features) > 1:
                # Never guess: "Austin" is a real place in 5 states.
                candidates = [
                    f"{f['attributes']['NAME']}, "
                    f"{FIPS_TO_STATE_ABBR.get(f['attributes']['STATE'], '??')}"
                    for f in features
                ]
                raise AmbiguousQueryError(query, sorted(candidates))

            # Re-fetch the single match with geometry (cheaper than pulling
            # polygons for every candidate on the first pass).
            attrs = features[0]["attributes"]
            with_geom = self._query_layer(
                layer, f"GEOID='{attrs['GEOID']}'", geometry=True
            )
            if not with_geom:
                continue
            return self._to_area(
                query, QueryKind.CITY, with_geom[0], attrs.get("NAME", city)
            )
        return None

    def _to_area(
        self, query: str, kind: QueryKind, feature: dict, fallback_name: str
    ) -> ResolvedArea:
        attrs = feature["attributes"]
        rings = _rings_to_latlon(feature["geometry"]["rings"])
        bbox = _bbox_from_rings(rings)

        center_lat = float(attrs["CENTLAT"]) if attrs.get("CENTLAT") else bbox.centroid[0]
        center_lon = float(attrs["CENTLON"]) if attrs.get("CENTLON") else bbox.centroid[1]

        state_fips = attrs.get("STATE") or None
        county_fips = None
        looked_up_state, looked_up_county = self._lookup_fips(center_lat, center_lon)
        # A ZCTA has no STATE attribute and can straddle counties; the point
        # lookup is the only way to pin it to one.
        state_fips = state_fips or looked_up_state
        county_fips = looked_up_county

        display = attrs.get("NAME") or fallback_name
        if state_fips and (abbr := FIPS_TO_STATE_ABBR.get(state_fips)):
            display = f"{display}, {abbr}"

        return ResolvedArea(
            query_raw=query,
            query_kind=kind,
            display_name=display,
            bbox=bbox,
            center_lat=center_lat,
            center_lon=center_lon,
            state_fips=state_fips,
            county_fips=county_fips,
            boundary_rings=rings,
        )

    def _lookup_fips(self, lat: float, lon: float) -> tuple[str | None, str | None]:
        try:
            resp = self._http().get(
                CENSUS_GEOCODER_URL,
                params={
                    "x": str(lon),
                    "y": str(lat),
                    "benchmark": "Public_AR_Current",
                    "vintage": "Current_Current",
                    "layers": "Census Tracts",
                    "format": "json",
                },
            )
            resp.raise_for_status()
            tracts = resp.json()["result"]["geographies"].get("Census Tracts") or []
            if not tracts:
                return None, None
            return tracts[0].get("STATE"), tracts[0].get("COUNTY")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            # Demographics degrade to absent rather than failing the search.
            logger.warning("fips_lookup_failed", extra={"error": str(exc)})
            return None, None


def build_geocoder(settings: SourceSettings | None = None) -> TigerwebGeocoder:
    settings = settings or get_source_settings()
    if settings.geocoder_provider != "tigerweb":
        raise ValueError(
            f"Unknown geocoder_provider {settings.geocoder_provider!r}. "
            "Only 'tigerweb' is implemented."
        )
    return TigerwebGeocoder(settings)
