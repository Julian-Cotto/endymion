from __future__ import annotations


from azure.identity import DefaultAzureCredential

from app.services.cache import CacheBackend


class AppConfigFlagService:
    def __init__(
        self,
        endpoint: str,
        label: str,
        cache: CacheBackend,
        cache_ttl_seconds: int = 30,
    ):
        self.endpoint = endpoint
        self.label = label
        self.cache = cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self.credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)

    async def resolve_flags(self, keys: list[str]) -> dict[str, bool]:
    # LOCAL DEV OVERRIDE
    # Enable everything unless explicitly disabled

        return {key: True for key in keys}