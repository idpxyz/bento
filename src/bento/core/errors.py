"""Core exception system for Bento framework.

This module provides a structured exception hierarchy aligned with DDD layers.

Example:
    ```python
    from bento.core.errors import DomainException
    from bento.core.error_codes import OrderErrors

    # Raise a domain exception
    raise DomainException(
        error_code=OrderErrors.ORDER_NOT_FOUND,
        details={"order_id": "123"}
    )
    ```
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """Exception categories aligned with DDD layers.

    Maps exceptions to architectural layers for better error handling
    and monitoring.
    """

    DOMAIN = "domain"
    """Domain layer - business rule violations"""

    APPLICATION = "application"
    """Application layer - use case failures"""

    INFRASTRUCTURE = "infrastructure"
    """Infrastructure layer - technical failures (DB, cache, etc.)"""

    INTERFACE = "interface"
    """Interface layer - API/validation errors"""


@dataclass(frozen=True)
class ErrorCode:
    """Structured error code definition.

    Provides consistent error identification across the application.

    Attributes:
        code: Unique error code (e.g., "ORDER_001")
        message: Human-readable error message
        http_status: HTTP status code for API responses (default: 500)

    Example:
        ```python
        USER_NOT_FOUND = ErrorCode(
            code="USER_001",
            message="User not found",
            http_status=404
        )
        ```
    """

    code: str
    message: str
    http_status: int = 500


class BentoException(Exception):
    """Base exception for Bento framework.

    All framework exceptions should inherit from this class.
    Provides structured error information for consistent API responses
    and logging.

    Attributes:
        error_code: The error code definition
        category: Exception category (domain/application/infrastructure/interface)
        details: Additional context about the error
        __cause__: Optional underlying exception (exception chaining)

    Example:
        ```python
        from bento.core.errors import BentoException, ErrorCategory
        from bento.core.error_codes import CommonErrors

        raise BentoException(
            error_code=CommonErrors.UNKNOWN_ERROR,
            category=ErrorCategory.INFRASTRUCTURE,
            details={"operation": "database_query"},
            cause=original_exception
        )
        ```
    """

    def __init__(
        self,
        error_code: ErrorCode,
        category: ErrorCategory,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize exception.

        Args:
            error_code: The error code definition
            category: Exception category
            details: Additional error context (optional)
            cause: Underlying exception for exception chaining (optional)
        """
        self.error_code = error_code
        self.category = category
        self.details = details or {}
        self.__cause__ = cause

        super().__init__(error_code.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response.

        Returns:
            Dictionary containing error information

        Example:
            ```python
            {
                "code": "ORDER_001",
                "message": "Order not found",
                "category": "domain",
                "details": {"order_id": "123"}
            }
            ```
        """
        return {
            "code": self.error_code.code,
            "message": self.error_code.message,
            "category": self.category.value,
            "details": self.details,
        }


class DomainException(BentoException):
    """Domain layer exception - business rule violations.

    Raised when domain invariants are violated or business rules fail.
    These exceptions represent business logic errors, not technical failures.

    Example:
        ```python
        from bento.core.errors import DomainException
        from bento.core.error_codes import OrderErrors

        # In Order aggregate
        def pay(self) -> None:
            if self.status == OrderStatus.PAID:
                raise DomainException(
                    error_code=OrderErrors.ORDER_ALREADY_PAID,
                    details={"order_id": self.id.value}
                )
        ```
    """

    def __init__(
        self,
        error_code: ErrorCode,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize domain exception.

        Args:
            error_code: The error code definition
            details: Additional error context (optional)
            cause: Underlying exception (optional)
        """
        super().__init__(
            error_code=error_code,
            category=ErrorCategory.DOMAIN,
            details=details,
            cause=cause,
        )


class ApplicationException(BentoException):
    """Application layer exception - use case failures.

    Raised when application services or use cases fail.
    These exceptions represent coordination or orchestration errors.

    Example:
        ```python
        from bento.core.errors import ApplicationException
        from bento.core.error_codes import CommonErrors

        # In use case
        async def execute(self, command: CreateOrderCommand) -> Order:
            if not command.items:
                raise ApplicationException(
                    error_code=CommonErrors.INVALID_PARAMS,
                    details={"field": "items", "reason": "cannot be empty"}
                )
        ```
    """

    def __init__(
        self,
        error_code: ErrorCode,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize application exception.

        Args:
            error_code: The error code definition
            details: Additional error context (optional)
            cause: Underlying exception (optional)
        """
        super().__init__(
            error_code=error_code,
            category=ErrorCategory.APPLICATION,
            details=details,
            cause=cause,
        )


class InfrastructureException(BentoException):
    """Infrastructure layer exception - technical failures.

    Raised when infrastructure components fail (database, cache, messaging, etc.).
    These exceptions represent technical errors, not business errors.

    Example:
        ```python
        from bento.core.errors import InfrastructureException
        from bento.core.error_codes import CommonErrors

        # In repository
        async def find_by_id(self, order_id: OrderId) -> Order:
            try:
                result = await self.session.execute(...)
            except SQLAlchemyError as e:
                raise InfrastructureException(
                    error_code=CommonErrors.DATABASE_ERROR,
                    details={"operation": "find_order"},
                    cause=e
                )
        ```
    """

    def __init__(
        self,
        error_code: ErrorCode,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize infrastructure exception.

        Args:
            error_code: The error code definition
            details: Additional error context (optional)
            cause: Underlying exception (optional)
        """
        super().__init__(
            error_code=error_code,
            category=ErrorCategory.INFRASTRUCTURE,
            details=details,
            cause=cause,
        )


class InterfaceException(BentoException):
    """Interface layer exception - API/validation errors.

    Raised when interface-level validation fails or API constraints are violated.
    These exceptions represent input/output errors at the system boundary.

    Example:
        ```python
        from bento.core.errors import InterfaceException
        from bento.core.error_codes import CommonErrors

        # In API layer
        @app.post("/orders")
        async def create_order(data: dict):
            if "customer_id" not in data:
                raise InterfaceException(
                    error_code=CommonErrors.INVALID_PARAMS,
                    details={"missing_field": "customer_id"}
                )
        ```
    """

    def __init__(
        self,
        error_code: ErrorCode,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize interface exception.

        Args:
            error_code: The error code definition
            details: Additional error context (optional)
            cause: Underlying exception (optional)
        """
        super().__init__(
            error_code=error_code,
            category=ErrorCategory.INTERFACE,
            details=details,
            cause=cause,
        )


# Legacy aliases for backward compatibility
DomainError = DomainException
ApplicationError = ApplicationException
InfraError = InfrastructureException
