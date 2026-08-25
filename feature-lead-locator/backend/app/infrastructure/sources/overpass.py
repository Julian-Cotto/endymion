"""POIs from OpenStreetMap via Overpass.

Overpass is a free, shared, community-run endpoint. It rate-limits hard, 429s
under load, and occasionally 504s on big areas — so this adapter retries with
backoff and the results are cached in the `pois` table rather than re-fetched
per search.

The category mapping is the opinionated part. OSM tagging is open-ended
(thousands of amenity/shop values); the scoring model needs a small stable
vocabulary to weight against, so unknown tags collapse to OTHER rather than
inventing categories at runtime.
"""

from __future__ import annotations

import logging
import time

import httpx

from .base import BoundingBox, PoiCategory, PoiRecord
from .config import SourceSettings, get_source_settings

logger = logging.getLogger(__name__)

# Statuses worth backing off on rather than failing the search:
#   429 - rate limited (documented)
#   504 - query too heavy for the endpoint right now (documented)
#   502/503 - mirror or load balancer wobble
#   406 - undocumented, but observed in practice from a loaded endpoint for a
#         query that succeeded moments later. Not treated as fatal for that
#         reason; a real syntax error surfaces as 400.
_RETRYABLE_STATUS = frozenset({406, 429, 502, 503, 504})


# Which OSM tags we ask Overpass for. Kept narrow on purpose: fetching every
# node in a city would be gigabytes and mostly noise (benches, trees).
_QUERY_FILTERS = [
    'node["shop"]',
    'way["shop"]',
    'node["amenity"~"^(restaurant|cafe|fast_food|bar|pub|food_court|bank|pharmacy|hospital|clinic|doctors|school|college|university|library|townhall|community_centre|post_office|cinema|theatre|marketplace)$"]',
    'way["amenity"~"^(restaurant|cafe|fast_food|bar|pub|food_court|bank|pharmacy|hospital|clinic|doctors|school|college|university|library|townhall|community_centre|post_office|cinema|theatre|marketplace)$"]',
    'node["public_transport"="station"]',
    'node["railway"~"^(station|subway_entrance|tram_stop)$"]',
    'node["highway"="bus_stop"]',
    'node["office"]',
    'way["office"]',
    'node["tourism"~"^(hotel|motel|hostel|attraction|museum)$"]',
    'way["tourism"~"^(hotel|motel|hostel|attraction|museum)$"]',
    'node["leisure"~"^(park|fitness_centre|sports_centre|stadium|playground)$"]',
    'way["leisure"~"^(park|fitness_centre|sports_centre|stadium|playground)$"]',
]

# shop=* values that are grocery-ish. Grocery is split out from general retail
# because supermarkets are strong, reliable traffic anchors — a supermarket
# pulls very different footfall from a hairdresser.
_GROCERY_SHOPS = {
    "supermarket", "grocery", "greengrocer", "convenience", "butcher",
    "bakery", "deli", "general", "farm", "food",
}

_FOOD_AMENITIES = {"restaurant", "cafe", "fast_food", "bar", "pub", "food_court"}
_EDUCATION_AMENITIES = {"school", "college", "university", "library"}
_HEALTHCARE_AMENITIES = {"pharmacy", "hospital", "clinic", "doctors"}
_CIVIC_AMENITIES = {"townhall", "community_centre", "post_office", "marketplace"}
_LEISURE_AMENITIES = {"cinema", "theatre"}
_LODGING_TOURISM = {"hotel", "motel", "hostel"}


def categorize(tags: dict[str, str]) -> PoiCategory:
    """Map raw OSM tags to our vocabulary.

    Order matters: a node can carry several tags (a supermarket with an ATM),
    and the first match wins. Most-specific first.
    """
    shop = tags.get("shop")
    if shop:
        return PoiCategory.GROCERY if shop in _GROCERY_SHOPS else PoiCategory.RETAIL

    amenity = tags.get("amenity")
    if amenity:
        if amenity in _FOOD_AMENITIES:
            return PoiCategory.FOOD_DRINK
        if amenity in _EDUCATION_AMENITIES:
            return PoiCategory.EDUCATION
        if amenity in _HEALTHCARE_AMENITIES:
            return PoiCategory.HEALTHCARE
        if amenity in _CIVIC_AMENITIES:
            return PoiCategory.CIVIC
        if amenity in _LEISURE_AMENITIES:
            return PoiCategory.LEISURE
        if amenity == "bank":
            return PoiCategory.RETAIL

    if (
        tags.get("public_transport") == "station"
        or tags.get("railway") in {"station", "subway_entrance", "tram_stop"}
        or tags.get("highway") == "bus_stop"
    ):
        return PoiCategory.TRANSIT

    tourism = tags.get("tourism")
    if tourism:
        if tourism in _LODGING_TOURISM:
            return PoiCategory.LODGING
        return PoiCategory.LEISURE

    if tags.get("leisure"):
        return PoiCategory.LEISURE
    if tags.get("office"):
        return PoiCategory.OFFICE

    return PoiCategory.OTHER


