"""Command Handler Base Class - CQRS Write Operations.

This module provides the CommandHandler base class for implementing
commands in the CQRS pattern. Commands modify system state and trigger domain events.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from bento.application.ports.uow import UnitOfWork

# Type variables
TCommand = TypeVar("TCommand")
TResult = TypeVar("TResult")


class CommandHandler[TCommand, TResult](ABC):
    """Base class for Command Handlers (CQRS Write Operations).

    Command Handlers:
    - Modify system state
    - Trigger domain events
    - Require transactions (UnitOfWork)
    - Should be idempotent when possible

    Responsibilities:
    1. Validate command
    2. Load domain objects
    3. Execute business logic
    4. Persist changes
    5. Publish domain events (automatic)

    Example:
        ```python
        class CreateProductHandler(CommandHandler[CreateProductCommand, str]):
            async def validate(self, command: CreateProductCommand) -> None:
                if not command.name:
                    raise ValidationError("name is required")

            async def handle(self, command: CreateProductCommand) -> str:
                product = Product.create(command.name, command.price)
                repo = self.uow.repository(Product)
                await repo.save(product)
                return str(product.id)
        ```

    Usage:
        ```python
        handler = CreateProductHandler(uow)
        result = await handler.execute(command)
        ```
    """

    def __init__(self, uow: UnitOfWork):
        """Initialize handler with Unit of Work.

        Args:
            uow: Unit of Work for transaction management
        """
        self.uow = uow

    async def validate(self, command: TCommand) -> None:
        """Validate command before execution.
        
        Override this method to add custom validation logic.
        Raise exceptions for validation failures.
        
        Default implementation performs no validation (optional hook method).

        Args:
            command: The command to validate

        Raises:
            ValidationError: If validation fails
        """
        # Default: no validation (this is an optional hook method)
        return None  # noqa: B027

    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Handle command execution (business logic).

        This method contains the core business logic.
        It will be executed within a transaction.

        Args:
            command: The command to execute

        Returns:
            Result of the command execution

        Raises:
            DomainException: If business rules are violated
        """
        ...

    async def execute(self, command: TCommand) -> TResult:
        """Execute the command with transaction management.

        This method orchestrates the command execution:
        1. Validates the command
        2. Executes business logic (handle)
        3. Commits transaction
        4. Publishes domain events

        Args:
            command: The command to execute

        Returns:
            Result of the command execution

        Raises:
            ValidationError: If validation fails
            DomainException: If business rules are violated
        """
        # Step 1: Validate
        await self.validate(command)

        # Step 2-4: Execute in transaction (UoW handles commit and events)
        async with self.uow:
            result = await self.handle(command)
            await self.uow.commit()
            return result
