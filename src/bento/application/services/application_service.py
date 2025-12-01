"""Core Application Service implementation.

This module provides the main ApplicationService base class and result wrapper.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from bento.application.ports.uow import UnitOfWork

# Type variables for generic services
TCommand = TypeVar("TCommand")
TResult = TypeVar("TResult")


class ApplicationServiceResult[TResult]:
    """Standard result wrapper for application services."""

    def __init__(self, is_success: bool, data: TResult | None = None, error: str | None = None):
        self.is_success = is_success
        self.data = data
        self.error = error

    @classmethod
    def success(cls, data: TResult | None = None) -> ApplicationServiceResult[TResult]:
        """Create successful result."""
        return cls(is_success=True, data=data)

    @classmethod
    def failure(cls, error: str) -> ApplicationServiceResult[TResult]:
        """Create failure result."""
        return cls(is_success=False, error=error)


class ApplicationService[TCommand, TResult](ABC):
    """Standard Application Service base class.

    Combines the simplicity of use cases with enterprise-grade standardization:

    ✅ Simple API: Only implement handle() method
    ✅ Automatic: UoW, validation, error handling all managed
    ✅ Standard: Returns ApplicationServiceResult for consistency
    ✅ Type Safe: Full generic type support

    Usage:
        ```python
        class CreateProductService(ApplicationService[CreateProductCommand, ProductResult]):
            async def handle(self, command: CreateProductCommand) -> ProductResult:
                # Pure business logic - framework handles everything else
                repo = self.uow.repository(Product)
                product = Product.create_new(command.name, command.price)
                await repo.save(product)
                return ProductResult.from_aggregate(product)

        # Usage
        service = CreateProductService(uow)
        result = await service.execute(command)  # Returns ApplicationServiceResult

        if result.is_success:
            product = result.data  # ProductResult
        else:
            handle_error(result.error)
        ```

    Key Benefits:
    - 🎯 Minimal Code: Only business logic in handle()
    - 🛡️ Automatic Management: UoW, validation, errors
    - 📊 Consistent Results: ApplicationServiceResult format
    - 🔧 Flexible: Override validate() or execute() if needed
    """

    def __init__(self, uow: UnitOfWork):
        """Initialize with UnitOfWork.

        Args:
            uow: UnitOfWork instance for transaction management
        """
        self.uow = uow

    async def validate(self, command: TCommand) -> None:
        """Validate command before execution (override if needed).

        Args:
            command: Command to validate

        Raises:
            ValueError: If command is invalid
        """
        if command is None:
            raise ValueError("Command cannot be None")

    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Implement pure business logic here.

        This method should contain ONLY business logic:
        - Load aggregates via self.uow.repository()
        - Execute domain operations
        - Return business result

        Framework automatically handles:
        - UnitOfWork transaction management
        - Validation
        - Error wrapping
        - Result formatting

        Args:
            command: Input command

        Returns:
            Business result (will be wrapped in ApplicationServiceResult)
        """
        pass

    async def execute(self, command: TCommand) -> ApplicationServiceResult[TResult]:
        """Execute the use case with automatic UoW and error handling.

        This method automatically:
        1. Validates the command
        2. Starts UoW transaction
        3. Calls your handle() method
        4. Commits the transaction
        5. Wraps result in ApplicationServiceResult
        6. Handles any exceptions

        Args:
            command: Input command

        Returns:
            ApplicationServiceResult with success/failure info
        """
        try:
            # 1. Validate command
            await self.validate(command)

            # 2. Execute within UoW transaction
            async with self.uow:
                # 3. Call business logic
                business_result = await self.handle(command)

                # 4. Commit transaction (auto event publishing)
                await self.uow.commit()

                # 5. Return success result
                return ApplicationServiceResult.success(business_result)

        except Exception as e:
            # 6. Automatic error handling
            return ApplicationServiceResult.failure(str(e))


# Utility functions for Application Service patterns


def create_service_factory():
    """Factory function to create application services.

    Returns:
        Function that creates properly configured ApplicationService instances
    """

    def factory(service_class: type, uow: UnitOfWork) -> ApplicationService:
        """Create service instance with UoW dependency injection."""
        return service_class(uow)

    return factory


def validate_service_compliance(service_class: type) -> list[str]:
    """Validate that a service follows Bento Framework standards.

    Args:
        service_class: ApplicationService class to validate

    Returns:
        List of compliance violations (empty if compliant)
    """
    violations = []

    # Check if inherits from proper base class
    from .batch_service import BatchService
    from .query_service import QueryService

    if not issubclass(service_class, (ApplicationService, QueryService, BatchService)):
        violations.append(
            f"{service_class.__name__} must inherit from "
            f"ApplicationService/QueryService/BatchService"
        )

    # Check if __init__ requires UnitOfWork
    init_signature = service_class.__init__.__annotations__
    if "uow" not in init_signature:
        violations.append(
            f"{service_class.__name__}.__init__ must require 'uow: UnitOfWork' parameter"
        )

    # Check if handle method exists
    if not hasattr(service_class, "handle"):
        violations.append(f"{service_class.__name__} must implement handle() method")

    return violations
