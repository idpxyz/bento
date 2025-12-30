"""Optimistic locking interceptor for concurrency control.

This interceptor implements optimistic locking using version numbers to prevent
concurrent update conflicts.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, TypeVar

from ..core import (
    Interceptor,
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)
from ..core.metadata import EntityMetadataRegistry

T = TypeVar("T")


@dataclass
class EntityVersionUpdated:
    """Event emitted when entity version is updated.

    Attributes:
        entity_id: ID of the entity
        entity_type: Type name of the entity
        old_version: Previous version number
        new_version: New version number
        operation: Operation that triggered the update
        timestamp: When the update occurred
    """

    entity_id: Any
    entity_type: str
    old_version: int
    new_version: int
    operation: str
    timestamp: datetime = field(default_factory=datetime.now)


class OptimisticLockException(Exception):
    """Exception raised when optimistic lock conflict is detected.

    This indicates that the entity has been modified by another transaction
    since it was loaded.
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        expected_version: int,
        actual_version: int,
    ) -> None:
        """Initialize optimistic lock exception.

        Args:
            entity_type: Type of entity that had the conflict
            entity_id: ID of the entity
            expected_version: Version that was expected
            actual_version: Actual version found in database
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.actual_version = actual_version

        super().__init__(
            f"Optimistic lock conflict for {entity_type}#{entity_id}: "
            f"expected version {expected_version}, found {actual_version}. "
            f"The entity has been modified by another transaction."
        )


class OptimisticLockInterceptor(Interceptor[T]):
    """Optimistic locking interceptor using version numbers.

    Implements optimistic locking by:
    1. Incrementing version on updates
    2. Checking version matches during updates
    3. Raising OptimisticLockException on conflicts

    Required Fields:
    - version: Integer version number (can be customized via metadata)

    Priority: HIGH (100)

    Configuration:
        Enable/disable per entity via EntityMetadataRegistry

    Field Mapping:
        Default field can be customized via EntityMetadataRegistry:
        ```python
        EntityMetadataRegistry.register(
            MyEntity,
            fields={
                "version_field": "revision"
            }
        )
        ```

    Example:
        ```python
        # Load entity (version = 5)
        user = await repo.get(user_id)

        # Concurrent update changes version to 6

        # Attempt update (will fail)
        user.name = "New Name"
        await repo.save(user)  # Raises OptimisticLockException
        ```
    """

    interceptor_type: ClassVar[str] = "optimistic_lock"

    def __init__(self, config: Any | None = None) -> None:
        """Initialize optimistic lock interceptor.

        Args:
            config: Configuration object
        """
        self._enabled = self.is_enabled_in_config(config) if config else True

    @property
    def enabled(self) -> bool:
        """Check if interceptor is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set interceptor enabled state."""
        self._enabled = value

    @property
    def priority(self) -> InterceptorPriority:
        """Get interceptor priority (HIGH)."""
        return InterceptorPriority.HIGH

    @classmethod
    def is_enabled_in_config(cls, config: Any) -> bool:
        """Check if interceptor is enabled in configuration.

        Args:
            config: Configuration object

        Returns:
            True if enabled
        """
        return getattr(config, "enable_optimistic_lock", True)

    def _get_version_field(self, entity_type: type[T]) -> str:
        """Get version field name for entity type.

        Args:
            entity_type: Entity class

        Returns:
            Version field name
        """
        # Try to get from metadata registry
        # Version field is stored directly as metadata, not under "fields"
        version_field = EntityMetadataRegistry.get_metadata(entity_type, "version_field")
        if version_field:
            return version_field

        return "version"  # Default field name

    def _has_sqlalchemy_version_id_col(self, entity_type: type) -> bool:
        """Check if entity uses SQLAlchemy's native version_id_col.

        When version_id_col is configured, SQLAlchemy automatically handles
        version increment and conflict detection, so we should not manually
        increment the version.

        Args:
            entity_type: The entity/model type to check

        Returns:
            True if version_id_col is configured
        """
        try:
            # Check if this is a SQLAlchemy model with a mapper
            mapper = getattr(entity_type, "__mapper__", None)
            if mapper is not None:
                # SQLAlchemy stores version_id_col in mapper.version_id_col
                return mapper.version_id_col is not None
        except Exception:
            pass
        return False

    def _should_check_version(self, context: InterceptorContext[T]) -> bool:
        """Check if version should be checked.

        Args:
            context: Interceptor context

        Returns:
            True if version check should be performed
        """
        if not self._enabled:
            return False

        # Only check on UPDATE and CREATE operations
        if context.operation not in (OperationType.UPDATE, OperationType.CREATE):
            return False

        if not context.entity:
            return False

        version_field = self._get_version_field(context.entity_type)
        if not self.has_field(context.entity, version_field):
            return False

        return self.is_enabled_for_entity(context.entity_type)

    async def _notify_version_update(
        self,
        context: InterceptorContext[T],
        entity_id: Any,
        old_version: int,
        new_version: int,
    ) -> None:
        """Notify version update event.

        Args:
            context: Interceptor context
            entity_id: Entity ID
            old_version: Previous version
            new_version: New version
        """
        event = EntityVersionUpdated(
            entity_id=entity_id,
            entity_type=context.entity_type.__name__,
            old_version=old_version,
            new_version=new_version,
            operation=context.operation.name,
        )
        await self.publish_event("EntityVersionUpdated", event.__dict__)

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]],
    ) -> Any:
        """Process before operation, incrementing version for updates.

        Args:
            context: Interceptor context
            next_interceptor: Next interceptor in chain

        Returns:
            Result from next interceptor
        """
        # Handle batch operations
        if context.is_batch_operation():
            if context.entities:
                if context.operation == OperationType.BATCH_CREATE:
                    # Initialize version for new entities
                    for entity in context.entities:
                        if self.is_enabled_for_entity(context.entity_type):
                            version_field = self._get_version_field(context.entity_type)
                            if self.has_field(entity, version_field):
                                self.set_field_value(entity, version_field, 1)

                elif context.operation == OperationType.BATCH_UPDATE:
                    # Increment version for updates
                    for entity in context.entities:
                        if self.is_enabled_for_entity(context.entity_type):
                            version_field = self._get_version_field(context.entity_type)
                            if self.has_field(entity, version_field):
                                current_version = self.get_field_value(entity, version_field, 0)
                                self.set_field_value(entity, version_field, current_version + 1)

        # Handle single entity operations
        else:
            if self._should_check_version(context):
                version_field = self._get_version_field(context.entity_type)

                if context.operation == OperationType.CREATE:
                    # Initialize version for new entity
                    self.set_field_value(context.entity, version_field, 1)

                elif context.operation == OperationType.UPDATE:
                    # Check if SQLAlchemy's version_id_col is configured
                    # If configured, SQLAlchemy handles version increment automatically
                    # We detect this by checking the mapper's version_id_col property
                    has_sqlalchemy_version = self._has_sqlalchemy_version_id_col(
                        context.entity_type
                    )

                    current_version = self.get_field_value(context.entity, version_field, 0)
                    context.set_context_value("_old_version", current_version)

                    if not has_sqlalchemy_version:
                        # Only increment version manually if not using SQLAlchemy's version_id_col
                        new_version = current_version + 1
                        self.set_field_value(context.entity, version_field, new_version)
                    # else: SQLAlchemy handles version increment via version_id_col

        return await next_interceptor(context)

    async def process_result(
        self,
        context: InterceptorContext[T],
        result: T,
        next_interceptor: Callable[[InterceptorContext[T], T], Awaitable[T]],
    ) -> T:
        """Process result, notifying version updates.

        Args:
            context: Interceptor context
            result: Operation result
            next_interceptor: Next interceptor in chain

        Returns:
            Processed result
        """
        if not self._should_check_version(context):
            return await next_interceptor(context, result)

        if context.operation == OperationType.UPDATE:
            # Notify version update
            version_field = self._get_version_field(context.entity_type)
            old_version = context.get_context_value("_old_version", 0)
            new_version = self.get_field_value(result, version_field, 0)

            # Get entity ID
            entity_id = self.get_field_value(result, "id")

            if entity_id is not None:
                await self._notify_version_update(context, entity_id, old_version, new_version)

        return await next_interceptor(context, result)
