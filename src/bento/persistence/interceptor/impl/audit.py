"""Audit interceptor for automatic timestamp and user tracking.

This interceptor automatically maintains audit fields like:
- created_at, created_by (on creation)
- updated_at, updated_by (on updates)
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, ClassVar, TypeVar

from ..core import (
    Interceptor,
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)
from ..core.metadata import EntityMetadataRegistry

T = TypeVar("T")


class AuditInterceptor(Interceptor[T]):
    """Audit interceptor for automatic timestamp and user tracking.

    Automatically maintains audit fields:
    - created_at, created_by: Set on entity creation
    - updated_at, updated_by: Set on entity updates

    Priority: NORMAL (200)

    Configuration:
        Enable/disable per entity via EntityMetadataRegistry

    Field Mapping:
        Default fields can be customized via EntityMetadataRegistry:
        ```python
        EntityMetadataRegistry.register(
            MyEntity,
            fields={
                "audit_fields": {
                    "created_at": "creation_time",
                    "updated_at": "modification_time"
                }
            }
        )
        ```
    """

    interceptor_type: ClassVar[str] = "audit"

    def __init__(self, actor: str | None = None) -> None:
        """Initialize audit interceptor.

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
        return getattr(config, "enable_audit", True)

    def _get_audit_fields(self, entity_type: type[T]) -> dict[str, str]:
        """Get audit field mappings for entity type.

        Args:
            entity_type: Entity class

        Returns:
            Dictionary mapping standard field names to actual field names
        """
        # Try to get from metadata registry
        # Fields are stored under "fields" key, then "audit_fields" sub-key
        all_fields = EntityMetadataRegistry.get_metadata(entity_type, "fields")
        if all_fields and isinstance(all_fields, dict):
            audit_fields = all_fields.get("audit_fields")
            if audit_fields:
                return audit_fields

        # Default field mapping
        return {
            "created_at": "created_at",
            "created_by": "created_by",
            "updated_at": "updated_at",
            "updated_by": "updated_by",
        }

    def _should_audit(self, context: InterceptorContext[T]) -> bool:
        """Check if audit should be applied.

        Args:
            context: Interceptor context

        Returns:
            True if audit should be applied
        """
        if not context.entity:
            return False

        return self.is_enabled_for_entity(context.entity_type)

    def _apply_create_audit(self, entity: Any, entity_type: type[T]) -> None:
        """Apply audit fields for entity creation.

        Args:
            entity: Entity instance
            entity_type: Entity class
        """
        now = datetime.now(UTC)
        actor = self._actor

        fields = self._get_audit_fields(entity_type)

        # Set creation fields
        created_at_field = fields.get("created_at", "created_at")
        created_by_field = fields.get("created_by", "created_by")

        if self.has_field(entity, created_at_field):
            self.set_field_value(entity, created_at_field, now)

        if self.has_field(entity, created_by_field):
            self.set_field_value(entity, created_by_field, actor)

        # Also set update fields on creation
        updated_at_field = fields.get("updated_at", "updated_at")
        updated_by_field = fields.get("updated_by", "updated_by")

        if self.has_field(entity, updated_at_field):
            self.set_field_value(entity, updated_at_field, now)

        if self.has_field(entity, updated_by_field):
            self.set_field_value(entity, updated_by_field, actor)

    def _apply_update_audit(self, entity: Any, entity_type: type[T]) -> None:
        """Apply audit fields for entity update.

        Args:
            entity: Entity instance
            entity_type: Entity class
        """
        now = datetime.now(UTC)
        actor = self._actor

        fields = self._get_audit_fields(entity_type)

        # Set update fields
        updated_at_field = fields.get("updated_at", "updated_at")
        updated_by_field = fields.get("updated_by", "updated_by")

        if self.has_field(entity, updated_at_field):
            self.set_field_value(entity, updated_at_field, now)

        if self.has_field(entity, updated_by_field):
            self.set_field_value(entity, updated_by_field, actor)

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]],
    ) -> Any:
        """Process before operation, applying audit fields.

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
                    for entity in context.entities:
                        if self.is_enabled_for_entity(context.entity_type):
                            self._apply_create_audit(entity, context.entity_type)

                elif context.operation == OperationType.BATCH_UPDATE:
                    for entity in context.entities:
                        if self.is_enabled_for_entity(context.entity_type):
                            self._apply_update_audit(entity, context.entity_type)

        # Handle single entity operations
        else:
            if self._should_audit(context):
                if context.operation == OperationType.CREATE:
                    self._apply_create_audit(context.entity, context.entity_type)

                elif context.operation == OperationType.UPDATE:
                    self._apply_update_audit(context.entity, context.entity_type)

        return await next_interceptor(context)
