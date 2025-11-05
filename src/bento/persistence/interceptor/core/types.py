"""Interceptor system type definitions.

This module defines the core types used throughout the interceptor system.
"""

from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class InterceptorPriority(IntEnum):
    """Interceptor priority levels.

    Lower numerical values indicate higher priority:
    - HIGHEST: Critical operations (e.g., transactions)
    - HIGH: Core functionality (e.g., optimistic locking)
    - NORMAL: Regular functionality (e.g., audit)
    - LOW: Optional functionality (e.g., logging)
    - LOWEST: Secondary functionality
    """

    HIGHEST = 50
    HIGH = 100
    NORMAL = 200
    LOW = 300
    LOWEST = 400


class OperationType(Enum):
    """Database operation types."""

    CREATE = auto()
    READ = auto()
    GET = auto()
    FIND = auto()
    QUERY = auto()
    UPDATE = auto()
    DELETE = auto()
    BATCH_CREATE = auto()
    BATCH_UPDATE = auto()
    BATCH_DELETE = auto()
    COMMIT = auto()
    ROLLBACK = auto()


@dataclass
class InterceptorContext[T]:
    """Interceptor execution context.

    Contains all contextual information needed during interceptor execution.

    Attributes:
        session: Database session
        entity_type: Type of entity being operated on
        operation: Type of operation being performed
        entity: Single entity (for single operations)
        entities: Multiple entities (for batch operations)
        actor: Current actor/user performing the operation
        config: Interceptor configuration
        context_data: Additional context data
    """

    session: AsyncSession
    entity_type: type[T]
    operation: OperationType
    entity: T | None = None
    entities: list[T] | None = None
    actor: str | None = None
    config: Any | None = None
    context_data: dict[str, Any] = field(default_factory=dict)

    def is_batch_operation(self) -> bool:
        """Check if this is a batch operation.

        Returns:
            True if operation is a batch operation
        """
        return self.operation in (
            OperationType.BATCH_CREATE,
            OperationType.BATCH_UPDATE,
            OperationType.BATCH_DELETE,
        )

    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get a value from context data.

        Args:
            key: Context data key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        return self.context_data.get(key, default)

    def set_context_value(self, key: str, value: Any) -> None:
        """Set a value in context data.

        Args:
            key: Context data key
            value: Value to set
        """
        self.context_data[key] = value

    def has_context_value(self, key: str) -> bool:
        """Check if a context value exists.

        Args:
            key: Context data key

        Returns:
            True if key exists in context data
        """
        return key in self.context_data
