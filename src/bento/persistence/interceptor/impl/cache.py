from __future__ import annotations

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

    def __init__(
        self,
        cache: Cache,
        *,
        ttl: int = 300,
        enabled: bool = True,
        prefix: str = "",
    ) -> None:
        self._cache = cache
        self._ttl = ttl
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
        et = self._get_entity_type(context)
        op = context.operation
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
        return None

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}" if self._prefix else key

    def _is_read(self, op: OperationType) -> bool:
        return op in (
            OperationType.READ,
            OperationType.GET,
            OperationType.FIND,
            OperationType.QUERY,
        )

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
                await self._cache.set(self._full_key(key), result, ttl=self._ttl)
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
                await self._cache.set(self._full_key(key), results, ttl=self._ttl)
        elif context.operation in (
            OperationType.BATCH_CREATE,
            OperationType.BATCH_UPDATE,
            OperationType.BATCH_DELETE,
        ):
            # Invalidate per-entity id cache and list query cache
            et = self._get_entity_type(context)
            if context.entities:
                for ent in context.entities:
                    eid = getattr(ent, "id", None)
                    if eid is not None:
                        await self._cache.delete(self._full_key(f"{et}:id:{eid}"))
            await self._cache.delete_pattern(self._full_key(f"{et}:query*"))

        return await next_interceptor(context, results)

    async def _invalidate_related(self, context: InterceptorContext[T]) -> None:
        et = self._get_entity_type(context)
        entity_id = None
        if context.entity and hasattr(context.entity, "id"):
            entity: Any = context.entity
            entity_id = entity.id
        if entity_id is not None:
            await self._cache.delete(self._full_key(f"{et}:id:{entity_id}"))
        await self._cache.delete_pattern(self._full_key(f"{et}:query*"))
