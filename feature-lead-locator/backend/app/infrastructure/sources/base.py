"""Source contracts.

These Protocols are the seam that keeps the free MVP stack swappable for paid
feeds. The scoring engine depends only on the types here, never on Overpass /
Nominatim / Census concretes, so adding Placer.ai or Google Places means adding
one adapter and changing a settings value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable


class PoiCategory(StrEnum):
    """Normalized POI categories.

    OSM tagging is open-ended and inconsistent; the scoring model needs a small
    stable vocabulary to weight against. Mapping lives in overpass.py.
    """

    RETAIL = "retail"
    GROCERY = "grocery"
    FOOD_DRINK = "food_drink"
    TRANSIT = "transit"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    LEISURE = "leisure"
    OFFICE = "office"
    LODGING = "lodging"
    CIVIC = "civic"
    OTHER = "other"


class QueryKind(StrEnum):
    ZIP = "zip"
    CITY = "city"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """WGS84 bbox. Kept dumb on purpose — geometry lives in PostGIS."""

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def __post_init__(self) -> None:
        if self.min_lat > self.max_lat:
            raise ValueError(f"min_lat {self.min_lat} > max_lat {self.max_lat}")
        if self.min_lon > self.max_lon:
            raise ValueError(f"min_lon {self.min_lon} > max_lon {self.max_lon}")

    @property
    def centroid(self) -> tuple[float, float]:
        return ((self.min_lat + self.max_lat) / 2, (self.min_lon + self.max_lon) / 2)

    def as_polygon_coords(self) -> list[tuple[float, float]]:
        """Closed ring, (lat, lon) order to match h3's convention."""
        return [
            (self.min_lat, self.min_lon),
            (self.max_lat, self.min_lon),
            (self.max_lat, self.max_lon),
            (self.min_lat, self.max_lon),
            (self.min_lat, self.min_lon),
        ]


@dataclass(frozen=True, slots=True)
class ResolvedArea:
    """A user's "90210" or "Austin, TX" turned into something tileable."""

    query_raw: str
    query_kind: QueryKind
    display_name: str
    bbox: BoundingBox
    center_lat: float
    center_lon: float
    # Present when the geocoder identified a US state/county, which the Census
    # adapter needs to address ACS.
    state_fips: str | None = None
    county_fips: str | None = None
    # True boundary rings as [(lat, lon), ...] per ring, exterior first.
    # Tiling this instead of `bbox` matters: a bbox around a city sweeps in
    # neighbouring towns and water, which would be scored as if in-area.
    # Falls back to the bbox when a source has no polygon.
    boundary_rings: tuple[tuple[tuple[float, float], ...], ...] | None = None

    def tiling_rings(self) -> tuple[tuple[tuple[float, float], ...], ...]:
        if self.boundary_rings:
            return self.boundary_rings
        return (tuple(self.bbox.as_polygon_coords()),)


class GeocodeError(Exception):
    """Base for geocoding failures that should surface to the user."""


class AmbiguousQueryError(GeocodeError):
    """Query matched several places and needs disambiguating.

    "Austin" alone matches 5 states — guessing one would silently prospect the
    wrong market, so callers must re-ask with a state.
    """

    def __init__(self, query: str, candidates: list[str]) -> None:
        self.query = query
        self.candidates = candidates
        super().__init__(
            f"{query!r} matched {len(candidates)} places: {', '.join(candidates[:8])}"
            ". Add a state, e.g. 'Austin, TX'."
        )


@dataclass(frozen=True, slots=True)
class PoiRecord:
    source: str
    source_id: str
    name: str | None
    category: PoiCategory
    lat: float
    lon: float
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TractDemographics:
    """ACS values for one census tract. None means "ACS withheld it"."""

    geoid: str
    population: int | None
    median_household_income: int | None
    households: int | None
    acs_year: int


@dataclass(frozen=True, slots=True)
class TrafficSignal:
    """Per-cell traffic estimate.

    `value` is unitless and only comparable within a single search — it is a
    modeled proxy, not a visit count. A paid feed would set `is_measured=True`
    and carry real visit counts in `components`.
    """

    h3_index: str
    value: float
    is_measured: bool
    components: dict[str, float] = field(default_factory=dict)


@runtime_checkable
class Geocoder(Protocol):
    def resolve(self, query: str) -> ResolvedArea | None: ...


@runtime_checkable
class PoiSource(Protocol):
    def fetch_pois(self, bbox: BoundingBox) -> list[PoiRecord]: ...


@runtime_checkable
class DemographicsSource(Protocol):
    def fetch_tracts(
        self, state_fips: str, county_fips: str
    ) -> list[TractDemographics]: ...


@runtime_checkable
class TrafficSource(Protocol):
    """The swap point for paid foot-traffic data."""

    @property
    def is_measured(self) -> bool: ...

    def estimate(
        self, cells: list[str], pois: list[PoiRecord]
    ) -> list[TrafficSignal]: ...
