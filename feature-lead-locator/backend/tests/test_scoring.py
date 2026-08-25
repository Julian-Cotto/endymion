"""Opportunity-model tests. Pure functions, no network, no DB."""

from __future__ import annotations

import h3
import pytest

from app.domain.scoring import (
    ScoreWeights,
    _minmax_normalize,
    score_cells,
)
from app.infrastructure.sources.base import (
    PoiCategory,
    PoiRecord,
    TractDemographics,
    TrafficSignal,
)

RES = 8
ANCHOR = h3.latlng_to_cell(34.07, -118.40, RES)


def _grid() -> list[str]:
    return list(h3.grid_disk(ANCHOR, 2))


def _poi(cat: PoiCategory, cell: str, id_: str) -> PoiRecord:
    lat, lon = h3.cell_to_latlng(cell)
    return PoiRecord(source="t", source_id=id_, name=None, category=cat, lat=lat, lon=lon)


class TestNormalize:
    def test_scales_to_unit_range(self) -> None:
        out = _minmax_normalize({"a": 10.0, "b": 20.0, "c": 30.0})
        assert out == {"a": 0.0, "b": 0.5, "c": 1.0}

    def test_flat_input_collapses_to_zero_not_nan(self) -> None:
        # A term with no variation carries no ranking info -> contributes 0.
        assert _minmax_normalize({"a": 5.0, "b": 5.0}) == {"a": 0.0, "b": 0.0}

    def test_all_zero_is_safe(self) -> None:
        assert _minmax_normalize({"a": 0.0, "b": 0.0}) == {"a": 0.0, "b": 0.0}

    def test_empty(self) -> None:
        assert _minmax_normalize({}) == {}


class TestScoreCells:
    def test_empty_cells_returns_empty(self) -> None:
        assert score_cells([], [], [], {}, {}, {}) == []

    def test_ranks_by_score_descending(self) -> None:
        cells = _grid()
        signals = [TrafficSignal(h3_index=c, value=float(i), is_measured=False,
                                 components={}) for i, c in enumerate(cells)]
        scores = score_cells(cells, signals, [], {}, {}, {})

        assert scores[0].rank == 1
        assert [s.rank for s in scores] == list(range(1, len(scores) + 1))
        vals = [s.score for s in scores]
        assert vals == sorted(vals, reverse=True)

    def test_traffic_drives_score_when_only_term_present(self) -> None:
        cells = _grid()
        best = cells[0]
        signals = [
            TrafficSignal(h3_index=c, value=(100.0 if c == best else 1.0),
                          is_measured=False, components={})
            for c in cells
        ]
        scores = score_cells(cells, signals, [], {}, {}, {})
        assert scores[0].h3_index == best

    def test_saturation_subtracts(self) -> None:
        # Two cells, equal traffic; the one with competitors must rank lower.
        cells = _grid()
        c_clean, c_saturated = cells[0], cells[1]
        signals = [TrafficSignal(h3_index=c, value=10.0, is_measured=False,
                                 components={}) for c in cells]
        pois = [
            _poi(PoiCategory.RETAIL, c_saturated, "r1"),
            _poi(PoiCategory.FOOD_DRINK, c_saturated, "r2"),
            _poi(PoiCategory.GROCERY, c_saturated, "r3"),
        ]
        weights = ScoreWeights(traffic=0.5, demand=0.0, saturation=0.5, anchor_pull=0.0)
        scores = score_cells(cells, signals, pois, {}, {}, {}, weights=weights)
        by_cell = {s.h3_index: s for s in scores}
        assert by_cell[c_clean].score > by_cell[c_saturated].score

    def test_demand_from_demographics(self) -> None:
        cells = _grid()
        rich_cell, poor_cell = cells[0], cells[1]
        cell_to_tract = {rich_cell: "T_RICH", poor_cell: "T_POOR"}
        tracts = {
            "T_RICH": TractDemographics("T_RICH", population=5000,
                                        median_household_income=150000,
                                        households=2000, acs_year=2023),
            "T_POOR": TractDemographics("T_POOR", population=500,
                                        median_household_income=25000,
                                        households=200, acs_year=2023),
        }
        area = {"T_RICH": 1_000_000, "T_POOR": 1_000_000}  # equal area
        signals = [TrafficSignal(h3_index=c, value=1.0, is_measured=False,
                                 components={}) for c in cells]
        weights = ScoreWeights(traffic=0.0, demand=1.0, saturation=0.0, anchor_pull=0.0)
        scores = score_cells(cells, signals, [], cell_to_tract, tracts, area,
                             weights=weights)
        by_cell = {s.h3_index: s for s in scores}
        assert by_cell[rich_cell].demand > by_cell[poor_cell].demand

    def test_suppressed_demographics_do_not_poison_demand(self) -> None:
        cells = _grid()[:2]
        cell_to_tract = {cells[0]: "T1", cells[1]: "T2"}
        tracts = {
            "T1": TractDemographics("T1", population=None,  # ACS-suppressed
                                    median_household_income=None,
                                    households=None, acs_year=2023),
            "T2": TractDemographics("T2", population=1000,
                                    median_household_income=50000,
                                    households=400, acs_year=2023),
        }
        area = {"T1": 1_000_000, "T2": 1_000_000}
        signals = [TrafficSignal(h3_index=c, value=1.0, is_measured=False,
                                 components={}) for c in cells]
        scores = score_cells(cells, signals, [], cell_to_tract, tracts, area)
        by_cell = {s.h3_index: s for s in scores}
        # Suppressed tract -> demand 0, not a crash or negative.
        assert by_cell[cells[0]].breakdown["raw"]["demand"] == 0.0

    def test_missing_land_area_yields_zero_demand_not_infinity(self) -> None:
        cells = _grid()[:1]
        tracts = {"T1": TractDemographics("T1", population=1000,
                                          median_household_income=50000,
                                          households=400, acs_year=2023)}
        scores = score_cells(cells, [TrafficSignal(cells[0], 1.0, False, {})],
                             [], {cells[0]: "T1"}, tracts, {"T1": None})
        assert scores[0].breakdown["raw"]["demand"] == 0.0

    def test_breakdown_records_weights_and_terms(self) -> None:
        cells = _grid()[:1]
        weights = ScoreWeights(traffic=0.4, demand=0.3, saturation=0.2, anchor_pull=0.1)
        scores = score_cells(cells, [TrafficSignal(cells[0], 5.0, False, {"retail": 5.0})],
                             [], {}, {}, {}, weights=weights)
        bd = scores[0].breakdown
        assert bd["weights"]["traffic"] == 0.4
        assert "normalized" in bd and "raw" in bd
        assert bd["traffic_components"] == {"retail": 5.0}


class TestWeights:
    def test_defaults(self) -> None:
        w = ScoreWeights()
        assert (w.traffic, w.demand, w.saturation, w.anchor_pull) == (0.4, 0.3, 0.2, 0.1)

    def test_from_mapping_partial_override(self) -> None:
        w = ScoreWeights.from_mapping({"traffic": 0.9})
        assert w.traffic == 0.9
        assert w.demand == 0.3  # untouched default

    def test_from_mapping_ignores_unknown_keys(self) -> None:
        w = ScoreWeights.from_mapping({"traffic": 0.5, "bogus": 99})
        assert w.traffic == 0.5

    def test_from_mapping_none(self) -> None:
        assert ScoreWeights.from_mapping(None) == ScoreWeights()
