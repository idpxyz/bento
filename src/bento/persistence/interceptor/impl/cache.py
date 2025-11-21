from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, TypeVar

from bento.application.ports.cache import Cache

from ..core import (
    Interceptor,
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)

T = TypeVar("T")


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
    ) -> None:
        self._cache = cache
        self._ttl = ttl  # Default TTL
        self._ttl_config = ttl_config or self.DEFAULT_TTL_CONFIG
        self._enabled = enabled
        self._prefix = prefix

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

        cached = await self._cache.get(self._full_key(key))
        if cached is not None:
            return cached

        return await next_interceptor(context)

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
            if key and result is not None:
                # Use operation-specific TTL
                ttl = self._get_ttl(context.operation)
                await self._cache.set(self._full_key(key), result, ttl=ttl)
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
                # Use operation-specific TTL
                ttl = self._get_ttl(context.operation)
                await self._cache.set(self._full_key(key), results, ttl=ttl)
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
