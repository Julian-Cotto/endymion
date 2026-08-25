"""The opportunity model — the actual product.

Turns a tiling + POIs + demographics + a traffic signal into a ranked,
explainable score per cell:

    opportunity = w1*traffic + w2*demand - w3*saturation + w4*anchor_pull

Every term is normalized to [0, 1] *within the search* before weighting,
because the raw units are incomparable (a traffic proxy value vs people per
km2 vs a competitor count) and because "high opportunity" is only ever meant
relative to the area you asked about. A quiet cell in Manhattan and a busy one
in rural Montana should not be scored on the same absolute scale.

The weights are deliberate guesses, overridable per search. They cannot be
validated without measured foot-traffic ground truth — see NEXT_STEPS.md. Treat
scores as ordinal within one search, never as absolute truth.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import h3

from app.infrastructure.sources.base import (
    PoiCategory,
    PoiRecord,
    TractDemographics,
    TrafficSignal,
)

logger = logging.getLogger(__name__)


# --- anchor_pull ------------------------------------------------------------
# Major regional draws whose pull reaches beyond the immediate block. This is
# what keeps anchor_pull from double-counting the traffic proxy: the proxy sums
# ALL nearby POIs over rings 0-2 (~1 km), whereas anchor_pull looks only at
# these anchor-class POIs over a WIDER radius, rewarding a cell for sitting
# near a big generator even when its own surroundings are sparse (rings 3-5,
# which the proxy never sees).
ANCHOR_CATEGORIES: frozenset[PoiCategory] = frozenset(
    {
        PoiCategory.TRANSIT,     # stations pull commuters from a whole line
        PoiCategory.EDUCATION,   # universities/colleges anchor a district
        PoiCategory.HEALTHCARE,  # hospitals are all-day regional destinations
        PoiCategory.LEISURE,     # stadiums, big parks, cinemas
    }
)
# Anchor influence reaches further than ambient footfall. Ring ~= 500m at res 8.
ANCHOR_RING_DECAY: dict[int, float] = {0: 1.0, 1: 0.8, 2: 0.6, 3: 0.4, 4: 0.25, 5: 0.15}
ANCHOR_MAX_RING = max(ANCHOR_RING_DECAY)

# --- saturation -------------------------------------------------------------
# "Already served" commercial competition. Domain-specific by nature; this
# default targets general retail/service siting. Override COMPETITOR_CATEGORIES
# per vertical once one is chosen.
COMPETITOR_CATEGORIES: frozenset[PoiCategory] = frozenset(
    {PoiCategory.RETAIL, PoiCategory.FOOD_DRINK, PoiCategory.GROCERY}
)
SATURATION_RING_DECAY: dict[int, float] = {0: 1.0, 1: 0.5}
SATURATION_MAX_RING = max(SATURATION_RING_DECAY)


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    traffic: float = 0.40
    demand: float = 0.30
    saturation: float = 0.20
    anchor_pull: float = 0.10

    @classmethod
    def from_mapping(cls, data: dict | None) -> "ScoreWeights":
        if not data:
            return cls()
        known = {f: data[f] for f in ("traffic", "demand", "saturation",
                                      "anchor_pull") if f in data}
        return cls(**known)


@dataclass(slots=True)
class CellScore:
    h3_index: str
    score: float
    traffic_proxy: float
    demand: float
    saturation: float
    anchor_pull: float
    # Normalized [0,1] terms + the raw inputs behind them, for the drill-down.
    breakdown: dict = field(default_factory=dict)
    rank: int | None = None


def _minmax_normalize(values: dict[str, float]) -> dict[str, float]:
    """Scale a {cell: value} map to [0, 1]. Flat input -> all zeros.

    All-equal (including all-zero) collapses to 0.0 rather than blowing up on a
    zero range: a term with no variation carries no ranking information, so it
    should contribute nothing, not NaN.
    """
    if not values:
        return {}
    lo = min(values.values())
    hi = max(values.values())
    span = hi - lo
    if span <= 0:
        return {k: 0.0 for k in values}
    return {k: (v - lo) / span for k, v in values.items()}


def _raw_anchor_pull(cells: list[str], pois: list[PoiRecord]) -> dict[str, float]:
    """Proximity to anchor-class POIs over the wide anchor radius."""
    resolution = h3.get_resolution(cells[0])
    from collections import defaultdict

    bins: dict[str, list[PoiCategory]] = defaultdict(list)
    for poi in pois:
        if poi.category in ANCHOR_CATEGORIES:
            bins[h3.latlng_to_cell(poi.lat, poi.lon, resolution)].append(poi.category)

    out: dict[str, float] = {}
    for cell in cells:
        total = 0.0
        for ring_index in range(ANCHOR_MAX_RING + 1):
            decay = ANCHOR_RING_DECAY[ring_index]
            ring = [cell] if ring_index == 0 else h3.grid_ring(cell, ring_index)
            for neighbour in ring:
                total += decay * len(bins.get(neighbour, ()))
        out[cell] = total
    return out


def _raw_saturation(cells: list[str], pois: list[PoiRecord]) -> dict[str, float]:
    """Competitor density in/near the cell."""
    resolution = h3.get_resolution(cells[0])
    from collections import defaultdict

    bins: dict[str, int] = defaultdict(int)
    for poi in pois:
        if poi.category in COMPETITOR_CATEGORIES:
            bins[h3.latlng_to_cell(poi.lat, poi.lon, resolution)] += 1

    out: dict[str, float] = {}
    for cell in cells:
        total = 0.0
        for ring_index in range(SATURATION_MAX_RING + 1):
            decay = SATURATION_RING_DECAY[ring_index]
            ring = [cell] if ring_index == 0 else h3.grid_ring(cell, ring_index)
            for neighbour in ring:
                total += decay * bins.get(neighbour, 0)
        out[cell] = total
    return out


def _raw_demand(
    cells: list[str],
    cell_to_tract: dict[str, str],
    tracts: dict[str, TractDemographics],
    tract_area_sq_m: dict[str, int | None],
) -> dict[str, float]:
    """Population density x income signal, per cell, via the cell's tract.

    Density not raw population: a dense tract and a huge empty one can hold the
    same headcount but mean very different demand. Income scales it — spending
    power, not just bodies. ACS-suppressed values (None) contribute 0 for that
    cell rather than poisoning the normalization.

    Every cell gets an entry (0.0 when it maps to no tract, or the tract lacks
    data) — a cell absent from this map would break normalization downstream.
    """
    out: dict[str, float] = {c: 0.0 for c in cells}
    for cell in cells:
        geoid = cell_to_tract.get(cell)
        if geoid is None:
            continue
        tract = tracts.get(geoid)
        if tract is None or tract.population is None:
            continue
        area = tract_area_sq_m.get(geoid)
        if not area:
            continue
        density = tract.population / (area / 1_000_000)  # people per km2
        income = tract.median_household_income or 0
        # Multiplicative: density and spending power reinforce. Income in $10k
        # units keeps the product from being dominated by raw dollars.
        out[cell] = density * (income / 10_000 if income else 1.0)
    return out


def score_cells(
    cells: list[str],
    traffic_signals: list[TrafficSignal],
    pois: list[PoiRecord],
    cell_to_tract: dict[str, str],
    tracts: dict[str, TractDemographics],
    tract_area_sq_m: dict[str, int | None],
    weights: ScoreWeights | None = None,
) -> list[CellScore]:
    """Score and rank cells. Returns them sorted by score desc (rank filled)."""
    if not cells:
        return []
    weights = weights or ScoreWeights()

    traffic_by_cell = {s.h3_index: s.value for s in traffic_signals}
    traffic_components = {s.h3_index: s.components for s in traffic_signals}

    raw_traffic = {c: traffic_by_cell.get(c, 0.0) for c in cells}
    raw_anchor = _raw_anchor_pull(cells, pois)
    raw_saturation = _raw_saturation(cells, pois)
    raw_demand = _raw_demand(cells, cell_to_tract, tracts, tract_area_sq_m)

    n_traffic = _minmax_normalize(raw_traffic)
    n_anchor = _minmax_normalize(raw_anchor)
    n_saturation = _minmax_normalize(raw_saturation)
    n_demand = _minmax_normalize(raw_demand)

    scores: list[CellScore] = []
    for cell in cells:
        t, d = n_traffic[cell], n_demand[cell]
        s, a = n_saturation[cell], n_anchor[cell]
        # Saturation subtracts: more existing competition, less opportunity.
        opportunity = (
            weights.traffic * t
            + weights.demand * d
            - weights.saturation * s
            + weights.anchor_pull * a
        )
        scores.append(
            CellScore(
                h3_index=cell,
                score=round(opportunity, 6),
                traffic_proxy=round(t, 6),
                demand=round(d, 6),
                saturation=round(s, 6),
                anchor_pull=round(a, 6),
                breakdown={
                    "weights": {
                        "traffic": weights.traffic,
                        "demand": weights.demand,
                        "saturation": weights.saturation,
                        "anchor_pull": weights.anchor_pull,
                    },
                    "normalized": {
                        "traffic": round(t, 4),
                        "demand": round(d, 4),
                        "saturation": round(s, 4),
                        "anchor_pull": round(a, 4),
                    },
                    "raw": {
                        "traffic": round(raw_traffic[cell], 4),
                        "demand": round(raw_demand.get(cell, 0.0), 4),
                        "saturation": round(raw_saturation[cell], 4),
                        "anchor_pull": round(raw_anchor[cell], 4),
                    },
                    "traffic_components": traffic_components.get(cell, {}),
                    "tract": cell_to_tract.get(cell),
                },
            )
        )

    scores.sort(key=lambda cs: cs.score, reverse=True)
    for rank, cs in enumerate(scores, start=1):
        cs.rank = rank
    return scores
