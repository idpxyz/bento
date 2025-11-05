"""Cache Port - Application layer contract for caching.

This module defines the Cache protocol for caching data to improve performance.

Caching helps reduce:
1. Database query load
2. External API calls
3. Expensive computations
"""

from typing import Any, Optional, Protocol


class Cache(Protocol):
    """Cache protocol - defines the contract for caching operations.
    
    This protocol abstracts caching mechanisms, allowing the application
    layer to cache data without depending on specific cache implementations
    (Redis, Memcached, in-memory, etc.).
    
    This is a Protocol (not ABC), enabling structural subtyping.
    
    Example:
        ```python
        # Application layer uses the protocol
        class UserService:
            def __init__(self, cache: Cache, repo: Repository):
                self.cache = cache
                self.repo = repo
            
            async def get_user(self, user_id: str) -> User:
                # Try cache first
                cached = await self.cache.get(f"user:{user_id}")
                if cached:
                    return User.from_dict(cached)
                
                # Load from database
                user = await self.repo.find_by_id(user_id)
                if user:
                    await self.cache.set(
                        f"user:{user_id}",
                        user.to_dict(),
                        ttl=3600
                    )
                return user
        
        # Infrastructure provides implementation
        class RedisCache:
            async def get(self, key: str) -> Optional[Any]:
                # Redis-specific implementation
                ...
        ```
    """

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache by key.
        
        Args:
            key: The cache key to look up
            
        Returns:
            The cached value if found and not expired, None otherwise
            
        Example:
            ```python
            value = await cache.get("user:123")
            if value:
                print(f"Cache hit: {value}")
            else:
                print("Cache miss")
            ```
        """
        ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Set a value in cache with optional TTL.
        
        Args:
            key: The cache key
            value: The value to cache (must be serializable)
            ttl: Time-to-live in seconds (None = no expiration)
            
        Example:
            ```python
            await cache.set("user:123", user_data, ttl=3600)  # 1 hour
            ```
        """
        ...

    async def delete(self, key: str) -> None:
        """Delete a value from cache.
        
        Args:
            key: The cache key to delete
            
        Note:
            Deleting a non-existent key should not raise an error.
            
        Example:
            ```python
            await cache.delete("user:123")
            ```
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache.
        
        Args:
            key: The cache key to check
            
        Returns:
            True if key exists and not expired, False otherwise
            
        Example:
            ```python
            if await cache.exists("user:123"):
                print("Key exists")
            ```
        """
        ...

    async def clear(self) -> None:
        """Clear all cached values.
        
        Warning:
            This operation may affect other services if using a shared cache.
            Use with caution in production environments.
            
        Example:
            ```python
            await cache.clear()  # Usually for testing
            ```
        """
        ...

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from cache at once.
        
        Args:
            keys: List of cache keys to look up
            
        Returns:
            Dictionary mapping keys to values (missing keys are omitted)
            
        Example:
            ```python
            result = await cache.get_many(["user:1", "user:2", "user:3"])
            # {"user:1": {...}, "user:3": {...}}  # user:2 was missing
            ```
        """
        ...

    async def set_many(
        self,
        items: dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Set multiple values in cache at once.
        
        Args:
            items: Dictionary mapping keys to values
            ttl: Time-to-live in seconds (applied to all items)
            
        Example:
            ```python
            await cache.set_many({
                "user:1": user1_data,
                "user:2": user2_data,
            }, ttl=3600)
            ```
        """
        ...

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "user:*")
            
        Returns:
            Number of keys deleted
            
        Note:
            Pattern syntax depends on cache implementation.
            For Redis, uses SCAN + DEL pattern.
            
        Example:
            ```python
            deleted = await cache.delete_pattern("user:*")
            print(f"Deleted {deleted} keys")
            ```
        """
        ...

