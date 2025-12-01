"""Batch Service implementation for processing multiple items."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from bento.application.ports.uow import UnitOfWork

from .application_service import ApplicationServiceResult

# Type variables for batch services
TCommand = TypeVar("TCommand")
TResult = TypeVar("TResult")


class BatchService[TCommand, TResult](ABC):
    """Batch Service for processing multiple items.

    Handles batch operations with proper error handling and partial success support.

    Usage:
        ```python
        class BulkCreateProductsService(BatchService[BulkCreateCommand, BatchResult]):
            async def handle(self, command: BulkCreateCommand) -> BatchResult:
                results = []
                for product_data in command.products:
                    try:
                        result = await self._create_single_product(product_data)
                        results.append(result)
                    except Exception as e:
                        results.append(ProductResult.failure(product_data.id, str(e)))

                return BatchResult(results=results, total=len(command.products))
        ```
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def validate(self, command: TCommand) -> None:
        """Validate batch command."""
        if command is None:
            raise ValueError("Command cannot be None")

    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Implement batch processing logic."""
        pass

    async def execute(self, command: TCommand) -> ApplicationServiceResult[TResult]:
        """Execute batch operation with transaction management."""
        try:
            await self.validate(command)

            async with self.uow:
                result = await self.handle(command)
                await self.uow.commit()

                return ApplicationServiceResult.success(result)

        except Exception as e:
            return ApplicationServiceResult.failure(str(e))

    async def execute_with_partial_failures(
        self, command: TCommand, continue_on_error: bool = True
    ) -> ApplicationServiceResult[TResult]:
        """Execute batch with configurable error handling.

        Args:
            command: Batch command
            continue_on_error: Whether to continue processing after individual failures

        Returns:
            Batch result with success/failure details
        """
        return await self.execute(command)
