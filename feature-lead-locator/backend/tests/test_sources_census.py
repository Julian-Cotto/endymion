"""Census ACS / TIGER adapter tests."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.infrastructure.sources.census_acs import (
    CensusAcsSource,
    MissingCensusKeyError,
    TigerTractGeometrySource,
    _parse_acs_value,
)
from app.infrastructure.sources.config import SourceSettings

CENSUS = "https://api.census.gov/data"
TIGER = "https://tigerweb.geo.census.gov"


class TestParseAcsValue:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("54321", 54321),
            ("0", 0),  # a real zero must survive
            (12345, 12345),
            ("12345.0", 12345),
        ],
    )
    def test_real_values(self, raw: object, expected: int) -> None:
        assert _parse_acs_value(raw) == expected

    @pytest.mark.parametrize(
        "raw", ["-666666666", "-999999999", "-222222222", -666666666]
    )
    def test_jam_values_become_none(self, raw: object) -> None:
        # ACS encodes suppression as huge negatives, not null. Treating them as
        # numbers would give tracts negative half-billion incomes.
        assert _parse_acs_value(raw) is None

    @pytest.mark.parametrize("raw", [None, "", "N/A", "null"])
    def test_unparseable_becomes_none(self, raw: object) -> None:
        assert _parse_acs_value(raw) is None


class TestMissingKey:
    def test_raises_without_key_before_any_request(self) -> None:
        source = CensusAcsSource(SourceSettings(census_api_key=None))
        assert source.has_key is False
        with pytest.raises(MissingCensusKeyError) as excinfo:
            source.fetch_tracts("06", "037")
        # The message must tell the operator how to fix it.
        assert "key_signup" in str(excinfo.value)

    @respx.mock
    def test_raises_when_api_redirects_to_missing_key_page(self) -> None:
        # A bad key lands on an HTML page with a 200 after redirect, so status
        # alone does not reveal the failure.
        respx.get(url__startswith=CENSUS).mock(
            return_value=httpx.Response(
                200,
                html="<html>missing_key</html>",
                request=httpx.Request("GET", f"{CENSUS}/missing_key.html"),
            )
        )
        source = CensusAcsSource(SourceSettings(census_api_key="bogus"))
        with pytest.raises(MissingCensusKeyError):
            source.fetch_tracts("06", "037")


@respx.mock
class TestFetchTracts:
    def test_parses_rows_into_demographics(self) -> None:
        respx.get(url__startswith=CENSUS).mock(
            return_value=httpx.Response(
                200,
                json=[
                    ["NAME", "B01003_001E", "B19013_001E", "B11001_001E",
                     "state", "county", "tract"],
                    ["Tract 1", "4200", "95000", "1500", "06", "037", "700600"],
                    # Suppressed income in a real-population tract.
                    ["Tract 2", "3100", "-666666666", "1200", "06", "037", "700700"],
                ],
                headers={"content-type": "application/json"},
            )
        )

        tracts = CensusAcsSource(
            SourceSettings(census_api_key="k")
        ).fetch_tracts("06", "037")

        assert len(tracts) == 2
        assert tracts[0].geoid == "06037700600"  # state+county+tract concatenated
        assert tracts[0].population == 4200
        assert tracts[0].median_household_income == 95000
        assert tracts[1].median_household_income is None
        assert tracts[1].population == 3100

    def test_column_order_is_read_from_header_not_assumed(self) -> None:
        # The API is free to reorder; indexing positionally would silently
        # swap income and population.
        respx.get(url__startswith=CENSUS).mock(
            return_value=httpx.Response(
                200,
                json=[
                    ["B19013_001E", "NAME", "B11001_001E", "B01003_001E",
                     "state", "county", "tract"],
                    ["95000", "Tract 1", "1500", "4200", "06", "037", "700600"],
                ],
                headers={"content-type": "application/json"},
            )
        )

        tracts = CensusAcsSource(
            SourceSettings(census_api_key="k")
        ).fetch_tracts("06", "037")

        assert tracts[0].population == 4200
        assert tracts[0].median_household_income == 95000
        assert tracts[0].households == 1500


@respx.mock
class TestTigerGeometry:
    def test_flips_esri_lon_lat_to_lat_lon(self) -> None:
        respx.get(url__startswith=TIGER).mock(
            return_value=httpx.Response(
                200,
                json={
                    "features": [
                        {
                            "attributes": {"GEOID": "11001002801",
                                           "AREALAND": "171910"},
                            "geometry": {"rings": [[[-77.03, 38.90], [-77.01, 38.90],
                                                    [-77.01, 38.92]]]},
                        }
                    ]
                },
            )
        )

        geoms = TigerTractGeometrySource(SourceSettings()).fetch_geometries(
            "11", "001"
        )

        assert "11001002801" in geoms
        assert geoms["11001002801"]["rings"][0][0] == (38.90, -77.03)
        assert geoms["11001002801"]["area_land_sq_m"] == 171910

    def test_skips_features_without_geometry(self) -> None:
        respx.get(url__startswith=TIGER).mock(
            return_value=httpx.Response(
                200,
                json={
                    "features": [
                        {"attributes": {"GEOID": "1", "AREALAND": "1"}},
                        {
                            "attributes": {"GEOID": "2", "AREALAND": "2"},
                            "geometry": {"rings": [[[-77.0, 38.9], [-77.0, 38.9]]]},
                        },
                    ]
                },
            )
        )

        geoms = TigerTractGeometrySource(SourceSettings()).fetch_geometries("11", "001")

        assert list(geoms) == ["2"]

    def test_missing_area_is_none_not_zero(self) -> None:
        # Zero land area would silently produce infinite density downstream.
        respx.get(url__startswith=TIGER).mock(
            return_value=httpx.Response(
                200,
                json={
                    "features": [
                        {
                            "attributes": {"GEOID": "3", "AREALAND": ""},
                            "geometry": {"rings": [[[-77.0, 38.9], [-77.0, 38.9]]]},
                        }
                    ]
                },
            )
        )

        geoms = TigerTractGeometrySource(SourceSettings()).fetch_geometries("11", "001")

        assert geoms["3"]["area_land_sq_m"] is None

    def test_surfaces_tigerweb_error_payload(self) -> None:
        # TIGERweb returns errors as a 200 with an "error" key.
        respx.get(url__startswith=TIGER).mock(
            return_value=httpx.Response(
                200, json={"error": {"code": 400, "message": "Failed to execute query."}}
            )
        )

        with pytest.raises(httpx.HTTPError, match="TIGERweb error"):
            TigerTractGeometrySource(SourceSettings()).fetch_geometries("11", "001")
