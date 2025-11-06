"""Unit tests for EntityMetadataRegistry.

Tests cover:
- Entity registration
- Feature flag checking
- Field name mapping
- Metadata retrieval
- Clearing metadata
- Multiple entity types
"""

import pytest

from bento.persistence.interceptor.core.metadata import EntityMetadataRegistry

# ==================== Test Entities ====================


class UserEntity:
    """Test user entity."""

    pass


class ProductEntity:
    """Test product entity."""

    pass


class OrderEntity:
    """Test order entity."""

    pass


# ==================== Fixtures ====================


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean up EntityMetadataRegistry after each test."""
    yield
    EntityMetadataRegistry.clear()


# ==================== Registration Tests ====================


def test_register_entity_with_features():
    """Test registering entity with feature flags."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": True, "soft_delete": True},
    )

    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "soft_delete")


def test_register_entity_with_fields():
    """Test registering entity with field mappings."""
    EntityMetadataRegistry.register(
        UserEntity,
        fields={
            "audit_fields": {
                "created_at": "creation_time",
                "updated_at": "modification_time",
            }
        },
    )

    field_name = EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "created_at")
    assert field_name == "creation_time"


def test_register_entity_with_custom_metadata():
    """Test registering entity with custom metadata via kwargs."""
    EntityMetadataRegistry.register(
        UserEntity,
        custom_field="custom_value",
        another_field=123,
    )

    assert EntityMetadataRegistry.get_metadata(UserEntity, "custom_field") == "custom_value"
    assert EntityMetadataRegistry.get_metadata(UserEntity, "another_field") == 123


def test_register_entity_multiple_times_updates():
    """Test that registering same entity multiple times updates metadata."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": True},
    )

    EntityMetadataRegistry.register(
        UserEntity,
        features={"soft_delete": True},
    )

    # Both features should be present
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "soft_delete")


def test_register_multiple_entities():
    """Test registering multiple different entities."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": True},
    )

    EntityMetadataRegistry.register(
        ProductEntity,
        features={"audit": False},
    )

    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert not EntityMetadataRegistry.is_feature_enabled(ProductEntity, "audit")


# ==================== Feature Flag Tests ====================


def test_is_feature_enabled_default_true():
    """Test that features default to enabled for unregistered entities."""
    # No registration
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "soft_delete")


def test_is_feature_enabled_explicit_true():
    """Test explicitly enabled feature."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": True},
    )

    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")


def test_is_feature_enabled_explicit_false():
    """Test explicitly disabled feature."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": False},
    )

    assert not EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")


def test_is_feature_enabled_unspecified_defaults_true():
    """Test that unspecified features default to True."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": True},  # Only specify audit
    )

    # soft_delete not specified, should default to True
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "soft_delete")


def test_multiple_features():
    """Test multiple feature flags."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={
            "audit": True,
            "soft_delete": False,
            "optimistic_lock": True,
        },
    )

    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert not EntityMetadataRegistry.is_feature_enabled(UserEntity, "soft_delete")
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "optimistic_lock")


# ==================== Field Name Mapping Tests ====================


def test_get_field_name_with_mapping():
    """Test getting field name with custom mapping."""
    EntityMetadataRegistry.register(
        UserEntity,
        fields={
            "audit_fields": {
                "created_at": "creation_timestamp",
                "updated_at": "modification_timestamp",
            }
        },
    )

    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "created_at")
        == "creation_timestamp"
    )
    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "updated_at")
        == "modification_timestamp"
    )


def test_get_field_name_without_mapping():
    """Test that unmapped fields return original name."""
    EntityMetadataRegistry.register(
        UserEntity,
        fields={
            "audit_fields": {
                "created_at": "creation_timestamp",
            }
        },
    )

    # updated_at not mapped, should return original
    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "updated_at")
        == "updated_at"
    )


def test_get_field_name_unregistered_entity():
    """Test getting field name for unregistered entity returns original."""
    # No registration
    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "created_at")
        == "created_at"
    )


def test_get_field_name_nonexistent_category():
    """Test getting field name from nonexistent category returns original."""
    EntityMetadataRegistry.register(
        UserEntity,
        fields={
            "audit_fields": {
                "created_at": "creation_timestamp",
            }
        },
    )

    # soft_delete_fields not defined
    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "soft_delete_fields", "deleted_at")
        == "deleted_at"
    )


def test_multiple_field_categories():
    """Test multiple field categories."""
    EntityMetadataRegistry.register(
        UserEntity,
        fields={
            "audit_fields": {
                "created_at": "creation_time",
                "updated_at": "modification_time",
            },
            "soft_delete_fields": {
                "is_deleted": "is_archived",
                "deleted_at": "archived_at",
            },
        },
    )

    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "created_at")
        == "creation_time"
    )
    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "soft_delete_fields", "is_deleted")
        == "is_archived"
    )


# ==================== Metadata Retrieval Tests ====================


def test_get_metadata_existing_key():
    """Test getting existing metadata."""
    EntityMetadataRegistry.register(
        UserEntity,
        custom_key="custom_value",
    )

    assert EntityMetadataRegistry.get_metadata(UserEntity, "custom_key") == "custom_value"


