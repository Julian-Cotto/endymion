"""Geometry helpers bridging h3 / our (lat, lon) contract / PostGIS.

Two coordinate conventions collide here and getting them crossed is the classic
GIS bug: h3 and our dataclasses use (lat, lon); shapely, WKT and PostGIS use
(x, y) = (lon, lat). Every conversion lives in this one file so the flip
happens in exactly one place.
"""

from __future__ import annotations

import h3
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree


def cell_polygon(h3_index: str) -> Polygon:
    """H3 cell -> shapely Polygon in (lon, lat)."""
    boundary = h3.cell_to_boundary(h3_index)  # [(lat, lon), ...]
    return Polygon([(lon, lat) for lat, lon in boundary])


def cell_point(h3_index: str) -> Point:
    lat, lon = h3.cell_to_latlng(h3_index)
    return Point(lon, lat)


def latlon_point(lat: float, lon: float) -> Point:
    return Point(lon, lat)


def rings_to_polygon(rings: list[list[tuple[float, float]]]) -> Polygon:
    """[(lat, lon), ...] rings (exterior first, rest holes) -> shapely Polygon."""
    exterior = [(lon, lat) for lat, lon in rings[0]]
    holes = [[(lon, lat) for lat, lon in ring] for ring in rings[1:]]
    return Polygon(exterior, holes)


def rings_to_multipolygon(rings: list[list[tuple[float, float]]]) -> MultiPolygon:
    """Wrap a single ring-set as MultiPolygon.

    Tract/boundary columns are MULTIPOLYGON so a single geometry type covers
    both simple shapes and the occasional multi-part one (a city with a
    detached annex). A lone polygon is just a one-member multipolygon.
    """
    return MultiPolygon([rings_to_polygon(rings)])


def to_wkb_element(geometry: BaseGeometry, srid: int = 4326):
    """shapely geometry -> GeoAlchemy2 value for an INSERT."""
    return from_shape(geometry, srid=srid)


def assign_cells_to_tracts(
    cells: list[str],
    tract_polygons: dict[str, BaseGeometry],
) -> dict[str, str]:
    """Map each cell to the tract GEOID whose polygon contains its centroid.

    STRtree (an R-tree) makes this O(cells * log tracts) instead of the naive
    O(cells * tracts) point-in-polygon sweep — a metro is thousands of each.
    Cells whose centroid lands in no tract (water, a gap at the county edge)
    are omitted; the demand term treats a missing mapping as unknown.
    """
    if not tract_polygons:
        return {}

    geoids = list(tract_polygons.keys())
    geometries = [tract_polygons[g] for g in geoids]
    tree = STRtree(geometries)

    mapping: dict[str, str] = {}
    for cell in cells:
        centroid = cell_point(cell)
        # query() prefilters by bounding box; confirm with actual containment.
        for idx in tree.query(centroid):
            if geometries[idx].contains(centroid):
                mapping[cell] = geoids[idx]
                break
    return mapping
