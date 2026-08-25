"""Overpass adapter tests: category mapping, parsing, and retry behaviour."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.infrastructure.sources.base import BoundingBox, PoiCategory
from app.infrastructure.sources.config import SourceSettings
from app.infrastructure.sources.overpass import (
    OverpassPoiSource,
    build_query,
    categorize,
)

OVERPASS = "https://overpass-api.de/api/interpreter"
MIRROR = "https://overpass.kumi.systems/api/interpreter"


def _settings(**kw) -> SourceSettings:
    return SourceSettings(
        overpass_base_url=OVERPASS,
        overpass_mirror_urls=MIRROR,
        overpass_max_retries=3,
        **kw,
    )


def _bbox() -> BoundingBox:
    return BoundingBox(min_lat=34.06, max_lat=34.08, min_lon=-118.41, max_lon=-118.39)


class TestCategorize:
    @pytest.mark.parametrize(
        ("tags", "expected"),
        [
            # Grocery is split from retail because supermarkets anchor traffic
            # very differently from a hairdresser.
            ({"shop": "supermarket"}, PoiCategory.GROCERY),
            ({"shop": "convenience"}, PoiCategory.GROCERY),
            ({"shop": "bakery"}, PoiCategory.GROCERY),
            ({"shop": "hairdresser"}, PoiCategory.RETAIL),
            ({"shop": "clothes"}, PoiCategory.RETAIL),
            ({"amenity": "restaurant"}, PoiCategory.FOOD_DRINK),
            ({"amenity": "cafe"}, PoiCategory.FOOD_DRINK),
            ({"amenity": "school"}, PoiCategory.EDUCATION),
            ({"amenity": "pharmacy"}, PoiCategory.HEALTHCARE),
            ({"amenity": "post_office"}, PoiCategory.CIVIC),
            ({"amenity": "cinema"}, PoiCategory.LEISURE),
            ({"amenity": "bank"}, PoiCategory.RETAIL),
            ({"railway": "station"}, PoiCategory.TRANSIT),
            ({"highway": "bus_stop"}, PoiCategory.TRANSIT),
            ({"public_transport": "station"}, PoiCategory.TRANSIT),
            ({"tourism": "hotel"}, PoiCategory.LODGING),
            ({"tourism": "museum"}, PoiCategory.LEISURE),
            ({"leisure": "park"}, PoiCategory.LEISURE),
            ({"office": "lawyer"}, PoiCategory.OFFICE),
        ],
    )
    def test_maps_tags(self, tags: dict, expected: PoiCategory) -> None:
        assert categorize(tags) is expected

    def test_unknown_tags_collapse_to_other(self) -> None:
        # Rather than inventing categories at runtime from open-ended OSM tags.
        assert categorize({"man_made": "silo"}) is PoiCategory.OTHER
        assert categorize({}) is PoiCategory.OTHER

    def test_shop_wins_over_amenity_when_both_present(self) -> None:
        # A supermarket with an ATM is a supermarket.
        assert categorize({"shop": "supermarket", "amenity": "bank"}) is (
            PoiCategory.GROCERY
        )


class TestBuildQuery:
    def test_bbox_order_is_south_west_north_east(self) -> None:
        q = build_query(_bbox(), 90)
        assert "(34.06,-118.41,34.08,-118.39)" in q

    def test_requests_json_and_centers(self) -> None:
        q = build_query(_bbox(), 90)
        assert q.startswith("[out:json][timeout:90]")
        # `out center` is what gives ways a usable point.
        assert "out center tags;" in q


@respx.mock
class TestFetchPois:
    def test_parses_nodes_and_ways(self) -> None:
        respx.post(OVERPASS).mock(
            return_value=httpx.Response(
                200,
                json={
                    "elements": [
                        {
                            "type": "node",
                            "id": 1,
                            "lat": 34.07,
                            "lon": -118.40,
                            "tags": {"shop": "supermarket", "name": "Market"},
                        },
                        {
                            # Ways carry no lat/lon; `out center` supplies one.
                            "type": "way",
                            "id": 2,
                            "center": {"lat": 34.071, "lon": -118.401},
                            "tags": {"amenity": "restaurant", "name": "Cafe"},
                        },
                    ]
                },
            )
        )

        pois = OverpassPoiSource(_settings()).fetch_pois(_bbox())

        assert len(pois) == 2
        assert pois[0].source_id == "node/1"
        assert pois[0].category is PoiCategory.GROCERY
        assert pois[1].source_id == "way/2"
        assert pois[1].lat == 34.071
        assert pois[1].category is PoiCategory.FOOD_DRINK

    def test_skips_elements_without_coordinates(self) -> None:
        respx.post(OVERPASS).mock(
            return_value=httpx.Response(
                200,
                json={
                    "elements": [
                        {"type": "relation", "id": 3, "tags": {"shop": "mall"}},
                        {"type": "node", "id": 4, "lat": 34.07, "lon": -118.4,
                         "tags": {"shop": "clothes"}},
                    ]
                },
            )
        )

        pois = OverpassPoiSource(_settings()).fetch_pois(_bbox())

        assert [p.source_id for p in pois] == ["node/4"]

    def test_unnamed_poi_keeps_none_name(self) -> None:
        respx.post(OVERPASS).mock(
            return_value=httpx.Response(
                200,
                json={"elements": [{"type": "node", "id": 5, "lat": 34.07,
                                    "lon": -118.4, "tags": {"shop": "kiosk"}}]},
            )
        )
        pois = OverpassPoiSource(_settings()).fetch_pois(_bbox())
        assert pois[0].name is None


@respx.mock
class TestRetry:
    def test_retries_transient_406_then_succeeds(self) -> None:
        # 406 is undocumented but was observed from a loaded endpoint for a
        # query that succeeded moments later.
        route = respx.post(OVERPASS)
        route.side_effect = [
            httpx.Response(406, text="not acceptable"),
            httpx.Response(200, json={"elements": []}),
        ]
        respx.post(MIRROR).mock(return_value=httpx.Response(200, json={"elements": []}))

        calls: list[float] = []
        source = OverpassPoiSource(_settings(), sleep=calls.append)
        pois = source.fetch_pois(_bbox())

        assert pois == []
        assert calls, "expected a backoff sleep between attempts"

    def test_fails_over_to_mirror(self) -> None:
        respx.post(OVERPASS).mock(return_value=httpx.Response(504, text="busy"))
        respx.post(MIRROR).mock(
            return_value=httpx.Response(
                200,
                json={"elements": [{"type": "node", "id": 9, "lat": 34.07,
                                    "lon": -118.4, "tags": {"shop": "books"}}]},
            )
        )

        source = OverpassPoiSource(_settings(), sleep=lambda _: None)
        pois = source.fetch_pois(_bbox())

        assert [p.source_id for p in pois] == ["node/9"]

    def test_syntax_error_raises_immediately_without_retrying(self) -> None:
        # A 400 is our bug; retrying it just burns the budget.
        route = respx.post(OVERPASS).mock(
            return_value=httpx.Response(400, text="syntax error")
        )

        source = OverpassPoiSource(_settings(), sleep=lambda _: None)
        with pytest.raises(httpx.HTTPStatusError):
            source.fetch_pois(_bbox())

        assert route.call_count == 1

    def test_gives_up_after_max_retries(self) -> None:
        respx.post(OVERPASS).mock(return_value=httpx.Response(429, text="rate"))
        respx.post(MIRROR).mock(return_value=httpx.Response(429, text="rate"))

        source = OverpassPoiSource(_settings(), sleep=lambda _: None)
        with pytest.raises(RuntimeError, match="failed after"):
            source.fetch_pois(_bbox())
