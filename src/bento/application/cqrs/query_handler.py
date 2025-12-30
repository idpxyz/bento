"""Query Handler Base Class - CQRS Read Operations.

This module provides the QueryHandler base class for implementing
queries in the CQRS pattern. Queries are read-only operations that don't modify state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from bento.application.ports.uow import UnitOfWork

# Type variables
TQuery = TypeVar("TQuery")
TResult = TypeVar("TResult")


class QueryHandler[TQuery, TResult](ABC):
    """Base class for Query Handlers (CQRS Read Operations).

    Query Handlers:
    - Read-only operations
    - Do NOT modify state
    - Do NOT trigger domain events
    - May or may not need transactions
    - Return DTOs (not domain objects)

    Responsibilities:
    1. Validate query parameters
    2. Fetch data
    3. Convert to DTO
    4. Return response

    Example:
        ```python
        class GetProductHandler(QueryHandler[GetProductQuery, ProductResponse]):
            async def handle(self, query: GetProductQuery) -> ProductResponse:
                repo = self.uow.repository(Product)
                product = await repo.get(ID(query.product_id))
                if not product:
                    raise EntityNotFoundError(f"Product {query.product_id} not found")
                return ProductResponse.from_domain(product)
        ```

    Usage:
        ```python
        handler = GetProductHandler(uow)
        response = await handler.execute(query)
        ```
    """

    def __init__(self, uow: UnitOfWork):
        """Initialize handler with Unit of Work.

        Args:
            uow: Unit of Work for data access
        """
        self.uow = uow

    async def validate(self, query: TQuery) -> None:
        """Validate query parameters before execution.

        Override this method to add custom validation logic.
        Raise exceptions for validation failures.

        Default implementation performs no validation (optional hook method).

        Args:
            query: The query to validate

        Raises:
            ValidationError: If validation fails
        """
        # Default: no validation (this is an optional hook method)
        return None  # noqa: B027

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Handle query execution (data fetching logic).

        This method contains the query logic.
        It should be read-only and not modify any state.

        Args:
            query: The query to execute

        Returns:
            Query result (usually a DTO)

        Raises:
            EntityNotFoundError: If requested entity not found
        """
        ...

    async def execute(self, query: TQuery) -> TResult:
        """Execute the query.

        This method orchestrates the query execution:
        1. Validates the query
        2. Executes query logic (handle)
        3. Returns result

        Note: Queries typically don't need transactions,
        but we use UoW for consistent data access interface.

        Args:
            query: The query to execute

        Returns:
            Query result

        Raises:
            ValidationError: If validation fails
            EntityNotFoundError: If entity not found
        """
        # Step 1: Validate
        await self.validate(query)

        # Step 2: Execute (read-only, no commit needed)
        return await self.handle(query)
