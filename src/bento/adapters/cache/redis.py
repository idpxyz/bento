"""Redis Cache - Redis-based distributed cache implementation.

This module provides a Redis cache backend for distributed caching.

Features:
- Distributed caching across multiple services
- Persistence and replication support
- High performance
- Pattern-based key deletion (SCAN)
- JSON/Pickle serialization
"""

import asyncio
import json
import pickle
import time
from collections.abc import Callable
from typing import Any

from redis.asyncio import Redis

from bento.adapters.cache.config import CacheConfig, SerializerType
from bento.adapters.cache.stats import CacheStats


class RedisCache:
    """Redis-based distributed cache implementation.

    Provides distributed caching with Redis backend.

    Features:
    - Distributed storage (shared across services)
    - Persistence support
    - High performance
    - Batch operations
    - Pattern matching

    Example:
        ```python
        from bento.adapters.cache import RedisCache, CacheConfig

        # Create cache
        config = CacheConfig(
            redis_url="redis://localhost:6379/0",
            prefix="myapp:",
            ttl=3600
        )
        cache = RedisCache(config)

        # Initialize connection
        await cache.initialize()

        # Use cache
        await cache.set("user:123", {"name": "John"})
        user = await cache.get("user:123")

        # Cleanup
        await cache.close()
        ```
    """

    def __init__(self, config: CacheConfig) -> None:
        """Initialize Redis cache.

        Args:
            config: Cache configuration (must include redis_url)

        Raises:
            ValueError: If redis_url is not provided
        """
        if not config.redis_url:
            raise ValueError("redis_url is required for RedisCache")

        self.config = config
        self._client: Redis | None = None

        # Statistics
        self._stats = CacheStats() if config.enable_stats else None

    async def initialize(self) -> None:
        """Initialize Redis connection.

        Raises:
            RuntimeError: If connection fails
        """
        try:
            self._client = Redis.from_url(
                self.config.redis_url,  # type: ignore
                encoding="utf-8",
                decode_responses=False,  # We use custom serialization
            )

            # Test connection
            await self._client.ping()

        except Exception as e:
            self._client = None
            raise RuntimeError(f"Failed to connect to Redis: {e}") from e

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise

        Raises:
            RuntimeError: If Redis client not initialized

        Example:
            ```python
            value = await cache.get("user:123")
            ```
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")

        start_time = time.time() if self._stats else None

        try:
            prefixed_key = self.config.get_prefixed_key(key)
            data = await self._client.get(prefixed_key)

            if data is None:
                if self._stats:
                    duration = time.time() - start_time if start_time else 0.0
                    self._stats.record_miss(duration)
                return None

            value = self._deserialize(data)

            if self._stats:
                duration = time.time() - start_time if start_time else 0.0
                self._stats.record_hit(duration)

            return value

        except Exception:
            if self._stats:
                self._stats.record_error()
            raise

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (overrides default)

        Raises:
            RuntimeError: If Redis client not initialized

        Example:
            ```python
            await cache.set("user:123", user_data, ttl=3600)
            ```
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")

        start_time = time.time() if self._stats else None

        try:
            prefixed_key = self.config.get_prefixed_key(key)
            serialized_data = self._serialize(value)

            # Use ttl if provided, otherwise use default
            expire_time = ttl if ttl is not None else self.config.ttl

            if expire_time:
                await self._client.setex(prefixed_key, expire_time, serialized_data)
            else:
                await self._client.set(prefixed_key, serialized_data)

            if self._stats:
                duration = time.time() - start_time if start_time else 0.0
                self._stats.record_set(duration)

        except Exception:
            if self._stats:
                self._stats.record_error()
            raise

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key to delete

        Raises:
            RuntimeError: If Redis client not initialized

        Example:
            ```python
            await cache.delete("user:123")
            ```
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")

        prefixed_key = self.config.get_prefixed_key(key)
        await self._client.delete(prefixed_key)

        if self._stats:
            self._stats.record_delete()

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists

        Raises:
            RuntimeError: If Redis client not initialized

        Example:
            ```python
            if await cache.exists("user:123"):
                print("Key exists")
            ```
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")

        prefixed_key = self.config.get_prefixed_key(key)
        return await self._client.exists(prefixed_key) > 0

    async def clear(self) -> None:
        """Clear all cached values with prefix.

        Warning:
            Only clears keys matching the configured prefix.

        Raises:
            RuntimeError: If Redis client not initialized

        Example:
            ```python
            await cache.clear()  # Clears all "myapp:*" keys
            ```
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")

        # Clear all keys matching prefix
        if self.config.prefix:
            await self.delete_pattern("*")

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values at once.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary mapping keys to values

        Raises:
            RuntimeError: If Redis client not initialized

        Example:
            ```python
            result = await cache.get_many(["user:1", "user:2"])
            # {"user:1": {...}, "user:2": {...}}
            ```
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")

        if not keys:
            return {}

        # Add prefix to all keys
        prefixed_keys = [self.config.get_prefixed_key(key) for key in keys]

        # Batch get
        values = await self._client.mget(prefixed_keys)

        # Build result dictionary
        result: dict[str, Any] = {}
        for original_key, value in zip(keys, values, strict=False):
            if value is not None:
                result[original_key] = self._deserialize(value)

        return result

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Set multiple values at once.

        Args:
            items: Dictionary mapping keys to values
            ttl: Time-to-live for all items

        Raises:
            RuntimeError: If Redis client not initialized

        Example:
            ```python
            await cache.set_many({
                "user:1": user1_data,
                "user:2": user2_data,
            }, ttl=3600)
            ```
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")

        if not items:
            return

        # Use pipeline for efficiency
        async with self._client.pipeline(transaction=True) as pipe:
            for key, value in items.items():
                prefixed_key = self.config.get_prefixed_key(key)
                serialized_data = self._serialize(value)

                expire_time = ttl if ttl is not None else self.config.ttl

                if expire_time:
                    await pipe.setex(prefixed_key, expire_time, serialized_data)
                else:
                    await pipe.set(prefixed_key, serialized_data)

            await pipe.execute()

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Uses SCAN for safe iteration (doesn't block Redis).

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            Number of keys deleted

        Raises:
            RuntimeError: If Redis client not initialized

        Example:
            ```python
            deleted = await cache.delete_pattern("user:*")
            print(f"Deleted {deleted} keys")
            ```
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")

        # Build full pattern with prefix
        full_pattern = self.config.get_prefixed_key(pattern)

        # Use SCAN for safe iteration
        matching_keys: set[str] = set()
        cursor = b"0"
        max_iterations = 100

        for _ in range(max_iterations):
            cursor, keys = await self._client.scan(
                cursor=int(cursor), match=full_pattern, count=100
            )

            if keys:
                # Decode bytes to strings
                for key in keys:
                    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                    matching_keys.add(key_str)

            if cursor == b"0":
                break

        # Delete matching keys in batches
        if matching_keys:
            batch_size = 100
            keys_list = list(matching_keys)

            for i in range(0, len(keys_list), batch_size):
                batch = keys_list[i : i + batch_size]
                await self._client.delete(*batch)

        return len(matching_keys)

    async def get_or_set(
        self, key: str, loader: Callable[[], Any], ttl: int | None = None, lock_timeout: int = 10
    ) -> Any:
        """Get value from cache or load and cache it (防击�?with distributed lock).

        This method prevents cache breakdown/stampede in distributed systems
        by using Redis distributed locks (SETNX).

        Args:
            key: Cache key
            loader: Async function to load data if cache misses
            ttl: Time-to-live in seconds
            lock_timeout: Lock timeout in seconds (防止死锁)

        Returns:
            Cached or loaded value

        Example:
            ```python
            async def load_user(user_id):
                return await db.query(...).where(id=user_id).first()

            # Multiple services requesting same key will only trigger
            # one database query (分布式防击穿)
            user = await cache.get_or_set(
                f"user:{user_id}",
                lambda: load_user(user_id),
                ttl=3600
            )
            ```
        """
        # Try cache first
        value = await self.get(key)
        if value is not None:
            return value

        # Cache breakdown protection with distributed lock
        if not self.config.enable_breakdown_protection:
            # No protection, load directly
            value = await loader()
            if value is not None:
                await self.set(key, value, ttl=ttl)
            return value

        if not self._client:
            raise RuntimeError("Redis client not initialized")

        # Use Redis SETNX for distributed lock
        prefixed_key = self.config.get_prefixed_key(key)
        lock_key = f"{prefixed_key}:lock"

        # Try to acquire lock
        acquired = await self._client.set(lock_key, "1", nx=True, ex=lock_timeout)

        if acquired:
            try:
                # Double-check cache
                value = await self.get(key)
                if value is not None:
                    return value

                # Load data
                value = await loader()

                # Cache it
                if value is not None:
                    await self.set(key, value, ttl=ttl)

                return value
            finally:
                # Release lock
                await self._client.delete(lock_key)
        else:
            # Another process is loading, wait and retry
            for _ in range(lock_timeout * 10):  # Poll every 0.1s
                await asyncio.sleep(0.1)

                # Check if data is now cached
                value = await self.get(key)
                if value is not None:
                    return value

            # Timeout waiting for lock, load anyway (fallback)
            value = await loader()
            if value is not None:
                await self.set(key, value, ttl=ttl)
            return value

    def get_stats(self) -> dict[str, float | int] | None:
        """Get cache statistics.

        Returns:
            Statistics dictionary or None if stats disabled

        Example:
            ```python
            stats = cache.get_stats()
            if stats:
                print(f"Hit rate: {stats['hit_rate']:.2%}")
                print(f"Avg get time: {stats['avg_get_time']:.4f}s")
            ```
        """
        if self._stats:
            return self._stats.to_dict()
        return None

    def reset_stats(self) -> None:
        """Reset cache statistics.

        Example:
            ```python
            # Reset daily
            cache.reset_stats()
            ```
        """
        if self._stats:
            self._stats.reset()

    async def close(self) -> None:
        """Close Redis connection.

        Example:
            ```python
            await cache.close()
            ```
        """
        if self._client:
            await self._client.aclose()
            self._client = None

    # ==================== Internal Methods ====================

    def _serialize(self, value: Any) -> bytes:
        """Serialize value to bytes.

        Args:
            value: Value to serialize

        Returns:
            Serialized bytes

        Raises:
            ValueError: If serialization fails
        """
        try:
            if self.config.serializer == SerializerType.JSON:
                return json.dumps(value).encode("utf-8")
            else:  # PICKLE
                return pickle.dumps(value)
        except Exception as e:
            raise ValueError(f"Failed to serialize value: {e}") from e

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to value.

        Args:
            data: Serialized bytes

        Returns:
            Deserialized value

        Raises:
            ValueError: If deserialization fails
        """
        try:
            if self.config.serializer == SerializerType.JSON:
                return json.loads(data.decode("utf-8"))
            else:  # PICKLE
                return pickle.loads(data)
        except Exception as e:
            raise ValueError(f"Failed to deserialize value: {e}") from e