def build_query(bbox: BoundingBox, timeout_seconds: int) -> str:
    """Overpass QL. bbox order is (south, west, north, east)."""
    bbox_str = f"{bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon}"
    parts = "\n  ".join(f"{f}({bbox_str});" for f in _QUERY_FILTERS)
    # `out center` gives ways a single representative point, so areas and nodes
    # come back in one shape the scorer can treat uniformly.
    return f"[out:json][timeout:{timeout_seconds}];\n(\n  {parts}\n);\nout center tags;"


class OverpassPoiSource:
    def __init__(
        self,
        settings: SourceSettings | None = None,
        client: httpx.Client | None = None,
        sleep: object = time.sleep,
    ) -> None:
        self._settings = settings or get_source_settings()
        self._client = client
        self._sleep = sleep

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._settings.overpass_timeout_seconds,
                headers={"User-Agent": self._settings.geocoder_user_agent},
            )
        return self._client

    def fetch_pois(self, bbox: BoundingBox) -> list[PoiRecord]:
        query = build_query(bbox, int(self._settings.overpass_timeout_seconds))
        payload = self._post_with_retry(query)
        return self._parse(payload)

    def _endpoints(self) -> list[str]:
        """Primary endpoint, then any configured mirrors."""
        endpoints = [self._settings.overpass_base_url]
        for mirror in self._settings.overpass_mirror_urls_list:
            if mirror not in endpoints:
                endpoints.append(mirror)
        return endpoints

    def _post_with_retry(self, query: str) -> dict:
        """Retry across attempts and mirrors.

        Overpass is free and shared, so transient rejection is normal traffic,
        not an exception: the same valid query was observed returning 406 and
        504 seconds apart while the endpoint was loaded. Retrying and then
        failing over to a mirror is the difference between "leads take a few
        seconds longer" and "the search errors".
        """
        last_exc: Exception | None = None
        endpoints = self._endpoints()

        for attempt in range(self._settings.overpass_max_retries):
            endpoint = endpoints[attempt % len(endpoints)]
            try:
                resp = self._http().post(endpoint, data={"data": query})
                if resp.status_code in _RETRYABLE_STATUS:
                    raise httpx.HTTPStatusError(
                        f"overpass busy: {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                # A genuine query bug (400) will never succeed on retry —
                # surface it now instead of burning the backoff budget.
                if status is not None and status not in _RETRYABLE_STATUS:
                    raise
                last_exc = exc
                backoff = 2**attempt
                logger.warning(
                    "overpass_retry",
                    extra={
                        "attempt": attempt + 1,
                        "status": status,
                        "endpoint": endpoint,
                        "backoff_s": backoff,
                    },
                )
                self._sleep(backoff)
        raise RuntimeError(
            f"Overpass failed after {self._settings.overpass_max_retries} attempts "
            f"across {len(endpoints)} endpoint(s)"
        ) from last_exc

    def _parse(self, payload: dict) -> list[PoiRecord]:
        records: list[PoiRecord] = []
        for element in payload.get("elements", []):
            # Nodes carry lat/lon directly; ways/relations get `center` from
            # `out center`.
            lat = element.get("lat")
            lon = element.get("lon")
            if lat is None or lon is None:
                center = element.get("center") or {}
                lat, lon = center.get("lat"), center.get("lon")
            if lat is None or lon is None:
                continue

            tags = element.get("tags") or {}
            records.append(
                PoiRecord(
                    source="osm",
                    source_id=f"{element.get('type')}/{element.get('id')}",
                    name=tags.get("name"),
                    category=categorize(tags),
                    lat=float(lat),
                    lon=float(lon),
                    tags=tags,
                )
            )
        return records


def build_poi_source(settings: SourceSettings | None = None) -> OverpassPoiSource:
    settings = settings or get_source_settings()
    if settings.poi_provider != "overpass":
        raise ValueError(
            f"Unknown poi_provider {settings.poi_provider!r}. "
            "Only 'overpass' is implemented."
        )
    return OverpassPoiSource(settings)
