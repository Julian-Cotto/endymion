"""Geometry-bridge tests — mostly guarding the (lat,lon) <-> (lon,lat) flip."""

from __future__ import annotations

import h3
from shapely.geometry import Polygon

from app.infrastructure import geo


def test_cell_polygon_is_in_lon_lat_order() -> None:
    cell = h3.latlng_to_cell(34.07, -118.40, 8)
    poly = geo.cell_polygon(cell)
    # Shapely x is longitude (~-118), y is latitude (~34). If flipped, x would
    # be ~34 — this is the bug the whole module exists to prevent.
    minx, miny, maxx, maxy = poly.bounds
    assert -119 < minx < -118 and -119 < maxx < -118
    assert 34 < miny < 35 and 34 < maxy < 35


def test_cell_point_matches_centroid() -> None:
    cell = h3.latlng_to_cell(30.27, -97.74, 9)
    lat, lon = h3.cell_to_latlng(cell)
    pt = geo.cell_point(cell)
    assert pt.x == lon and pt.y == lat


def test_rings_to_polygon_flips_and_orders() -> None:
    # (lat, lon) input -> (lon, lat) shapely.
    rings = [[(34.0, -118.0), (34.0, -117.0), (35.0, -117.0), (35.0, -118.0)]]
    poly = geo.rings_to_polygon(rings)
    assert poly.exterior.coords[0] == (-118.0, 34.0)


def test_rings_to_polygon_honours_holes() -> None:
    exterior = [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0)]
    hole = [(2.0, 2.0), (2.0, 4.0), (4.0, 4.0), (4.0, 2.0)]
    poly = geo.rings_to_polygon([exterior, hole])
    assert len(poly.interiors) == 1


def test_rings_to_multipolygon_wraps_single() -> None:
    rings = [[(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]]
    mp = geo.rings_to_multipolygon(rings)
    assert mp.geom_type == "MultiPolygon"
    assert len(mp.geoms) == 1


class TestAssignCellsToTracts:
    def test_assigns_cell_to_containing_tract(self) -> None:
        cell = h3.latlng_to_cell(34.07, -118.40, 8)
        lat, lon = h3.cell_to_latlng(cell)
        # A generous box around the centroid, in (lon, lat).
        containing = Polygon([(lon - 0.1, lat - 0.1), (lon + 0.1, lat - 0.1),
                              (lon + 0.1, lat + 0.1), (lon - 0.1, lat + 0.1)])
        far = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
        mapping = geo.assign_cells_to_tracts([cell], {"HIT": containing, "MISS": far})
        assert mapping == {cell: "HIT"}

    def test_cell_in_no_tract_is_omitted(self) -> None:
        cell = h3.latlng_to_cell(34.07, -118.40, 8)
        far = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
        mapping = geo.assign_cells_to_tracts([cell], {"MISS": far})
        assert mapping == {}

    def test_empty_tracts_returns_empty(self) -> None:
        cell = h3.latlng_to_cell(34.07, -118.40, 8)
        assert geo.assign_cells_to_tracts([cell], {}) == {}
