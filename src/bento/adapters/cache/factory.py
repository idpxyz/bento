"""Cache Factory - Factory for creating cache instances.

This module provides a factory for creating cache instances based on configuration.
"""

from bento.application.ports.cache import Cache

from .config import CacheBackend, CacheConfig
from .memory import MemoryCache
from .redis import RedisCache


class CacheFactory:
    """Factory for creating cache instances.

    Creates cache instances based on configuration (Memory/Redis).

    Example:
        ```python
        from bento.adapters.cache import CacheFactory, CacheConfig

        # Create from config
        config = CacheConfig.from_env()
        cache = await CacheFactory.create(config)

        # Use cache
        await cache.set("key", "value")

        # Cleanup
        await cache.close()
        ```
    """

    @staticmethod
    async def create(config: CacheConfig) -> Cache:
        """Create and initialize cache instance.

        Args:
            config: Cache configuration

        Returns:
            Initialized cache instance (MemoryCache or RedisCache)

        Raises:
            ValueError: If backend type is invalid

        Example:
            ```python
            # Memory cache
            config = CacheConfig(backend=CacheBackend.MEMORY)
            cache = await CacheFactory.create(config)

            # Redis cache
            config = CacheConfig(
                backend=CacheBackend.REDIS,
                redis_url="redis://localhost:6379/0"
            )
            cache = await CacheFactory.create(config)
            ```
        """
        if config.backend == CacheBackend.MEMORY:
            cache = MemoryCache(config)
        elif config.backend == CacheBackend.REDIS:
            cache = RedisCache(config)
        else:
            raise ValueError(f"Unknown cache backend: {config.backend}")

        # Initialize cache
        await cache.initialize()

        return cache


async def create_cache(
    backend: str = "memory",
    prefix: str = "",
    ttl: int | None = None,
    redis_url: str | None = None,
) -> Cache:
    """Convenience function to create cache instance.

    Args:
        backend: Backend type ("memory" or "redis")
        prefix: Key prefix
        ttl: Default TTL in seconds
        redis_url: Redis URL (for redis backend)

    Returns:
        Initialized cache instance

    Example:
        ```python
        # Memory cache
        cache = await create_cache(backend="memory", prefix="myapp:", ttl=3600)

        # Redis cache
        cache = await create_cache(
            backend="redis",
            prefix="myapp:",
            ttl=3600,
            redis_url="redis://localhost:6379/0"
        )
        ```
    """
    backend_enum = CacheBackend.MEMORY if backend == "memory" else CacheBackend.REDIS

    config = CacheConfig(
        backend=backend_enum,
        prefix=prefix,
        ttl=ttl,
        redis_url=redis_url,
    )

    return await CacheFactory.create(config)
