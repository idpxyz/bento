from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, TypeVar

from bento.application.ports.cache import Cache
from bento.persistence.interceptor.singleflight import SingleflightGroup

from ..core import (
    Interceptor,
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class _CacheNullValue:
    """Marker for cached null values to prevent cache penetration.

    Supports pickle serialization for compatibility with different cache backends.
    """

    def __reduce__(self):
        """Support pickle serialization."""
        return (_CacheNullValue, ())

    def __repr__(self) -> str:
        return "<CacheNull>"


CACHE_NULL = _CacheNullValue()


class CacheInterceptor(Interceptor[T]):
    interceptor_type: ClassVar[str] = "cache"

    # Default TTL configuration for different operation types
    DEFAULT_TTL_CONFIG: ClassVar[dict[OperationType, int]] = {
        # Basic operations - short cache
        OperationType.GET: 300,
        OperationType.FIND: 300,
        OperationType.QUERY: 300,
        # Aggregate operations - medium cache
        OperationType.AGGREGATE: 600,
        # Group by operations - long cache
        OperationType.GROUP_BY: 3600,
        # Sort/limit operations - short cache
        OperationType.SORT_LIMIT: 300,
        # Pagination - short cache
        OperationType.PAGINATE: 180,
        # Random sampling - no cache
        OperationType.RANDOM_SAMPLE: 0,
    }

    def __init__(
        self,
        cache: Cache,
        *,
        ttl: int = 300,
        ttl_config: dict[OperationType, int] | None = None,
        enabled: bool = True,
        prefix: str = "",
        # Performance optimizations
        enable_singleflight: bool = True,
        singleflight_timeout: float = 5.0,
        enable_jitter: bool = True,
        jitter_range: float = 0.1,
        # Cache penetration protection
        enable_null_cache: bool = True,
        null_cache_ttl: int = 10,
        # Fault tolerance
        fail_open: bool = True,
        cache_timeout: float = 0.1,
    ) -> None:
        self._cache = cache
        self._ttl = ttl  # Default TTL
        self._ttl_config = ttl_config or self.DEFAULT_TTL_CONFIG
        self._enabled = enabled
        self._prefix = prefix

        # Performance optimizations
        self._singleflight = SingleflightGroup() if enable_singleflight else None
        self._singleflight_timeout = singleflight_timeout
        self._enable_jitter = enable_jitter
        self._jitter_range = jitter_range  # ±10% by default

        # Cache penetration protection
        self._enable_null_cache = enable_null_cache
        self._null_cache_ttl = null_cache_ttl

        # Fault tolerance
        self._fail_open = fail_open
        self._cache_timeout = cache_timeout

        # Statistics for monitoring
        self._stats = {
            "singleflight_saved": 0,  # Queries saved by singleflight
            "singleflight_timeout": 0,  # Singleflight timeouts
            "fail_open_count": 0,  # Fail-open degradations
            "null_cache_hits": 0,  # Null cache hits
            "cache_hits": 0,  # Total cache hits
            "cache_misses": 0,  # Total cache misses
        }

    @property
    def priority(self) -> InterceptorPriority:
        return InterceptorPriority.HIGH

    @classmethod
    def is_enabled_in_config(cls, config: Any) -> bool:
        return getattr(config, "enable_cache", False) is True

    def _get_entity_type(self, context: InterceptorContext[T]) -> str:
        return context.entity_type.__name__

    def _get_cache_key(self, context: InterceptorContext[T]) -> str | None:
        """Generate cache key based on operation type and context."""
        et = self._get_entity_type(context)
        op = context.operation

        # Basic operations
        if op in (OperationType.READ, OperationType.GET, OperationType.FIND):
            if context.has_context_value("entity_id"):
                return f"{et}:id:{context.get_context_value('entity_id')}"
            if context.entity and hasattr(context.entity, "id"):
                entity: Any = context.entity
                return f"{et}:id:{entity.id}"
            return None

        if op is OperationType.QUERY:
            params = context.get_context_value("query_params", None)
            if not params:
                return None
            items = sorted((str(k), str(v)) for k, v in params.items())
            joined = ",".join(f"{k}:{v}" for k, v in items)
            return f"{et}:query:{joined}" if joined else f"{et}:query"

        # Aggregate operations
        if op == OperationType.AGGREGATE:
            method = context.get_context_value("aggregate_method", "unknown")
            field = context.get_context_value("field", "")
            spec_hash = self._get_spec_hash(context)
            return f"{et}:agg:{method}:{field}:{spec_hash}"

        # Group by operations
        if op == OperationType.GROUP_BY:
            fields = context.get_context_value("group_fields", [])
            period = context.get_context_value("period", "")
            spec_hash = self._get_spec_hash(context)
            fields_str = ":".join(fields) if isinstance(fields, list) else str(fields)
            return f"{et}:group:{fields_str}:{period}:{spec_hash}"

        # Sort/limit operations
        if op == OperationType.SORT_LIMIT:
            method = context.get_context_value("method", "unknown")
            order_by = context.get_context_value("order_by", "")
            limit = context.get_context_value("limit", "")
            spec_hash = self._get_spec_hash(context)
            return f"{et}:sort:{method}:{order_by}:{limit}:{spec_hash}"

        # Pagination operations
        if op == OperationType.PAGINATE:
            page = context.get_context_value("page", 1)
            page_size = context.get_context_value("page_size", 20)
            order_by = context.get_context_value("order_by", "")
            spec_hash = self._get_spec_hash(context)
            return f"{et}:page:{page}:{page_size}:{order_by}:{spec_hash}"

        return None

    def _get_spec_hash(self, context: InterceptorContext[T]) -> str:
        """Get hash of specification for cache key."""
        spec = context.get_context_value("specification")
        if spec is None:
            return "none"
        # Generate hash from spec string representation
        spec_str = str(spec)
        return hashlib.md5(spec_str.encode()).hexdigest()[:8]

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}" if self._prefix else key

    def _is_read(self, op: OperationType) -> bool:
        """Check if operation is a read operation that can be cached."""
        return op in (
            OperationType.READ,
            OperationType.GET,
            OperationType.FIND,
            OperationType.QUERY,
            # New cacheable operations
            OperationType.AGGREGATE,
            OperationType.GROUP_BY,
            OperationType.SORT_LIMIT,
            OperationType.PAGINATE,
            # Note: RANDOM_SAMPLE is intentionally excluded
        )

    def _get_ttl(self, operation: OperationType) -> int:
        """Get TTL for operation type."""
        return self._ttl_config.get(operation, self._ttl)

    def _apply_jitter(self, base_ttl: int) -> int:
        """Apply random jitter to TTL to prevent cache avalanche.

        Args:
            base_ttl: Base TTL in seconds

        Returns:
            TTL with random jitter applied (±jitter_range%)

        Example:
            base_ttl=600, jitter_range=0.1 → 540~660 seconds
        """
        if not self._enable_jitter or base_ttl == 0:
            return base_ttl

        multiplier = random.uniform(1 - self._jitter_range, 1 + self._jitter_range)
        return int(base_ttl * multiplier)

    def _is_write(self, op: OperationType) -> bool:
        return op in (
            OperationType.CREATE,
            OperationType.UPDATE,
            OperationType.DELETE,
            OperationType.BATCH_CREATE,
            OperationType.BATCH_UPDATE,
            OperationType.BATCH_DELETE,
        )

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]],
    ) -> Any:
        if not self._enabled or not self._is_read(context.operation):
            return await next_interceptor(context)

        key = self._get_cache_key(context)
        if not key:
            return await next_interceptor(context)

        # Use singleflight to prevent cache breakdown
        if self._singleflight:

            async def query_cache():
                return await self._get_from_cache_with_fallback(key)

            try:
                # Add timeout to prevent slow queries from blocking all requests
                cached = await asyncio.wait_for(
                    self._singleflight.do(key, query_cache), timeout=self._singleflight_timeout
                )
                # Check if we saved queries (singleflight was effective)
                stats = self._singleflight.stats()
                if key in stats.get("keys", []):
                    self._stats["singleflight_saved"] += 1

            except TimeoutError:
                self._stats["singleflight_timeout"] += 1
                logger.error(
                    f"Singleflight timeout for key: {key}",
                    extra={"key": key, "timeout": self._singleflight_timeout},
                )
                if self._fail_open:
                    cached = None  # Fail open: continue without cache
                else:
                    raise
        else:
            cached = await self._get_from_cache_with_fallback(key)

        # Handle null value marker
        if isinstance(cached, _CacheNullValue):
            self._stats["null_cache_hits"] += 1
            return None  # Prevents database query for known null values

        if cached is not None:
            self._stats["cache_hits"] += 1
            return cached

        self._stats["cache_misses"] += 1

        return await next_interceptor(context)

    async def _get_from_cache_with_fallback(self, key: str) -> Any:
        """Get from cache with fault tolerance.

        Implements fail-open pattern: cache failures don't block the application.
        """
        try:
            cached = await asyncio.wait_for(
                self._cache.get(self._full_key(key)), timeout=self._cache_timeout
            )
            return cached

        except TimeoutError:
            self._stats["fail_open_count"] += 1
            logger.warning(
                f"Cache timeout for key: {key}", extra={"key": key, "timeout": self._cache_timeout}
            )
            if self._fail_open:
                return None  # Fail open: continue without cache
            raise

        except Exception as e:
            self._stats["fail_open_count"] += 1
            logger.error(
                f"Cache error for key: {key}", extra={"key": key, "error": str(e)}, exc_info=True
            )
            if self._fail_open:
                return None  # Fail open: continue without cache
            raise

    async def process_result(
        self,
        context: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[InterceptorContext[T], Any], Awaitable[Any]],
    ) -> Any:
        if not self._enabled:
            return await next_interceptor(context, result)

        if self._is_read(context.operation):
            key = self._get_cache_key(context)
            if key:
                # Cache null values to prevent penetration
                if result is None and self._enable_null_cache:
                    cache_value = CACHE_NULL
                    ttl = self._null_cache_ttl  # Short TTL for null values
                elif result is not None:
                    cache_value = result
                    ttl = self._get_ttl(context.operation)
                    # Apply jitter to prevent cache avalanche
                    ttl = self._apply_jitter(ttl)
                else:
                    # result is None and null cache disabled
                    return await next_interceptor(context, result)

                # Set cache with fault tolerance
                try:
                    await asyncio.wait_for(
                        self._cache.set(self._full_key(key), cache_value, ttl=ttl),
                        timeout=self._cache_timeout,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to set cache for key: {key}", extra={"key": key, "error": str(e)}
                    )
                    # Continue even if cache set fails (fail-open)

                return await next_interceptor(context, result)

        if self._is_write(context.operation):
            await self._invalidate_related(context)
            return await next_interceptor(context, result)

        return await next_interceptor(context, result)

    async def process_batch_results(
        self,
        context: InterceptorContext[T],
        results: list[T],
        next_interceptor: Callable[[InterceptorContext[T], list[T]], Awaitable[list[T]]],
    ) -> list[T]:
        if not self._enabled:
            return await next_interceptor(context, results)

        if context.operation is OperationType.QUERY:
            key = self._get_cache_key(context)
            if key is not None:
                # Use operation-specific TTL with jitter
                ttl = self._get_ttl(context.operation)
                ttl = self._apply_jitter(ttl)

                try:
                    await asyncio.wait_for(
                        self._cache.set(self._full_key(key), results, ttl=ttl),
                        timeout=self._cache_timeout,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to set batch cache for key: {key}",
                        extra={"key": key, "error": str(e)},
                    )
        elif context.operation in (
            OperationType.BATCH_CREATE,
            OperationType.BATCH_UPDATE,
            OperationType.BATCH_DELETE,
        ):
            # Invalidate per-entity id cache and all related caches
            et = self._get_entity_type(context)
            if context.entities:
                for ent in context.entities:
                    eid = getattr(ent, "id", None)
                    if eid is not None:
                        await self._cache.delete(self._full_key(f"{et}:id:{eid}"))

            # Invalidate all query-related caches for this entity type
            await self._cache.delete_pattern(self._full_key(f"{et}:query*"))
            await self._cache.delete_pattern(self._full_key(f"{et}:agg:*"))
            await self._cache.delete_pattern(self._full_key(f"{et}:group:*"))
            await self._cache.delete_pattern(self._full_key(f"{et}:sort:*"))
            await self._cache.delete_pattern(self._full_key(f"{et}:page:*"))

        return await next_interceptor(context, results)

    async def _invalidate_related(self, context: InterceptorContext[T]) -> None:
        """Invalidate related cache entries when entity is modified."""
        et = self._get_entity_type(context)
        entity_id = None
        if context.entity and hasattr(context.entity, "id"):
            entity: Any = context.entity
            entity_id = entity.id

        # Invalidate entity-specific cache
        if entity_id is not None:
            await self._cache.delete(self._full_key(f"{et}:id:{entity_id}"))

        # Invalidate all query caches for this entity type
        await self._cache.delete_pattern(self._full_key(f"{et}:query*"))

        # Invalidate aggregate query caches
        await self._cache.delete_pattern(self._full_key(f"{et}:agg:*"))

        # Invalidate group by caches
        await self._cache.delete_pattern(self._full_key(f"{et}:group:*"))

        # Invalidate sort/limit caches
        await self._cache.delete_pattern(self._full_key(f"{et}:sort:*"))

        # Invalidate pagination caches
        await self._cache.delete_pattern(self._full_key(f"{et}:page:*"))

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary containing cache statistics:
            - singleflight_saved: Number of queries saved by singleflight
            - singleflight_timeout: Number of singleflight timeouts
            - fail_open_count: Number of fail-open degradations
            - null_cache_hits: Number of null cache hits
            - cache_hits: Total cache hits
            - cache_misses: Total cache misses

        Example:
            ```python
            stats = cache_interceptor.get_stats()
            hit_rate = stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses'])
            print(f"Cache hit rate: {hit_rate:.2%}")
            print(f"Singleflight savings: {stats['singleflight_saved']}")
            ```
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset cache statistics.

        Useful for testing or periodic metric collection.
        """
        for key in self._stats:
            self._stats[key] = 0
