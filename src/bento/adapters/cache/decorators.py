"""Cache Decorators - Decorators for automatic caching.

This module provides decorators to easily add caching to functions.
"""

import functools
import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from bento.application.ports.cache import Cache

T = TypeVar("T")


def cached(
    cache: Cache,
    ttl: int | None = None,
    key_prefix: str = "",
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to cache function results.

    Automatically caches function results based on arguments.

    Args:
        cache: Cache instance to use
        ttl: Time-to-live in seconds (None = use cache default)
        key_prefix: Prefix for cache keys (default: function name)
        key_builder: Custom key builder function (default: hash args/kwargs)

    Returns:
        Decorated function with caching

    Example:
        ```python
        from bento.adapters.cache import create_cache, cached

        cache = await create_cache(backend="memory")

        @cached(cache, ttl=3600, key_prefix="user:")
        async def get_user(user_id: str) -> dict:
            # Expensive database query
            return await db.query(...).where(id=user_id).first()

        # First call: executes function and caches result
        user = await get_user("123")

        # Second call: returns cached result
        user = await get_user("123")  # Cache hit!
        ```
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _build_cache_key(func, args, kwargs)

            # Add prefix
            if key_prefix:
                cache_key = f"{key_prefix}{cache_key}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def invalidate_cache(
    cache: Cache,
    pattern: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to invalidate cache on function execution.

    Useful for write operations that should clear related cache entries.

    Args:
        cache: Cache instance to use
        pattern: Pattern to match keys for deletion (e.g., "user:*")

    Returns:
        Decorated function that invalidates cache

    Example:
        ```python
        from bento.adapters.cache import create_cache, invalidate_cache

        cache = await create_cache(backend="memory")

        @invalidate_cache(cache, pattern="user:*")
        async def update_user(user_id: str, data: dict) -> None:
            # Update database
            await db.update(...)

            # Cache is automatically invalidated after this function
        ```
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Execute function
            result = await func(*args, **kwargs)

            # Invalidate cache
            await cache.delete_pattern(pattern)

            return result

        return wrapper

    return decorator


def cache_aside[T](
    cache: Cache,
    loader: Callable[..., Awaitable[T]],
    ttl: int | None = None,
    key_prefix: str = "",
) -> Callable[..., Awaitable[T]]:
    """Cache-aside pattern implementation.

    Provides a function that checks cache first, then loads from source.

    Args:
        cache: Cache instance to use
        loader: Function to load data if cache misses
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys

    Returns:
        Function that implements cache-aside pattern

    Example:
        ```python
        from bento.adapters.cache import create_cache, cache_aside

        cache = await create_cache(backend="redis")

        async def load_user_from_db(user_id: str) -> dict:
            return await db.query(...).where(id=user_id).first()

        # Create cache-aside function
        get_user = cache_aside(
            cache,
            loader=load_user_from_db,
            ttl=3600,
            key_prefix="user:"
        )

        # Use it
        user = await get_user("123")  # Loads from DB, caches result
        user = await get_user("123")  # Returns from cache
        ```
    """

    @functools.wraps(loader)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        # Build cache key
        cache_key = _build_cache_key(loader, args, kwargs)
        if key_prefix:
            cache_key = f"{key_prefix}{cache_key}"

        # Try cache
        cached_value = await cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        # Load from source
        result = await loader(*args, **kwargs)

        # Cache result
        if result is not None:
            await cache.set(cache_key, result, ttl=ttl)

        return result

    return wrapper


# ==================== Helper Functions ====================


def _build_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """Build cache key from function and arguments.

    Args:
        func: Function being cached
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Cache key string

    Note:
        Uses SHA256 hash of JSON-serialized arguments for consistent keys.
    """
    # Build key components
    func_name = f"{func.__module__}.{func.__name__}"

    # Serialize arguments
    try:
        args_str = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    except (TypeError, ValueError):
        # Fallback to str representation if JSON fails
        args_str = str({"args": args, "kwargs": kwargs})

    # Hash arguments for consistent key length
    args_hash = hashlib.sha256(args_str.encode()).hexdigest()[:16]

    return f"{func_name}:{args_hash}"
