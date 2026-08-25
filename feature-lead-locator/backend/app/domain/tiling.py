"""Tile a resolved area into H3 cells.

Kept separate from scoring because it has one job with real failure modes: a
whole-city polygon at res 9 can be >100k cells, which is both a compute problem
(scoring is per-cell) and a UX problem (an unreadable map). The guardrail
coarsens resolution before giving up, and always reports what it did rather
than silently returning a truncated set.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import h3

from app.infrastructure.sources.base import ResolvedArea
from app.infrastructure.sources.config import SourceSettings, get_source_settings

logger = logging.getLogger(__name__)

# How far we will coarsen to fit under the cell cap. res 5 ~= 252 km2 per cell,
# already coarse enough that a single metro fits in a handful of cells; going
# coarser stops being useful as "leads".
MIN_RESOLUTION = 5


@dataclass(frozen=True, slots=True)
class Tiling:
    cells: list[str]
    resolution: int
    # True when the requested resolution was coarsened to fit under the cap.
    # Callers surface this so the map can say "zoomed out to fit".
    coarsened: bool
    requested_resolution: int


class AreaTooLargeError(Exception):
    """The area cannot be tiled under the cap even at MIN_RESOLUTION."""

    def __init__(self, cell_count: int, cap: int) -> None:
        self.cell_count = cell_count
        self.cap = cap
        super().__init__(
            f"Area yields {cell_count} cells at the coarsest resolution "
            f"(res {MIN_RESOLUTION}), over the {cap} cap. Pick a smaller area."
        )


def _polygon_for(area: ResolvedArea) -> "h3.LatLngPoly":
    """Build an h3 polygon from the area's boundary, honouring holes.

    tiling_rings() returns the exterior ring first; any further rings are
    holes (a ZCTA with an enclosed exclave, say). h3.LatLngPoly takes
    (exterior, *holes), all as lists of (lat, lon).
    """
    rings = area.tiling_rings()
    exterior = [list(pt) for pt in rings[0]]
    holes = [[list(pt) for pt in ring] for ring in rings[1:]]
    return h3.LatLngPoly(exterior, *holes)


def _count_at(poly: "h3.LatLngPoly", resolution: int) -> int:
    # polygon_to_cells is the expensive call; counting is just len of it. There
    # is no cheaper "how many cells would this be" primitive, so this is the
    # cost of the guardrail. Accepted — it runs a handful of times at most.
    return len(h3.polygon_to_cells(poly, res=resolution))


def tile_area(
    area: ResolvedArea,
    resolution: int | None = None,
    settings: SourceSettings | None = None,
) -> Tiling:
    """Tile the area's true boundary, coarsening if it blows the cell cap."""
    settings = settings or get_source_settings()
    requested = resolution if resolution is not None else settings.default_h3_resolution
    cap = settings.max_cells_per_search

    poly = _polygon_for(area)

    current = requested
    while current >= MIN_RESOLUTION:
        cells = list(h3.polygon_to_cells(poly, res=current))
        if not cells:
            # An area smaller than one cell at this resolution (a tiny ZCTA at
            # a coarse res) tiles to nothing. A search with zero cells is
            # useless, so anchor it to the cell containing the centroid.
            cells = [h3.latlng_to_cell(area.center_lat, area.center_lon, current)]
        if len(cells) <= cap:
            if current != requested:
                logger.warning(
                    "tiling_coarsened",
                    extra={
                        "requested_resolution": requested,
                        "used_resolution": current,
                        "cell_count": len(cells),
                        "cap": cap,
                    },
                )
            return Tiling(
                cells=list(cells),
                resolution=current,
                coarsened=current != requested,
                requested_resolution=requested,
            )
        current -= 1

    # Even the coarsest resolution overflows — refuse rather than truncate.
    overflow = _count_at(poly, MIN_RESOLUTION)
    raise AreaTooLargeError(overflow, cap)
