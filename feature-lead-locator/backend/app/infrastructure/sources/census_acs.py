"""Census demographics: ACS values + TIGER tract geometry.

Two services, because neither gives both:

  * ACS API  -> values, no shapes. REQUIRES an API key (verified: every
    request without one 302s to /data/missing_key.html, including the
    simplest state-level query — the old keyless allowance is gone).
    Free and instant at https://api.census.gov/data/key_signup.html.
  * TIGERweb -> shapes, no values. Keyless.

The split matters for degradation: without a key the product still works —
areas resolve, POIs load, traffic scores — it just loses the demand term.
So a missing key is surfaced explicitly rather than silently zeroing demand,
which would quietly rank rich and poor tracts identically.
"""

from __future__ import annotations

import logging

import httpx

from .base import TractDemographics
from .config import SourceSettings, get_source_settings

logger = logging.getLogger(__name__)

# ACS variables. Chosen to feed the demand term:
#   B01003_001E - total population
#   B19013_001E - median household income
#   B11001_001E - total households
ACS_VARIABLES = {
    "population": "B01003_001E",
    "median_household_income": "B19013_001E",
    "households": "B11001_001E",
}

# ACS encodes "no data" as large negative jam values rather than null
# (-666666666 = suppressed for small samples, -999999999 = not applicable...).
# Treating these as real numbers would make suppressed tracts look like they
# have negative half-billion incomes and poison any normalization.
ACS_JAM_THRESHOLD = -1_000_000

TIGERWEB_TRACTS_LAYER = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
    "/tigerWMS_Current/MapServer/8"
)


class MissingCensusKeyError(RuntimeError):
    """Raised when ACS is called without an API key.

    Explicit rather than degrading silently: the demand term would otherwise
    vanish from every score with no signal to the operator.
    """

    def __init__(self) -> None:
        super().__init__(
            "The Census ACS API requires an API key (requests without one are "
            "redirected to missing_key.html). Get a free one instantly at "
            "https://api.census.gov/data/key_signup.html and set CENSUS_API_KEY. "
            "Without it, searches still run but have no demographics term."
        )


def _parse_acs_value(raw: object) -> int | None:
    if raw is None:
        return None
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return None
    return None if value <= ACS_JAM_THRESHOLD else value


class CensusAcsSource:
    """ACS 5-year estimates at tract level."""

    def __init__(
        self,
        settings: SourceSettings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or get_source_settings()
        self._client = client

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._settings.http_timeout_seconds,
                headers={"User-Agent": self._settings.geocoder_user_agent},
                # The missing-key response is a 302 to an HTML page; without
                # following it we would only see an opaque redirect.
                follow_redirects=True,
            )
        return self._client

    @property
    def has_key(self) -> bool:
        return bool(self._settings.census_api_key)

    def fetch_tracts(
        self, state_fips: str, county_fips: str
    ) -> list[TractDemographics]:
        if not self.has_key:
            raise MissingCensusKeyError()

        variables = ",".join(ACS_VARIABLES.values())
        url = (
            f"{self._settings.census_base_url}/{self._settings.census_acs_year}"
            f"/{self._settings.census_acs_dataset}"
        )
        resp = self._http().get(
            url,
            params={
                "get": f"NAME,{variables}",
                "for": "tract:*",
                "in": f"state:{state_fips} county:{county_fips}",
                "key": self._settings.census_api_key,
            },
        )

        # A bad/absent key lands on an HTML page with a 200 after the redirect,
        # so status alone does not tell us it failed.
        if "missing_key" in str(resp.url) or "html" in (
            resp.headers.get("content-type") or ""
        ):
            raise MissingCensusKeyError()
        resp.raise_for_status()

        rows = resp.json()
        header, records = rows[0], rows[1:]
        idx = {name: header.index(code) for name, code in ACS_VARIABLES.items()}
        i_state, i_county, i_tract = (
            header.index("state"),
            header.index("county"),
            header.index("tract"),
        )

        out: list[TractDemographics] = []
        for row in records:
            geoid = f"{row[i_state]}{row[i_county]}{row[i_tract]}"
            out.append(
                TractDemographics(
                    geoid=geoid,
                    population=_parse_acs_value(row[idx["population"]]),
                    median_household_income=_parse_acs_value(
                        row[idx["median_household_income"]]
                    ),
                    households=_parse_acs_value(row[idx["households"]]),
                    acs_year=self._settings.census_acs_year,
                )
            )
        return out


class TigerTractGeometrySource:
    """Tract polygons + land area from TIGERweb. No key required."""

    def __init__(
        self,
        settings: SourceSettings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or get_source_settings()
        self._client = client

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._settings.http_timeout_seconds,
                headers={"User-Agent": self._settings.geocoder_user_agent},
            )
        return self._client

    def fetch_geometries(
        self, state_fips: str, county_fips: str
    ) -> dict[str, dict]:
        """-> {geoid: {"rings": [[(lat, lon), ...]], "area_land_sq_m": int}}

        Paginated: layer 8 advertises maxRecordCount=100000 and a big county is
        ~2.5k tracts, so one page suffices today — but relying on that silently
        truncates if the limit ever drops, hence the explicit loop.
        """
        out: dict[str, dict] = {}
        offset = 0
        page_size = 1000

        while True:
            resp = self._http().get(
                f"{TIGERWEB_TRACTS_LAYER}/query",
                params={
                    "where": f"STATE='{state_fips}' AND COUNTY='{county_fips}'",
                    "outFields": "GEOID,AREALAND",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "resultOffset": str(offset),
                    "resultRecordCount": str(page_size),
                    "f": "json",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            if "error" in payload:
                raise httpx.HTTPError(f"TIGERweb error: {payload['error']}")

            features = payload.get("features", [])
            for feature in features:
                attrs = feature["attributes"]
                geometry = feature.get("geometry") or {}
                rings = geometry.get("rings")
                if not rings:
                    continue
                area = attrs.get("AREALAND")
                out[attrs["GEOID"]] = {
                    # Esri gives [lon, lat]; our contract is (lat, lon).
                    "rings": [[(pt[1], pt[0]) for pt in ring] for ring in rings],
                    "area_land_sq_m": int(area) if area not in (None, "") else None,
                }

            if not payload.get("exceededTransferLimit") and len(features) < page_size:
                break
            offset += page_size

        return out


def build_demographics_source(
    settings: SourceSettings | None = None,
) -> CensusAcsSource:
    return CensusAcsSource(settings or get_source_settings())


def build_tract_geometry_source(
    settings: SourceSettings | None = None,
) -> TigerTractGeometrySource:
    return TigerTractGeometrySource(settings or get_source_settings())
