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

        def _parse_int(name: str, default: int | None = None) -> int | None:
            """Parse integer environment variable with helpful error message.

            Args:
                name: Environment variable name
                default: Default value if env is not set

            Returns:
                Parsed integer or default

            Raises:
                ValueError: If value is set but not a valid integer
            """

            raw = os.getenv(name)
            if raw is None or raw == "":
                return default
            try:
                return int(raw)
            except ValueError as e:
                raise ValueError(f"Invalid integer for {name}={raw!r}") from e

        def _parse_bool(name: str, default: bool = True) -> bool:
            """Parse boolean environment variable (true/false/1/0/yes/no)."""

            raw = os.getenv(name)
            if raw is None or raw == "":
                return default
            value = raw.lower()
            if value in ("true", "1", "yes"):
                return True
            if value in ("false", "0", "no"):
                return False
            msg = (
                "Invalid boolean for "
                f"{name}={raw!r}, expected one of 'true', 'false', '1', '0', 'yes', 'no'"
            )
            raise ValueError(msg)

        # Backend: strict validation to avoid silent fallbacks
        backend_raw = os.getenv("CACHE_BACKEND", "memory")
        backend_str = backend_raw.lower()
        if backend_str == "memory":
            backend = CacheBackend.MEMORY
        elif backend_str == "redis":
            backend = CacheBackend.REDIS
        else:
            raise ValueError(f"Invalid CACHE_BACKEND={backend_raw!r}, expected 'memory' or 'redis'")

        # TTL / max_size with contextual errors
        ttl = _parse_int("CACHE_TTL", default=None)
        max_size = _parse_int("CACHE_MAX_SIZE", default=10000)

        # Serializer: strict validation
        serializer_raw = os.getenv("CACHE_SERIALIZER", "json")
        serializer_str = serializer_raw.lower()
        if serializer_str == "json":
            serializer = SerializerType.JSON
        elif serializer_str == "pickle":
            serializer = SerializerType.PICKLE
        else:
            raise ValueError(
                f"Invalid CACHE_SERIALIZER={serializer_raw!r}, expected 'json' or 'pickle'"
            )

        # Booleans: accept common truthy/falsey representations
        enable_stats = _parse_bool("CACHE_ENABLE_STATS", default=True)
        enable_breakdown_protection = _parse_bool("CACHE_ENABLE_BREAKDOWN_PROTECTION", default=True)

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
