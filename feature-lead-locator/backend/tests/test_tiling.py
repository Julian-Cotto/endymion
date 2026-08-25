"""H3 tiling + guardrail tests. No network, no DB."""

from __future__ import annotations

import h3
import pytest

from app.domain.tiling import MIN_RESOLUTION, AreaTooLargeError, tile_area
from app.infrastructure.sources.base import BoundingBox, QueryKind, ResolvedArea
from app.infrastructure.sources.config import SourceSettings


def _area(rings=None, bbox=None) -> ResolvedArea:
    bbox = bbox or BoundingBox(min_lat=34.06, max_lat=34.08, min_lon=-118.41,
                               max_lon=-118.39)
    return ResolvedArea(
        query_raw="test",
        query_kind=QueryKind.ZIP,
        display_name="test",
        bbox=bbox,
        center_lat=bbox.centroid[0],
        center_lon=bbox.centroid[1],
        boundary_rings=rings,
    )


def test_tiles_bbox_when_no_boundary() -> None:
    tiling = tile_area(_area(), resolution=8, settings=SourceSettings())
    assert tiling.cells
    assert tiling.resolution == 8
    assert tiling.coarsened is False
    # Every returned index really is a res-8 cell.
    assert all(h3.get_resolution(c) == 8 for c in tiling.cells)


def test_tiles_true_boundary_when_present() -> None:
    # A boundary smaller than the bbox should yield fewer cells than the bbox.
    inner = [(34.068, -118.405), (34.072, -118.405), (34.072, -118.395),
             (34.068, -118.395), (34.068, -118.405)]
    with_boundary = tile_area(_area(rings=(tuple(inner),)), resolution=9,
                              settings=SourceSettings())
    bbox_only = tile_area(_area(), resolution=9, settings=SourceSettings())
    assert 0 < len(with_boundary.cells) < len(bbox_only.cells)


def test_coarsens_when_over_cap() -> None:
    # Force coarsening with a tiny cap: a res-9 tiling of the bbox is many
    # cells, so it must drop to a coarser resolution to fit.
    settings = SourceSettings(max_cells_per_search=5)
    tiling = tile_area(_area(), resolution=9, settings=settings)

    assert tiling.coarsened is True
    assert tiling.resolution < 9
    assert tiling.requested_resolution == 9
    assert len(tiling.cells) <= 5


def test_raises_when_uncappable_even_at_min_resolution() -> None:
    # A large area (several degrees) yields many cells even at the coarsest
    # resolution, so a cap below that count cannot be satisfied by coarsening.
    big = BoundingBox(min_lat=30.0, max_lat=36.0, min_lon=-102.0, max_lon=-96.0)
    settings = SourceSettings(max_cells_per_search=2)
    with pytest.raises(AreaTooLargeError) as excinfo:
        tile_area(_area(bbox=big), resolution=9, settings=settings)
    assert excinfo.value.cap == 2
    assert excinfo.value.cell_count > 2


def test_tiny_area_still_yields_at_least_one_cell() -> None:
    # A sub-cell area at a coarse resolution tiles to nothing from h3; the
    # centroid fallback keeps the search non-empty.
    tiny = BoundingBox(min_lat=34.0700, max_lat=34.0701, min_lon=-118.4001,
                       max_lon=-118.4000)
    tiling = tile_area(_area(bbox=tiny), resolution=5, settings=SourceSettings())
    assert len(tiling.cells) >= 1


def test_never_coarsens_below_min_resolution() -> None:
    settings = SourceSettings(max_cells_per_search=1)
    try:
        tiling = tile_area(_area(), resolution=10, settings=settings)
        assert tiling.resolution >= MIN_RESOLUTION
    except AreaTooLargeError:
        pass  # also acceptable — it refused rather than over-coarsening


def test_default_resolution_used_when_unspecified() -> None:
    settings = SourceSettings(default_h3_resolution=7)
    tiling = tile_area(_area(), settings=settings)
    assert tiling.requested_resolution == 7
