"""Observable Query Handler - CQRS with built-in observability support.

Provides QueryHandler base class with integrated tracing and logging.
Use this for complex queries that need detailed observability.

Example:
    ```python
    from bento.application.cqrs import ObservableQueryHandler
    from bento.application.ports.observability import ObservabilityProvider

    class ListProductsHandler(ObservableQueryHandler[ListProductsQuery, Page[Product]]):
        def __init__(self, uow: UnitOfWork, observability: ObservabilityProvider):
            super().__init__(uow, observability, "catalog")

        async def handle(self, query: ListProductsQuery) -> Page[Product]:
            async with self.tracer.start_span("list_products") as span:
                # ... query logic ...
                self.logger.info("Products listed", count=len(products))
                return products
    ```
"""

from __future__ import annotations

from typing import Generic, TypeVar

from bento.application.cqrs.query_handler import QueryHandler
from bento.application.ports.observability import ObservabilityProvider
from bento.application.ports.uow import UnitOfWork

__all__ = ["ObservableQueryHandler"]

TQuery = TypeVar("TQuery")
TResult = TypeVar("TResult")


class ObservableQueryHandler(QueryHandler[TQuery, TResult], Generic[TQuery, TResult]):
    """QueryHandler with built-in observability support.

    Provides:
    - self.tracer: For distributed tracing
    - self.logger: For structured logging

    Note: Queries typically don't need metrics (no state changes),
    but tracing and logging are useful for performance monitoring.

    Use this base class for complex queries that need detailed observability.
    For simple queries, use regular QueryHandler.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        observability: ObservabilityProvider,
        context_name: str,
    ) -> None:
        """Initialize observable query handler.

        Args:
            uow: Unit of work for data access
            observability: Observability provider for tracing/logging
            context_name: Context name for tracer/logger (e.g., "ordering", "catalog")
        """
        super().__init__(uow)
        self.tracer = observability.get_tracer(context_name)
        self.logger = observability.get_logger(context_name)
        self._context_name = context_name
