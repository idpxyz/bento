"""Memory Cache - In-memory cache implementation.

This module provides an in-memory cache backend using OrderedDict.

Features:
- Fast access (O(1) for get/set)
- LRU eviction when max_size reached
- TTL support with automatic expiration
- Thread-safe with async lock
- JSON/Pickle serialization
"""

import asyncio
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from bento.adapters.cache.config import CacheConfig
from bento.adapters.cache.serializer import CacheSerializer
from bento.adapters.cache.stats import CacheStats


class MemoryCache:
    """In-memory cache implementation.

    Provides fast caching with LRU eviction and TTL support.

    Features:
    - OrderedDict-based storage (LRU ordering)
    - Automatic expiration cleanup
    - Configurable max size
    - JSON/Pickle serialization

    Example:
        ```python
        from bento.adapters.cache import MemoryCache, CacheConfig

        # Create cache
        config = CacheConfig(max_size=1000, ttl=3600)
        cache = MemoryCache(config)

        # Use cache
        await cache.set("user:123", {"name": "John"}, ttl=600)
        user = await cache.get("user:123")

        # Cleanup
        await cache.close()
        ```
    """

    def __init__(self, config: CacheConfig) -> None:
        """Initialize memory cache.

        Args:
            config: Cache configuration
        """
        self.config = config
        self._cache: OrderedDict[str, tuple[bytes, float | None]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None

        # Statistics
        self._stats = CacheStats() if config.enable_stats else None

        # Cache breakdown protection (prevent cache stampede)
        self._loading_locks: dict[str, asyncio.Lock] = (
            {} if config.enable_breakdown_protection else {}
        )

    async def initialize(self) -> None:
        """Initialize cache and start cleanup task.

        Starts background task for periodic expiration cleanup.
        """
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise

        Example:
            ```python
            value = await cache.get("user:123")
            if value:
                print(f"Cache hit: {value}")
            ```
        """
        start_time = time.time() if self._stats else None

        try:
            async with self._lock:
                prefixed_key = self.config.get_prefixed_key(key)

                if prefixed_key not in self._cache:
                    if self._stats:
                        duration = time.time() - start_time if start_time else 0.0
                        self._stats.record_miss(duration)
                    return None

                serialized_value, expire_at = self._cache[prefixed_key]

                # Check expiration
                if expire_at and time.time() > expire_at:
                    del self._cache[prefixed_key]
                    if self._stats:
                        duration = time.time() - start_time if start_time else 0.0
                        self._stats.record_miss(duration)
                    return None

                # Move to end (LRU)
                self._cache.move_to_end(prefixed_key)

                # Deserialize
                value = self._deserialize(serialized_value)

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

        Example:
            ```python
            await cache.set("user:123", user_data, ttl=3600)
            ```
        """
        start_time = time.time() if self._stats else None

        try:
            async with self._lock:
                prefixed_key = self.config.get_prefixed_key(key)

                # Evict if at capacity
                if (
                    self.config.max_size
                    and prefixed_key not in self._cache
                    and len(self._cache) >= self.config.max_size
                ):
                    # Remove oldest (first) entry
                    self._cache.popitem(last=False)

                # Calculate expiration
                expire_at = None
                if ttl is not None:
                    expire_at = time.time() + ttl
                elif self.config.ttl is not None:
                    expire_at = time.time() + self.config.ttl

                # Serialize and store
                serialized_value = self._serialize(value)
                self._cache[prefixed_key] = (serialized_value, expire_at)

                # Move to end (most recent)
                self._cache.move_to_end(prefixed_key)

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

        Example:
            ```python
            await cache.delete("user:123")
            ```
        """
        async with self._lock:
            prefixed_key = self.config.get_prefixed_key(key)
            self._cache.pop(prefixed_key, None)

        if self._stats:
            self._stats.record_delete()

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists and not expired

        Example:
            ```python
            if await cache.exists("user:123"):
                print("Key exists")
            ```
        """
        async with self._lock:
            prefixed_key = self.config.get_prefixed_key(key)

            if prefixed_key not in self._cache:
                return False

            _, expire_at = self._cache[prefixed_key]

            # Check expiration
            if expire_at and time.time() > expire_at:
                del self._cache[prefixed_key]
                return False

            return True

    async def clear(self) -> None:
        """Clear all cached values.

        Example:
            ```python
            await cache.clear()
            ```
        """
        async with self._lock:
            self._cache.clear()

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values at once.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary mapping keys to values (missing keys omitted)

        Example:
            ```python
            result = await cache.get_many(["user:1", "user:2", "user:3"])
            # {"user:1": {...}, "user:3": {...}}
            ```
        """
        result: dict[str, Any] = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Set multiple values at once.

        Args:
            items: Dictionary mapping keys to values
            ttl: Time-to-live for all items

        Example:
            ```python
            await cache.set_many({
                "user:1": user1_data,
                "user:2": user2_data,
            }, ttl=3600)
            ```
        """
        for key, value in items.items():
            await self.set(key, value, ttl=ttl)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            Number of keys deleted

        Example:
            ```python
            deleted = await cache.delete_pattern("user:*")
            print(f"Deleted {deleted} keys")
            ```
        """
        async with self._lock:
            # Convert pattern to prefix match (simple implementation)
            pattern_prefix = pattern.replace("*", "")
            full_prefix = self.config.get_prefixed_key(pattern_prefix)

            keys_to_delete = [
                key for key in list(self._cache.keys()) if key.startswith(full_prefix)
            ]

            for key in keys_to_delete:
                del self._cache[key]

            return len(keys_to_delete)

    async def get_or_set(self, key: str, loader: Callable[[], Any], ttl: int | None = None) -> Any:
        """Get value from cache or load and cache it (防击�?.

        This method prevents cache breakdown/stampede by ensuring only one
        request loads the data when cache misses.

        Args:
            key: Cache key
            loader: Async function to load data if cache misses
            ttl: Time-to-live in seconds

        Returns:
            Cached or loaded value

        Example:
            ```python
            async def load_user(user_id):
                return await db.query(...).where(id=user_id).first()

            # Multiple concurrent requests for same key will only trigger
            # one database query (防击�?
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

        # Cache breakdown protection
        if self._loading_locks is not None:
            prefixed_key = self.config.get_prefixed_key(key)

            # Get or create lock for this key
            if prefixed_key not in self._loading_locks:
                self._loading_locks[prefixed_key] = asyncio.Lock()

            lock = self._loading_locks[prefixed_key]

            async with lock:
                # Double-check cache (another request might have loaded it)
                value = await self.get(key)
                if value is not None:
                    return value

                # Load data
                value = await loader()

                # Cache it
                if value is not None:
                    await self.set(key, value, ttl=ttl)

                # Clean up lock
                if prefixed_key in self._loading_locks:
                    del self._loading_locks[prefixed_key]

                return value
        else:
            # No breakdown protection, load directly
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
                print(f"Total operations: {stats['total_operations']}")
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
        """Close cache and stop cleanup task.

        Example:
            ```python
            await cache.close()
            ```
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        await self.clear()

    # ==================== Internal Methods ====================

    def _serialize(self, value: Any) -> bytes:
        """Serialize value to bytes using unified serializer.

        Args:
            value: Value to serialize

        Returns:
            Serialized bytes
        """
        return CacheSerializer.serialize(value, self.config.serializer)

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to value using unified serializer.

        Args:
            data: Serialized bytes

        Returns:
            Deserialized value
        """
        return CacheSerializer.deserialize(data, self.config.serializer)

    async def _cleanup_loop(self) -> None:
        """Background task to remove expired entries.

        Runs every 60 seconds to clean up expired cache entries.
        """
        while True:
            try:
                await asyncio.sleep(60)  # Clean up every minute

                async with self._lock:
                    current_time = time.time()
                    expired_keys = [
                        key
                        for key, (_, expire_at) in self._cache.items()
                        if expire_at and current_time > expire_at
                    ]

                    for key in expired_keys:
                        del self._cache[key]

            except asyncio.CancelledError:
                break
            except Exception:
                # Avoid crashing the cleanup task
                await asyncio.sleep(5)
