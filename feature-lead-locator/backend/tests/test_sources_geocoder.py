"""Geocoder tests. HTTP is mocked — TIGERweb must not gate CI."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.infrastructure.sources.base import AmbiguousQueryError, QueryKind
from app.infrastructure.sources.config import SourceSettings
from app.infrastructure.sources.geocoder import (
    TigerwebGeocoder,
    classify_query,
    parse_city_query,
)
from app.infrastructure.sources.states import resolve_state_fips

TIGER_HOST = "https://tigerweb.geo.census.gov"
GEOCODER_HOST = "https://geocoding.geo.census.gov"


def _settings() -> SourceSettings:
    return SourceSettings(census_api_key=None)


# A square around (34.07, -118.40). Esri order is [lon, lat].
_SQUARE = [[[-118.41, 34.06], [-118.39, 34.06], [-118.39, 34.08], [-118.41, 34.08]]]


def _fips_route() -> None:
    respx.get(url__startswith=f"{GEOCODER_HOST}/geocoder/geographies").mock(
        return_value=httpx.Response(
            200,
            json={
                "result": {
                    "geographies": {"Census Tracts": [{"STATE": "06", "COUNTY": "037"}]}
                }
            },
        )
    )


class TestQueryClassification:
    @pytest.mark.parametrize("q", ["90210", " 90210 ", "90210-1234"])
    def test_zip_forms(self, q: str) -> None:
        assert classify_query(q) is QueryKind.ZIP

    @pytest.mark.parametrize("q", ["Austin, TX", "Austin", "1234", "123456"])
    def test_non_zip_is_city(self, q: str) -> None:
        assert classify_query(q) is QueryKind.CITY


class TestCityParsing:
    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("Austin, TX", ("Austin", "48")),
            ("Austin TX", ("Austin", "48")),
            ("Austin, Texas", ("Austin", "48")),
            ("austin, tx", ("austin", "48")),
            # Multi-word cities must survive the state split.
            ("Beverly Hills, CA", ("Beverly Hills", "06")),
            ("New York, NY", ("New York", "36")),
        ],
    )
    def test_parses_state(self, query: str, expected: tuple[str, str]) -> None:
        assert parse_city_query(query) == expected

    def test_no_state_returns_none(self) -> None:
        assert parse_city_query("Austin") == ("Austin", None)

    def test_bare_city_with_two_words_is_not_mistaken_for_state(self) -> None:
        # "Hills" is not a state, so the whole string stays the city.
        assert parse_city_query("Beverly Hills") == ("Beverly Hills", None)


class TestStateResolution:
    @pytest.mark.parametrize(
        ("token", "fips"),
        [("TX", "48"), ("tx", "48"), ("Texas", "48"), ("texas", "48"), ("48", "48")],
    )
    def test_accepts_forms(self, token: str, fips: str) -> None:
        assert resolve_state_fips(token) == fips

    @pytest.mark.parametrize("token", ["XX", "", "  ", "Nowhere"])
    def test_rejects_unknown(self, token: str) -> None:
        assert resolve_state_fips(token) is None


@respx.mock
class TestResolveZip:
    def test_returns_area_with_boundary(self) -> None:
        respx.get(url__startswith=f"{TIGER_HOST}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "features": [
                        {
                            "attributes": {"ZCTA5": "90210", "GEOID": "90210",
                                           "NAME": "ZCTA5 90210"},
                            "geometry": {"rings": _SQUARE},
                        }
                    ]
                },
            )
        )
        _fips_route()

        area = TigerwebGeocoder(_settings()).resolve("90210")

        assert area is not None
        assert area.query_kind is QueryKind.ZIP
        assert area.state_fips == "06"
        assert area.county_fips == "037"
        # Esri [lon, lat] must be flipped to (lat, lon).
        assert area.boundary_rings[0][0] == (34.06, -118.41)
        assert area.bbox.min_lat == 34.06
        assert area.bbox.max_lon == -118.39

    def test_unknown_zip_returns_none(self) -> None:
        respx.get(url__startswith=TIGER_HOST).mock(
            return_value=httpx.Response(200, json={"features": []})
        )
        assert TigerwebGeocoder(_settings()).resolve("00000") is None

    def test_empty_query_returns_none_without_network(self) -> None:
        assert TigerwebGeocoder(_settings()).resolve("   ") is None


@respx.mock
class TestResolveCity:
    def test_ambiguous_city_raises_rather_than_guessing(self) -> None:
        # The real failure this guards: "Austin" exists in 5 states, and
        # silently picking one would prospect the wrong market.
        respx.get(url__startswith=TIGER_HOST).mock(
            return_value=httpx.Response(
                200,
                json={
                    "features": [
                        {"attributes": {"NAME": "Austin city", "STATE": "48",
                                        "GEOID": "4805000"}},
                        {"attributes": {"NAME": "Austin city", "STATE": "27",
                                        "GEOID": "2702908"}},
                    ]
                },
            )
        )

        with pytest.raises(AmbiguousQueryError) as excinfo:
            TigerwebGeocoder(_settings()).resolve("Austin")

        assert len(excinfo.value.candidates) == 2
        assert "TX" in str(excinfo.value)
        assert "MN" in str(excinfo.value)

    def test_single_match_resolves(self) -> None:
        route = respx.get(url__startswith=TIGER_HOST)
        route.side_effect = [
            # First pass: identity only, no geometry.
            httpx.Response(
                200,
                json={
                    "features": [
                        {"attributes": {"NAME": "Austin city", "STATE": "48",
                                        "GEOID": "4805000", "CENTLAT": "+30.2985",
                                        "CENTLON": "-097.7537"}}
                    ]
                },
            ),
            # Second pass: the same match, with geometry.
            httpx.Response(
                200,
                json={
                    "features": [
                        {
                            "attributes": {"NAME": "Austin city", "STATE": "48",
                                           "GEOID": "4805000", "CENTLAT": "+30.2985",
                                           "CENTLON": "-097.7537"},
                            "geometry": {"rings": _SQUARE},
                        }
                    ]
                },
            ),
        ]
        _fips_route()

        area = TigerwebGeocoder(_settings()).resolve("Austin, TX")

        assert area is not None
        assert area.state_fips == "48"
        assert area.center_lat == pytest.approx(30.2985)
        assert "TX" in area.display_name


@respx.mock
def test_fips_lookup_failure_degrades_instead_of_raising() -> None:
    # Demographics are a nice-to-have; losing FIPS must not fail the search.
    respx.get(url__startswith=TIGER_HOST).mock(
        return_value=httpx.Response(
            200,
            json={
                "features": [
                    {
                        "attributes": {"ZCTA5": "90210", "NAME": "ZCTA5 90210"},
                        "geometry": {"rings": _SQUARE},
                    }
                ]
            },
        )
    )
    respx.get(url__startswith=f"{GEOCODER_HOST}/geocoder/geographies").mock(
        return_value=httpx.Response(500, text="boom")
    )

    area = TigerwebGeocoder(_settings()).resolve("90210")

    assert area is not None
    assert area.state_fips is None
    assert area.county_fips is None
    assert area.boundary_rings is not None


def test_tiling_rings_falls_back_to_bbox() -> None:
    from app.infrastructure.sources.base import BoundingBox, ResolvedArea

    area = ResolvedArea(
        query_raw="x",
        query_kind=QueryKind.ZIP,
        display_name="x",
        bbox=BoundingBox(min_lat=0.0, max_lat=1.0, min_lon=0.0, max_lon=1.0),
        center_lat=0.5,
        center_lon=0.5,
        boundary_rings=None,
    )
    rings = area.tiling_rings()
    assert len(rings) == 1
    assert rings[0][0] == (0.0, 0.0)


def test_bbox_rejects_inverted_bounds() -> None:
    from app.infrastructure.sources.base import BoundingBox

    with pytest.raises(ValueError, match="min_lat"):
        BoundingBox(min_lat=1.0, max_lat=0.0, min_lon=0.0, max_lon=1.0)
