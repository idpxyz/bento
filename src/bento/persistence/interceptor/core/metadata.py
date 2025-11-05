"""Entity metadata registry for interceptor configuration.

This module provides a centralized registry for managing entity-specific
interceptor configuration and field mappings.
"""

from typing import Any


class EntityMetadataRegistry:
    """Registry for entity metadata and interceptor configuration.

    This registry allows entities to declare which interceptors should be enabled
    and how fields should be mapped (e.g., custom audit field names).

    Example:
        ```python
        # Register entity metadata
        EntityMetadataRegistry.register(
            UserEntity,
            features={"audit": True, "soft_delete": True},
            fields={
                "audit_fields": {
                    "created_at": "creation_time",
                    "updated_at": "modification_time"
                }
            }
        )

        # Check if feature is enabled
        is_enabled = EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")

        # Get field name
        field = EntityMetadataRegistry.get_field_name(
            UserEntity, "audit_fields", "created_at"
        )  # Returns: "creation_time"
        ```
    """

    _metadata: dict[type, dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        entity_type: type,
        *,
        features: dict[str, bool] | None = None,
        fields: dict[str, dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Register metadata for an entity type.

        Args:
            entity_type: Entity class to register
            features: Feature flags (e.g., {"audit": True})
            fields: Field name mappings (e.g., {"audit_fields": {"created_at": "custom_name"}})
            **kwargs: Additional metadata
        """
        if entity_type not in cls._metadata:
            cls._metadata[entity_type] = {}

        metadata = cls._metadata[entity_type]

        if features:
            if "features" not in metadata:
                metadata["features"] = {}
            metadata["features"].update(features)

        if fields:
            if "fields" not in metadata:
                metadata["fields"] = {}
            for category, field_map in fields.items():
                if category not in metadata["fields"]:
                    metadata["fields"][category] = {}
                metadata["fields"][category].update(field_map)

        # Store additional metadata
        for key, value in kwargs.items():
            metadata[key] = value

    @classmethod
    def is_feature_enabled(cls, entity_type: type, feature_name: str) -> bool:
        """Check if a feature is enabled for an entity type.

        Args:
            entity_type: Entity class
            feature_name: Feature identifier

        Returns:
            True if feature is enabled, False otherwise (default: True)
        """
        if entity_type not in cls._metadata:
            return True  # Default: all features enabled

        features = cls._metadata[entity_type].get("features", {})
        return features.get(feature_name, True)

    @classmethod
    def get_field_name(cls, entity_type: type, field_category: str, field_name: str) -> str:
        """Get the actual field name for an entity.

        Allows entities to use custom field names while maintaining standard
        interceptor interfaces.

        Args:
            entity_type: Entity class
            field_category: Category of field (e.g., "audit_fields")
            field_name: Standard field name

        Returns:
            Actual field name (or original if no mapping exists)
        """
        if entity_type not in cls._metadata:
            return field_name

        fields = cls._metadata[entity_type].get("fields", {})
        category_fields = fields.get(field_category, {})
        return category_fields.get(field_name, field_name)

    @classmethod
    def get_metadata(cls, entity_type: type, key: str, default: Any = None) -> Any:
        """Get arbitrary metadata for an entity.

        Args:
            entity_type: Entity class
            key: Metadata key
            default: Default value if not found

        Returns:
            Metadata value or default
        """
        if entity_type not in cls._metadata:
            return default
        return cls._metadata[entity_type].get(key, default)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered metadata.

        Useful for testing.
        """
        cls._metadata.clear()

    @classmethod
    def clear_entity(cls, entity_type: type) -> None:
        """Clear metadata for a specific entity.

        Args:
            entity_type: Entity class to clear
        """
        if entity_type in cls._metadata:
            del cls._metadata[entity_type]
