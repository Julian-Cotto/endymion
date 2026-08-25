"""Settings for the external data sources.

Deliberately a separate Settings class from ``app.config``: that module is
scaffold-managed (`replace` mode in scaffold.metadata.json), so anything added
there is lost on the next `scaffold apply --upgrade`. This file is unmanaged.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Geocoding (zip/city -> area). TIGERweb, not Nominatim: Nominatim 403s
    # this client and its policy caps automated traffic, whereas TIGERweb is
    # keyless, US-authoritative, and returns real polygons. See geocoder.py.
    # ------------------------------------------------------------------
    geocoder_provider: str = "tigerweb"
    geocoder_user_agent: str = "endymion-lead-locator/0.1 (dev@example.local)"

    # ------------------------------------------------------------------
    # POIs (Overpass / OpenStreetMap)
    # ------------------------------------------------------------------
    poi_provider: str = "overpass"
    overpass_base_url: str = "https://overpass-api.de/api/interpreter"
    # Independent mirrors of the same API, tried in turn when the primary is
    # loaded. Not redundancy theatre: the main endpoint was observed rejecting
    # a valid query (406, then 504) within seconds during development.
    overpass_mirror_urls: str = (
        "https://overpass.kumi.systems/api/interpreter,"
        "https://overpass.osm.jp/api/interpreter"
    )
    overpass_timeout_seconds: float = 90.0
    # Attempts are spread across primary + mirrors, so this wants to be at
    # least as large as the endpoint count to give each one a turn.
    overpass_max_retries: int = 4

    @property
    def overpass_mirror_urls_list(self) -> list[str]:
        return [u.strip() for u in self.overpass_mirror_urls.split(",") if u.strip()]

    # ------------------------------------------------------------------
    # Demographics (US Census ACS + TIGERweb geometry)
    # ------------------------------------------------------------------
    census_base_url: str = "https://api.census.gov/data"
    # ACS works keyless under ~500 requests/day, which is enough for local dev.
    # Set CENSUS_API_KEY to lift that.
    census_api_key: str | None = None
    census_acs_year: int = 2023
    census_acs_dataset: str = "acs/acs5"
    tigerweb_tracts_url: str = (
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/0"
    )

    # ------------------------------------------------------------------
    # Traffic model
    # ------------------------------------------------------------------
    # "modeled" = the free proxy (POI density + anchor pull + access).
    # A paid feed (Placer/SafeGraph) registers here later without touching
    # the scoring engine — see app/infrastructure/sources/traffic.py.
    traffic_provider: str = "modeled"

    # ------------------------------------------------------------------
    # Tiling
    # ------------------------------------------------------------------
    # res 8 ~= 0.74 km2 (city overview), res 9 ~= 0.11 km2 (block level).
    default_h3_resolution: int = 8
    # Guardrail: a whole-city bbox at res 9 can be >100k cells.
    max_cells_per_search: int = 20_000

    http_timeout_seconds: float = 30.0
    source_cache_ttl_hours: int = 24


@lru_cache
def get_source_settings() -> SourceSettings:
    return SourceSettings()
