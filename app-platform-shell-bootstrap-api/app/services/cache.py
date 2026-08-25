from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import orjson
import redis


class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        raise NotImplementedError

    async def get_or_set(self, key: str, ttl_seconds: int, factory):
        value = await self.get(key)
        if value is not None:
            return value
        value = await factory()
        await self.set(key, value, ttl_seconds)
        return value


class InMemoryCache(CacheBackend):
    def __init__(self):
        self._items: dict[str, tuple[float, Any]] = {}

    async def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.time() >= expires_at:
            self._items.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._items[key] = (time.time() + ttl_seconds, value)


class RedisCache(CacheBackend):
    def __init__(self, redis_url: str):
        self._client = redis.Redis.from_url(redis_url, decode_responses=False)

    async def get(self, key: str) -> Any | None:
        raw = self._client.get(key)
        if raw is None:
            return None
        return orjson.loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._client.set(key, orjson.dumps(value), ex=ttl_seconds)

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
