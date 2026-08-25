"""Modeled traffic proxy tests.

These pin the *behaviour* of the model (decay, weighting, additivity), not the
specific weight values — those are explicitly provisional and meant to be
recalibrated against a measured feed.
"""

from __future__ import annotations

import h3
import pytest

from app.infrastructure.sources.base import PoiCategory, PoiRecord
from app.infrastructure.sources.traffic import (
    CATEGORY_TRAFFIC_WEIGHTS,
    RING_DECAY,
    ModeledTrafficSource,
)

RES = 8
CENTER_LAT, CENTER_LON = 34.07, -118.40


def _cell(lat: float = CENTER_LAT, lon: float = CENTER_LON) -> str:
    return h3.latlng_to_cell(lat, lon, RES)


def _poi(category: PoiCategory, lat: float, lon: float, id_: str = "n/1") -> PoiRecord:
    return PoiRecord(
        source="osm", source_id=id_, name=None, category=category, lat=lat, lon=lon
    )


def _source() -> ModeledTrafficSource:
    return ModeledTrafficSource()


class TestContract:
    def test_never_claims_to_be_measured(self) -> None:
        # The UI keys off this to avoid presenting a guess as a visit count.
        assert _source().is_measured is False

    def test_empty_cells_returns_empty(self) -> None:
        assert _source().estimate([], [_poi(PoiCategory.RETAIL, 34.07, -118.4)]) == []

    def test_cells_with_no_pois_score_zero(self) -> None:
        signals = _source().estimate([_cell()], [])
        assert len(signals) == 1
        assert signals[0].value == 0.0
        assert signals[0].components == {}

    def test_one_signal_per_cell_preserving_order(self) -> None:
        cells = list(h3.grid_disk(_cell(), 1))
        signals = _source().estimate(cells, [])
        assert [s.h3_index for s in signals] == cells


class TestWeighting:
    def test_transit_outweighs_lodging(self) -> None:
        # Relative ordering is the claim; the absolute numbers are provisional.
        cell = _cell()
        lat, lon = h3.cell_to_latlng(cell)

        transit = _source().estimate([cell], [_poi(PoiCategory.TRANSIT, lat, lon)])
        lodging = _source().estimate([cell], [_poi(PoiCategory.LODGING, lat, lon)])

        assert transit[0].value > lodging[0].value

    def test_contributions_are_additive(self) -> None:
        cell = _cell()
        lat, lon = h3.cell_to_latlng(cell)
        pois = [
            _poi(PoiCategory.RETAIL, lat, lon, "n/1"),
            _poi(PoiCategory.RETAIL, lat, lon, "n/2"),
        ]

        one = _source().estimate([cell], pois[:1])[0].value
        two = _source().estimate([cell], pois)[0].value

        assert two == pytest.approx(one * 2)

    def test_components_break_down_by_category(self) -> None:
        cell = _cell()
        lat, lon = h3.cell_to_latlng(cell)
        signals = _source().estimate(
            [cell],
            [_poi(PoiCategory.RETAIL, lat, lon, "n/1"),
             _poi(PoiCategory.TRANSIT, lat, lon, "n/2")],
        )

        comps = signals[0].components
        assert set(comps) == {"retail", "transit"}
        assert comps["transit"] == pytest.approx(
            CATEGORY_TRAFFIC_WEIGHTS[PoiCategory.TRANSIT]
        )
        assert sum(comps.values()) == pytest.approx(signals[0].value)

    def test_in_cell_poi_scores_full_weight(self) -> None:
        cell = _cell()
        lat, lon = h3.cell_to_latlng(cell)
        value = _source().estimate([cell], [_poi(PoiCategory.GROCERY, lat, lon)])[0].value
        assert value == pytest.approx(CATEGORY_TRAFFIC_WEIGHTS[PoiCategory.GROCERY])


class TestDistanceDecay:
    def test_neighbour_poi_contributes_less_than_in_cell(self) -> None:
        cell = _cell()
        neighbour = [c for c in h3.grid_ring(cell, 1)][0]
        n_lat, n_lon = h3.cell_to_latlng(neighbour)
        c_lat, c_lon = h3.cell_to_latlng(cell)

        near = _source().estimate([cell], [_poi(PoiCategory.RETAIL, c_lat, c_lon)])
        far = _source().estimate([cell], [_poi(PoiCategory.RETAIL, n_lat, n_lon)])

        assert far[0].value < near[0].value
        assert far[0].value == pytest.approx(
            CATEGORY_TRAFFIC_WEIGHTS[PoiCategory.RETAIL] * RING_DECAY[1]
        )

    def test_poi_beyond_max_ring_is_ignored(self) -> None:
        # Past ~1km, attributing footfall to a cell is noise.
        cell = _cell()
        distant = list(h3.grid_ring(cell, max(RING_DECAY) + 1))[0]
        d_lat, d_lon = h3.cell_to_latlng(distant)

        signals = _source().estimate([cell], [_poi(PoiCategory.TRANSIT, d_lat, d_lon)])

        assert signals[0].value == 0.0

    def test_decay_is_monotonic_across_rings(self) -> None:
        assert RING_DECAY[0] > RING_DECAY[1] > RING_DECAY[2]


def test_scales_to_many_cells_without_pairwise_blowup() -> None:
    # Guards the binning optimisation: naive cell x poi would be 2k*2k = 4M
    # distance computations. This should stay trivially fast.
    center = _cell()
    cells = list(h3.grid_disk(center, 25))
    lat, lon = h3.cell_to_latlng(center)
    pois = [
        _poi(PoiCategory.RETAIL, lat + i * 1e-4, lon + i * 1e-4, f"n/{i}")
        for i in range(2000)
    ]

    signals = ModeledTrafficSource().estimate(cells, pois)

    assert len(signals) == len(cells)
    assert any(s.value > 0 for s in signals)
