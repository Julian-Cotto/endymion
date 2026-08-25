"""Foot-traffic estimation.

The honest framing: Google exposes no foot-traffic API, and real visit counts
come from paid panels (Placer.ai, SafeGraph, Veraset). This module models a
*proxy* from free inputs instead — it is not a visit count, and its output is
only comparable within a single search.

The proxy asks: how much pedestrian activity would you expect here, given what
is around it? Nearby POIs generate footfall, weighted by how much traffic that
kind of place actually drives (a rail station or supermarket anchors far more
than an office), and attenuated by distance.

`ModeledTrafficSource` and a future `PlacerTrafficSource` both satisfy
TrafficSource, so the scoring engine never learns which one it got —
`is_measured` is the only thing that differs, and that exists so the UI can
stop calling a modeled guess a measurement.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import h3

from .base import PoiCategory, PoiRecord, TrafficSignal
from .config import SourceSettings, get_source_settings

logger = logging.getLogger(__name__)


# How much footfall each category generates. Ordinal judgement, not measured
# truth — the whole point of the pluggable TrafficSource is that these get
# replaced by real data. Calibrate against a paid feed before trusting them.
CATEGORY_TRAFFIC_WEIGHTS: dict[PoiCategory, float] = {
    PoiCategory.TRANSIT: 1.00,     # strongest reliable pedestrian generator
    PoiCategory.GROCERY: 0.90,     # high-frequency, repeat visits
    PoiCategory.FOOD_DRINK: 0.75,  # high volume, but clustered at meal times
    PoiCategory.RETAIL: 0.70,
    PoiCategory.EDUCATION: 0.65,   # dense but peaky and age-skewed
    PoiCategory.OFFICE: 0.60,      # weekday-only daytime population
    PoiCategory.LEISURE: 0.50,
    PoiCategory.HEALTHCARE: 0.45,  # visits are infrequent per person
    PoiCategory.CIVIC: 0.40,
    PoiCategory.LODGING: 0.35,
    PoiCategory.OTHER: 0.10,
}

# Distance decay by H3 ring. Ring 0 is the cell itself, ring 1 its 6 immediate
# neighbours, and so on. At res 8 a ring step is roughly 500m, so ring 2 is
# about a 1km walk — past that, footfall attribution is noise.
RING_DECAY: dict[int, float] = {0: 1.0, 1: 0.5, 2: 0.2}
MAX_RING = max(RING_DECAY)


class ModeledTrafficSource:
    """Free traffic proxy from POI density, category mix and distance decay."""

    def __init__(self, settings: SourceSettings | None = None) -> None:
        self._settings = settings or get_source_settings()

    @property
    def is_measured(self) -> bool:
        # Never claim measurement. The UI keys off this to label the number as
        # an estimate.
        return False

    def estimate(
        self, cells: list[str], pois: list[PoiRecord]
    ) -> list[TrafficSignal]:
        if not cells:
            return []

        resolution = h3.get_resolution(cells[0])

        # Bin POIs into cells once, then read neighbourhoods out of the bins.
        # The naive alternative — every cell against every POI — is O(cells x
        # pois): a city at res 9 is ~20k cells and ~10k POIs, i.e. 200M
        # distance computations per search. Binning makes it O(pois + cells*19).
        bins: dict[str, list[PoiRecord]] = defaultdict(list)
        for poi in pois:
            bins[h3.latlng_to_cell(poi.lat, poi.lon, resolution)].append(poi)

        signals: list[TrafficSignal] = []
        for cell in cells:
            total = 0.0
            components: dict[str, float] = defaultdict(float)

            for ring_index in range(MAX_RING + 1):
                decay = RING_DECAY[ring_index]
                ring = (
                    [cell]
                    if ring_index == 0
                    else h3.grid_ring(cell, ring_index)
                )
                for neighbour in ring:
                    for poi in bins.get(neighbour, ()):
                        weight = CATEGORY_TRAFFIC_WEIGHTS.get(poi.category, 0.1)
                        contribution = weight * decay
                        total += contribution
                        components[poi.category.value] += contribution

            signals.append(
                TrafficSignal(
                    h3_index=cell,
                    value=round(total, 6),
                    is_measured=False,
                    components={k: round(v, 6) for k, v in components.items()},
                )
            )
        return signals


def build_traffic_source(settings: SourceSettings | None = None):
    settings = settings or get_source_settings()
    if settings.traffic_provider == "modeled":
        return ModeledTrafficSource(settings)
    # The intended extension point: a measured feed slots in here and nothing
    # downstream changes.
    raise ValueError(
        f"Unknown traffic_provider {settings.traffic_provider!r}. "
        "Only 'modeled' is implemented; a paid feed would register here."
    )