def test_get_metadata_nonexistent_key():
    """Test getting nonexistent metadata returns default."""
    EntityMetadataRegistry.register(
        UserEntity,
        custom_key="custom_value",
    )

    assert EntityMetadataRegistry.get_metadata(UserEntity, "other_key") is None


def test_get_metadata_with_default():
    """Test getting nonexistent metadata with custom default."""
    assert (
        EntityMetadataRegistry.get_metadata(UserEntity, "nonexistent", default="default_value")
        == "default_value"
    )


def test_get_metadata_unregistered_entity():
    """Test getting metadata from unregistered entity returns default."""
    # No registration
    assert EntityMetadataRegistry.get_metadata(UserEntity, "any_key") is None


def test_get_metadata_features():
    """Test getting features metadata."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": True, "soft_delete": False},
    )

    features = EntityMetadataRegistry.get_metadata(UserEntity, "features")
    assert features == {"audit": True, "soft_delete": False}


def test_get_metadata_fields():
    """Test getting fields metadata."""
    EntityMetadataRegistry.register(
        UserEntity,
        fields={"audit_fields": {"created_at": "creation_time"}},
    )

    fields = EntityMetadataRegistry.get_metadata(UserEntity, "fields")
    assert fields == {"audit_fields": {"created_at": "creation_time"}}


# ==================== Clear Tests ====================


def test_clear_all_metadata():
    """Test clearing all metadata."""
    EntityMetadataRegistry.register(UserEntity, features={"audit": True})
    EntityMetadataRegistry.register(ProductEntity, features={"audit": True})

    EntityMetadataRegistry.clear()

    # Both should return defaults (True) now
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert EntityMetadataRegistry.is_feature_enabled(ProductEntity, "audit")


def test_clear_specific_entity():
    """Test clearing specific entity metadata."""
    EntityMetadataRegistry.register(UserEntity, features={"audit": False})
    EntityMetadataRegistry.register(ProductEntity, features={"audit": False})

    EntityMetadataRegistry.clear_entity(UserEntity)

    # UserEntity should return default (True), ProductEntity should still be False
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert not EntityMetadataRegistry.is_feature_enabled(ProductEntity, "audit")


def test_clear_nonexistent_entity():
    """Test clearing nonexistent entity doesn't raise error."""
    # Should not raise
    EntityMetadataRegistry.clear_entity(UserEntity)


# ==================== Complex Scenarios ====================


def test_full_entity_configuration():
    """Test registering entity with all types of metadata."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={
            "audit": True,
            "soft_delete": True,
            "optimistic_lock": False,
        },
        fields={
            "audit_fields": {
                "created_at": "creation_time",
                "created_by": "creator",
                "updated_at": "modification_time",
                "updated_by": "modifier",
            },
            "soft_delete_fields": {
                "is_deleted": "is_archived",
                "deleted_at": "archived_at",
                "deleted_by": "archiver",
            },
        },
        custom_metadata="some_value",
        another_field={"nested": "data"},
    )

    # Check features
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "soft_delete")
    assert not EntityMetadataRegistry.is_feature_enabled(UserEntity, "optimistic_lock")

    # Check field mappings
    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "created_at")
        == "creation_time"
    )
    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "soft_delete_fields", "is_deleted")
        == "is_archived"
    )

    # Check custom metadata
    assert EntityMetadataRegistry.get_metadata(UserEntity, "custom_metadata") == "some_value"
    assert EntityMetadataRegistry.get_metadata(UserEntity, "another_field") == {"nested": "data"}


def test_incremental_updates():
    """Test incremental updates to entity metadata."""
    # First registration
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": True},
    )

    # Second registration adds more features
    EntityMetadataRegistry.register(
        UserEntity,
        features={"soft_delete": False},
    )

    # Third registration adds field mappings
    EntityMetadataRegistry.register(
        UserEntity,
        fields={"audit_fields": {"created_at": "creation_time"}},
    )

    # All should be present
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert not EntityMetadataRegistry.is_feature_enabled(UserEntity, "soft_delete")
    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "created_at")
        == "creation_time"
    )


def test_isolated_entity_metadata():
    """Test that entity metadata is isolated."""
    EntityMetadataRegistry.register(
        UserEntity,
        features={"audit": True},
        fields={"audit_fields": {"created_at": "user_created_at"}},
    )

    EntityMetadataRegistry.register(
        ProductEntity,
        features={"audit": False},
        fields={"audit_fields": {"created_at": "product_created_at"}},
    )

    # Each should have its own metadata
    assert EntityMetadataRegistry.is_feature_enabled(UserEntity, "audit")
    assert not EntityMetadataRegistry.is_feature_enabled(ProductEntity, "audit")

    assert (
        EntityMetadataRegistry.get_field_name(UserEntity, "audit_fields", "created_at")
        == "user_created_at"
    )
    assert (
        EntityMetadataRegistry.get_field_name(ProductEntity, "audit_fields", "created_at")
        == "product_created_at"
    )
