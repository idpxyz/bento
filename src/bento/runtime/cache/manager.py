"""Cache manager for Bento Runtime."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages cache lifecycle and configuration.

    Integrates with bento.adapters.cache for MemoryCache and RedisCache support.
    Gracefully handles missing dependencies and provides fallback options.
    """

    def __init__(self, runtime: "BentoRuntime") -> None:
        """Initialize cache manager.

        Args:
            runtime: BentoRuntime instance
        """
        self.runtime = runtime

    def setup(self) -> None:
        """Setup cache from configuration.

        Supports both in-memory and Redis caches via bento.adapters.cache.
        Gracefully falls back to in-memory cache if Redis dependencies are missing.
        """
        # Cache configuration is optional
        cache_config = getattr(self.runtime.config, "cache", None)
        if not cache_config:
            logger.info("No cache configured, skipping")
            return

        try:
            # Try to import cache components
            try:
                from bento.adapters.cache.config import CacheBackend, CacheConfig

                has_cache_adapters = True
            except ImportError as e:
                logger.warning(f"bento.adapters.cache not fully available: {e}")
                has_cache_adapters = False

            if not has_cache_adapters:
                logger.warning("Continuing without cache")
                return

            # Parse configuration
            if isinstance(cache_config, dict):
                backend = cache_config.get("backend", "memory")
                config = CacheConfig(
                    backend=CacheBackend(backend),
                    prefix=cache_config.get("prefix", ""),
                    ttl=cache_config.get("ttl"),
                    max_size=cache_config.get("max_size", 10000),
                    redis_url=cache_config.get("redis_url"),
                )
            else:
                # Assume it's already a CacheConfig object
                config = cache_config

            # Create cache instance based on backend
            cache = self._create_cache(config)
            if cache:
                self.runtime.container.set("cache", cache)

        except Exception as e:
            logger.error(f"Failed to setup cache: {e}")
            logger.warning("Continuing without cache")

    def _create_cache(self, config: Any) -> Any:
        """Create cache instance based on configuration.

        Args:
            config: CacheConfig object

        Returns:
            Cache instance or None if creation fails
        """
        try:
            from bento.adapters.cache.config import CacheBackend
            from bento.adapters.cache.memory import MemoryCache

            if config.backend == CacheBackend.MEMORY:
                cache = MemoryCache(config)
                logger.info(
                    f"Cache configured: MemoryCache "
                    f"(prefix={config.prefix}, ttl={config.ttl}, max_size={config.max_size})"
                )
                return cache

            elif config.backend == CacheBackend.REDIS:
                if not config.redis_url:
                    raise ValueError("Redis cache requires redis_url configuration")

                try:
                    from bento.adapters.cache.redis import RedisCache

                    cache = RedisCache(config)
                    logger.info(
                        f"Cache configured: RedisCache "
                        f"(url={config.redis_url}, prefix={config.prefix}, ttl={config.ttl})"
                    )
                    return cache
                except ImportError:
                    logger.warning("Redis dependencies not available, falling back to MemoryCache")
                    # Fallback to memory cache
                    cache = MemoryCache(config)
                    logger.info("Using MemoryCache as fallback")
                    return cache

            else:
                raise ValueError(f"Unknown cache backend: {config.backend}")

        except Exception as e:
            logger.error(f"Failed to create cache: {e}")
            return None

    async def cleanup(self) -> None:
        """Cleanup cache connections."""
        try:
            cache = self.runtime.container.get("cache")
            if hasattr(cache, "close"):
                await cache.close()
                logger.info("Cache closed")
        except KeyError:
            pass  # No cache configured
