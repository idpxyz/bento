"""Cache Configuration - Settings for cache backends.

This module provides configuration for cache implementations.
Supports both Memory and Redis backends.
"""

import os
from dataclasses import dataclass
from enum import Enum


class CacheBackend(str, Enum):
    """Cache backend types."""

    MEMORY = "memory"
    REDIS = "redis"


class SerializerType(str, Enum):
    """Serializer types for cache values."""

    JSON = "json"
    PICKLE = "pickle"


@dataclass
class CacheConfig:
    """Cache configuration.

    Provides settings for cache backends (Memory/Redis).

    Attributes:
        backend: Cache backend type (memory/redis)
        prefix: Key prefix for all cache entries
        ttl: Default time-to-live in seconds (None = no expiration)
        max_size: Maximum number of entries (Memory only, None = unlimited)
        redis_url: Redis connection URL (Redis only)
        serializer: Serialization format (json/pickle)
        enable_stats: Enable cache statistics (default: True)
        enable_breakdown_protection: Enable cache breakdown protection (default: True)

    Example:
        ```python
        from bento.adapters.cache import CacheConfig, CacheBackend

        # Memory cache
        config = CacheConfig(
            backend=CacheBackend.MEMORY,
            prefix="myapp:",
            ttl=3600,
            max_size=10000
        )

        # Redis cache
        config = CacheConfig(
            backend=CacheBackend.REDIS,
            prefix="myapp:",
            ttl=3600,
            redis_url="redis://localhost:6379/0"
        )

        # From environment
        config = CacheConfig.from_env()
        ```
    """

    backend: CacheBackend = CacheBackend.MEMORY
    prefix: str = ""
    ttl: int | None = None
    max_size: int | None = 10000
    redis_url: str | None = None
    serializer: SerializerType = SerializerType.JSON
    enable_stats: bool = True
    enable_breakdown_protection: bool = True

    @classmethod
    def from_env(cls, prefix: str = "") -> "CacheConfig":
        """Create configuration from environment variables.

        Environment Variables:
            CACHE_BACKEND: Backend type (memory/redis, default: memory)
            CACHE_PREFIX: Key prefix (default: "")
            CACHE_TTL: Default TTL in seconds
            CACHE_MAX_SIZE: Max entries for memory cache (default: 10000)
            REDIS_URL: Redis connection URL
            CACHE_SERIALIZER: Serializer type (json/pickle, default: json)

        Args:
            prefix: Override prefix (if provided, ignores CACHE_PREFIX)

        Returns:
            CacheConfig instance

        Example:
            ```python
            # With environment variables:
            # CACHE_BACKEND=redis
            # REDIS_URL=redis://localhost:6379/0
            # CACHE_TTL=3600

            config = CacheConfig.from_env(prefix="myapp:")
            ```
        """
        backend_str = os.getenv("CACHE_BACKEND", "memory").lower()
        backend = CacheBackend.MEMORY if backend_str == "memory" else CacheBackend.REDIS

        ttl_str = os.getenv("CACHE_TTL")
        ttl = int(ttl_str) if ttl_str else None

        max_size_str = os.getenv("CACHE_MAX_SIZE")
        max_size = int(max_size_str) if max_size_str else 10000

        serializer_str = os.getenv("CACHE_SERIALIZER", "json").lower()
        serializer = SerializerType.JSON if serializer_str == "json" else SerializerType.PICKLE

        enable_stats_str = os.getenv("CACHE_ENABLE_STATS", "true").lower()
        enable_stats = enable_stats_str in ("true", "1", "yes")

        enable_breakdown_str = os.getenv("CACHE_ENABLE_BREAKDOWN_PROTECTION", "true").lower()
        enable_breakdown_protection = enable_breakdown_str in ("true", "1", "yes")

        return cls(
            backend=backend,
            prefix=prefix or os.getenv("CACHE_PREFIX", ""),
            ttl=ttl,
            max_size=max_size,
            redis_url=os.getenv("REDIS_URL"),
            serializer=serializer,
            enable_stats=enable_stats,
            enable_breakdown_protection=enable_breakdown_protection,
        )

    def get_prefixed_key(self, key: str) -> str:
        """Get key with prefix applied.

        Args:
            key: Original cache key

        Returns:
            Prefixed key

        Example:
            ```python
            config = CacheConfig(prefix="myapp:")
            prefixed = config.get_prefixed_key("user:123")
            # Returns: "myapp:user:123"
            ```
        """
        return f"{self.prefix}{key}"
