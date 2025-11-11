"""Soft delete interceptor for logical deletion.

This interceptor converts hard deletes into soft deletes by marking entities
as deleted instead of actually removing them from the database.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, ClassVar, TypeVar

from ..core import Interceptor, InterceptorContext, InterceptorPriority, OperationType
from ..core.metadata import EntityMetadataRegistry

T = TypeVar("T")


class SoftDeleteInterceptor(Interceptor[T]):
    """Soft delete interceptor for logical deletion.

    Converts DELETE operations into UPDATE operations that mark the entity
    as deleted rather than physically removing it from the database.

    Fields maintained:
    - deleted_at: Timestamp of deletion (NULL = not deleted)
    - deleted_by: Actor who performed the deletion

    Note:
        This interceptor does NOT use an is_deleted boolean field.
        Soft delete status is determined by deleted_at IS NOT NULL.

    Priority: NORMAL (200)

    Configuration:
        Enable/disable per entity via EntityMetadataRegistry

    Field Mapping:
        Default fields can be customized via EntityMetadataRegistry:
        ```python
        EntityMetadataRegistry.register(
            MyEntity,
            fields={
                "soft_delete_fields": {
                    "deleted_at": "archived_at",
                    "deleted_by": "archived_by"
                }
            }
        )
        ```

    Example:
        ```python
        # Instead of: DELETE FROM users WHERE id = 1
        # Executes: UPDATE users SET deleted_at = NOW(), deleted_by = 'actor' WHERE id = 1
        ```
    """

    interceptor_type: ClassVar[str] = "soft_delete"

    def __init__(self, actor: str | None = None) -> None:
        """Initialize soft delete interceptor.

        Args:
            actor: User/actor performing the operations
        """
        self._actor = actor or "system"

    @property
    def priority(self) -> InterceptorPriority:
        """Get interceptor priority."""
        return InterceptorPriority.NORMAL

    @classmethod
    def is_enabled_in_config(cls, config: Any) -> bool:
        """Check if interceptor is enabled in configuration.

        Args:
            config: Configuration object

        Returns:
            True if enabled
        """
        return getattr(config, "enable_soft_delete", True)

    def _get_soft_delete_fields(self, entity_type: type[T]) -> dict[str, str]:
        """Get soft delete field mappings for entity type.

        Args:
            entity_type: Entity class

        Returns:
            Dictionary mapping standard field names to actual field names
        """
        # Try to get from metadata registry
        # Fields are stored under "fields" key, then "soft_delete_fields" sub-key
        all_fields = EntityMetadataRegistry.get_metadata(entity_type, "fields")
        if all_fields and isinstance(all_fields, dict):
            soft_delete_fields = all_fields.get("soft_delete_fields")
            if soft_delete_fields:
                return soft_delete_fields

        # Default field mapping (no is_deleted field, use deleted_at IS NOT NULL)
        return {
            "deleted_at": "deleted_at",
            "deleted_by": "deleted_by",
        }

    def _should_soft_delete(self, context: InterceptorContext[T]) -> bool:
        """Check if soft delete should be applied.

        Args:
            context: Interceptor context

        Returns:
            True if soft delete should be applied
        """
        # Only applicable to DELETE operations
        if context.operation != OperationType.DELETE:
            return False

        if not context.entity:
            return False

        # Check if entity has deleted_at field
        fields = self._get_soft_delete_fields(context.entity_type)
        deleted_at_field = fields.get("deleted_at", "deleted_at")

        if not self.has_field(context.entity, deleted_at_field):
            return False

        # Check if enabled for this entity type
        return self.is_enabled_for_entity(context.entity_type)

    def _apply_soft_delete(self, entity: Any, entity_type: type[T]) -> None:
        """Apply soft delete marking to entity.

        Args:
            entity: Entity instance
            entity_type: Entity class
        """
        fields = self._get_soft_delete_fields(entity_type)

        # Check if already deleted (deleted_at is not None)
        deleted_at_field = fields.get("deleted_at", "deleted_at")
        if self.get_field_value(entity, deleted_at_field, None) is not None:
            # Already deleted, skip
            return

        now = datetime.now(UTC)
        actor = self._actor

        # Set deletion timestamp
        if self.has_field(entity, deleted_at_field):
            self.set_field_value(entity, deleted_at_field, now)

        # Set deletion actor
        deleted_by_field = fields.get("deleted_by", "deleted_by")
        if self.has_field(entity, deleted_by_field):
            self.set_field_value(entity, deleted_by_field, actor)

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]],
    ) -> Any:
        """Process before operation, handling soft delete.

        Args:
            context: Interceptor context
            next_interceptor: Next interceptor in chain

        Returns:
            Result from next interceptor
        """
        # Check if already processed
        if context.get_context_value("soft_delete_processed", False):
            return await next_interceptor(context)

        # Handle batch delete operations
        if context.operation == OperationType.BATCH_DELETE and context.entities:
            for entity in context.entities:
                if self.is_enabled_for_entity(context.entity_type):
                    fields = self._get_soft_delete_fields(context.entity_type)
                    deleted_at_field = fields.get("deleted_at", "deleted_at")

                    if self.has_field(entity, deleted_at_field):
                        self._apply_soft_delete(entity, context.entity_type)

            # Mark as processed
            context.set_context_value("soft_delete_processed", True)

        # Handle single delete operation
        elif self._should_soft_delete(context):
            self._apply_soft_delete(context.entity, context.entity_type)

            # Mark as processed
            context.set_context_value("soft_delete_processed", True)

        return await next_interceptor(context)
