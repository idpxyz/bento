"""Query Service implementation for read-only operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from bento.application.ports.uow import UnitOfWork

from .application_service import ApplicationServiceResult

# Type variables for query services
TQuery = TypeVar("TQuery")
TResult = TypeVar("TResult")


class QueryService[TQuery, TResult](ABC):
    """Query Service for read-only operations.

    Optimized for query operations that don't need transaction management.

    Usage:
        ```python
        class GetProductService(QueryService[GetProductQuery, ProductDetailsDTO]):
            async def handle(self, query: GetProductQuery) -> ProductDetailsDTO:
                repo = self.uow.repository(Product)
                product = await repo.get(query.product_id)

                if not product:
                    raise ValueError(f"Product {query.product_id} not found")

                return ProductDetailsDTO.from_aggregate(product)
        ```
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def validate(self, query: TQuery) -> None:
        """Validate query (override if needed)."""
        if query is None:
            raise ValueError("Query cannot be None")

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Implement query logic (read-only)."""
        pass

    async def execute(self, query: TQuery) -> ApplicationServiceResult[TResult]:
        """Execute query with automatic validation and error handling."""
        try:
            await self.validate(query)

            # No transaction needed for read-only operations
            result = await self.handle(query)

            return ApplicationServiceResult.success(result)

        except Exception as e:
            return ApplicationServiceResult.failure(str(e))
