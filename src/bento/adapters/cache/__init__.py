"""Cache Adapters - Cache implementation package.

This package provides cache adapters for the Cache port.

Available Backends:
- MemoryCache: In-memory cache (fast, not distributed)
- RedisCache: Redis-based cache (distributed, persistent)

Components:
- CacheConfig: Configuration for cache backends
- CacheFactory: Factory for creating cache instances
- create_cache: Convenience function

Example:
    ```python
    from bento.adapters.cache import create_cache

    # Create memory cache
    cache = await create_cache(backend="memory", prefix="myapp:", ttl=3600)

    # Create Redis cache
    cache = await create_cache(
        backend="redis",
        prefix="myapp:",
        ttl=3600,
        redis_url="redis://localhost:6379/0"
    )

    # Use cache
    await cache.set("key", "value")
    value = await cache.get("key")

    # Cleanup
    await cache.close()
    ```
"""

from bento.adapters.cache.config import CacheBackend, CacheConfig, SerializerType
from bento.adapters.cache.factory import CacheFactory, create_cache
from bento.adapters.cache.memory import MemoryCache
from bento.adapters.cache.redis import RedisCache
from bento.adapters.cache.stats import CacheStats

__all__ = [
    "CacheBackend",
    "CacheConfig",
    "SerializerType",
    "MemoryCache",
    "RedisCache",
    "CacheFactory",
    "create_cache",
    "CacheStats",
]
