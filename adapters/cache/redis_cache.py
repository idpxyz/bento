from __future__ import annotations

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore


class RedisCache:
    def __init__(self, url: str = "redis://localhost:6379/0"):
        assert redis is not None, "redis-py not installed"
        self.client = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        await self.client.set(key, value, ex=ex)
