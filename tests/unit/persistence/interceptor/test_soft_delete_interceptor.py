"""Unit tests for SoftDeleteInterceptor.

Tests cover:
- Soft delete marking (is_deleted flag)
- Deletion timestamp and actor tracking (deleted_at, deleted_by)
- Batch soft delete operations
- Custom field mapping via EntityMetadataRegistry
- Priority ordering
- Preventing duplicate soft delete
- Non-soft-deletable entities
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from bento.persistence.interceptor import (
    InterceptorContext,
    OperationType,
    SoftDeleteInterceptor,
)
from bento.persistence.interceptor.core.metadata import EntityMetadataRegistry

# ==================== Test Entities ====================


class SoftDeletableEntity:
    """Test entity with standard soft delete fields."""

    def __init__(self) -> None:
        self.id = "test-001"
        self.name = "Test"
        self.deleted_at: datetime | None = None
        self.deleted_by: str | None = None

    @property
    def is_deleted(self) -> bool:
        """Computed property: check if deleted based on deleted_at."""
        return self.deleted_at is not None


class CustomSoftDeleteEntity:
    """Test entity with custom soft delete field names."""

    def __init__(self) -> None:
        self.id = "test-002"
        self.name = "Custom"
        self.archived_at: datetime | None = None
        self.archived_by: str | None = None

    @property
    def is_archived(self) -> bool:
        """Computed property: check if archived based on archived_at."""
        return self.archived_at is not None


class NonSoftDeletableEntity:
    """Test entity without soft delete fields."""

    def __init__(self) -> None:
        self.id = "test-003"
        self.name = "NoSoftDelete"


class PartialSoftDeleteEntity:
    """Test entity with only deleted_at field (no deleted_by)."""

    def __init__(self) -> None:
        self.id = "test-004"
        self.name = "Partial"
        self.deleted_at: datetime | None = None
        # Missing: deleted_by


# ==================== Fixtures ====================


@pytest.fixture
def mock_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def soft_delete_interceptor():
    """Create soft delete interceptor with default actor."""
    return SoftDeleteInterceptor(actor="test@example.com")


@pytest.fixture
def system_interceptor():
    """Create soft delete interceptor with system actor."""
    return SoftDeleteInterceptor(actor="system")


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean up EntityMetadataRegistry after each test."""
    yield
    EntityMetadataRegistry.clear()


# ==================== Priority Tests ====================


def test_soft_delete_interceptor_priority(soft_delete_interceptor):
    """Test that soft delete interceptor has NORMAL priority."""
    from bento.persistence.interceptor import InterceptorPriority

    assert soft_delete_interceptor.priority == InterceptorPriority.NORMAL


def test_soft_delete_interceptor_type(soft_delete_interceptor):
    """Test interceptor type identifier."""
    assert soft_delete_interceptor.interceptor_type == "soft_delete"


# ==================== DELETE Operation Tests ====================


@pytest.mark.asyncio
async def test_delete_sets_is_deleted(soft_delete_interceptor, mock_session):
    """Test that DELETE operation sets is_deleted to True."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    assert entity.is_deleted is True


@pytest.mark.asyncio
async def test_delete_sets_deleted_at(soft_delete_interceptor, mock_session):
    """Test that DELETE operation sets deleted_at timestamp."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    before_time = datetime.now(UTC)

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    after_time = datetime.now(UTC)

    assert entity.deleted_at is not None
    assert before_time <= entity.deleted_at <= after_time


@pytest.mark.asyncio
async def test_delete_sets_deleted_by(soft_delete_interceptor, mock_session):
    """Test that DELETE operation sets deleted_by to actor."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="deleter@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    assert entity.deleted_by == "test@example.com"  # Uses interceptor's actor


@pytest.mark.asyncio
async def test_delete_with_system_actor(system_interceptor, mock_session):
    """Test DELETE operation with system actor."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="admin@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await system_interceptor.before_operation(context, next_interceptor)

    assert entity.is_deleted is True
    assert entity.deleted_by == "system"


# ==================== Already Deleted Tests ====================


@pytest.mark.asyncio
async def test_delete_already_deleted_entity_skipped(soft_delete_interceptor, mock_session):
    """Test that already deleted entity is not re-deleted."""
    entity = SoftDeletableEntity()
    # Mark as already deleted by setting deleted_at
    entity.deleted_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    entity.deleted_by = "original@example.com"

    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    # Fields should remain unchanged
    assert entity.is_deleted is True
    assert entity.deleted_at == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert entity.deleted_by == "original@example.com"


# ==================== Non-DELETE Operations ====================


@pytest.mark.asyncio
async def test_create_operation_ignored(soft_delete_interceptor, mock_session):
    """Test that CREATE operations don't trigger soft delete."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    assert entity.is_deleted is False
    assert entity.deleted_at is None
    assert entity.deleted_by is None


@pytest.mark.asyncio
async def test_update_operation_ignored(soft_delete_interceptor, mock_session):
    """Test that UPDATE operations don't trigger soft delete."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    assert entity.is_deleted is False
    assert entity.deleted_at is None
    assert entity.deleted_by is None


# ==================== Batch Operation Tests ====================


@pytest.mark.asyncio
async def test_batch_delete_all_entities(soft_delete_interceptor, mock_session):
    """Test that BATCH_DELETE soft deletes all entities."""
    entities = [SoftDeletableEntity() for _ in range(5)]

    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.BATCH_DELETE,
        entities=entities,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    for entity in entities:
        assert entity.is_deleted is True
        assert entity.deleted_at is not None
        assert entity.deleted_by == "test@example.com"


@pytest.mark.asyncio
async def test_batch_delete_mixed_deleted_states(soft_delete_interceptor, mock_session):
    """Test BATCH_DELETE with mix of deleted and non-deleted entities."""
    entities = []

    # Create 3 non-deleted entities
    for _ in range(3):
        entities.append(SoftDeletableEntity())

    # Create 2 already-deleted entities (mark by setting deleted_at)
    for _ in range(2):
        entity = SoftDeletableEntity()
        entity.deleted_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        entity.deleted_by = "previous@example.com"
        entities.append(entity)

    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.BATCH_DELETE,
        entities=entities,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    # All should be marked as deleted
    for entity in entities:
        assert entity.is_deleted is True

    # First 3 should have new deletion info
    for i in range(3):
        assert entities[i].deleted_by == "test@example.com"

    # Last 2 should retain original deletion info
    for i in range(3, 5):
        assert entities[i].deleted_at == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert entities[i].deleted_by == "previous@example.com"


@pytest.mark.asyncio
async def test_batch_delete_empty_list(soft_delete_interceptor, mock_session):
    """Test that BATCH_DELETE handles empty entity list."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.BATCH_DELETE,
        entities=[],
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await soft_delete_interceptor.before_operation(context, next_interceptor)


@pytest.mark.asyncio
async def test_batch_delete_none_entities(soft_delete_interceptor, mock_session):
    """Test that BATCH_DELETE handles None entities gracefully."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.BATCH_DELETE,
        entities=None,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await soft_delete_interceptor.before_operation(context, next_interceptor)


# ==================== Custom Field Mapping Tests ====================


@pytest.mark.asyncio
async def test_custom_soft_delete_fields(soft_delete_interceptor, mock_session):
    """Test soft delete with custom field names via EntityMetadataRegistry."""
    # Register custom field mappings
    EntityMetadataRegistry.register(
        CustomSoftDeleteEntity,
        fields={
            "soft_delete_fields": {
                "is_deleted": "is_archived",
                "deleted_at": "archived_at",
                "deleted_by": "archived_by",
            }
        },
    )

    entity = CustomSoftDeleteEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=CustomSoftDeleteEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    # Custom fields should be set
    assert entity.is_archived is True
    assert entity.archived_at is not None
    assert entity.archived_by == "test@example.com"


@pytest.mark.asyncio
async def test_partial_soft_delete_fields(soft_delete_interceptor, mock_session):
    """Test entity with only some soft delete fields present."""
    entity = PartialSoftDeleteEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=PartialSoftDeleteEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await soft_delete_interceptor.before_operation(context, next_interceptor)

    # Only existing field (deleted_at) should be set
    assert hasattr(entity, "deleted_at")
    assert entity.deleted_at is not None
    assert not hasattr(entity, "deleted_by")


# ==================== Non-Soft-Deletable Entity Tests ====================


@pytest.mark.asyncio
async def test_non_soft_deletable_entity_ignored(soft_delete_interceptor, mock_session):
    """Test that entities without is_deleted field are not soft deleted."""
    entity = NonSoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=NonSoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await soft_delete_interceptor.before_operation(context, next_interceptor)

    # Entity should remain unchanged
    assert not hasattr(entity, "is_deleted")
    assert not hasattr(entity, "deleted_at")
    assert not hasattr(entity, "deleted_by")


# ==================== Context Tests ====================


@pytest.mark.asyncio
async def test_null_entity_context(soft_delete_interceptor, mock_session):
    """Test that null entity in context is handled gracefully."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=None,  # No entity
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await soft_delete_interceptor.before_operation(context, next_interceptor)


@pytest.mark.asyncio
async def test_soft_delete_processed_flag(soft_delete_interceptor, mock_session):
    """Test that soft delete sets processed flag in context."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    # Check processed flag is set
    assert context.get_context_value("soft_delete_processed", False) is True


@pytest.mark.asyncio
async def test_already_processed_skipped(soft_delete_interceptor, mock_session):
    """Test that already processed soft delete is skipped."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    # Mark as already processed
    context.set_context_value("soft_delete_processed", True)

    async def next_interceptor(ctx):
        return None

    await soft_delete_interceptor.before_operation(context, next_interceptor)

    # Entity should not be modified
    assert entity.is_deleted is False
    assert entity.deleted_at is None
    assert entity.deleted_by is None


# ==================== Configuration Tests ====================


def test_is_enabled_in_config():
    """Test is_enabled_in_config method."""

    class MockConfig:
        enable_soft_delete = True

    assert SoftDeleteInterceptor.is_enabled_in_config(MockConfig())


def test_is_disabled_in_config():
    """Test is_enabled_in_config with disabled config."""

    class MockConfig:
        enable_soft_delete = False

    assert not SoftDeleteInterceptor.is_enabled_in_config(MockConfig())


def test_is_enabled_default():
    """Test is_enabled_in_config with missing attribute (default True)."""

    class MockConfig:
        pass

    # Default should be True
    assert SoftDeleteInterceptor.is_enabled_in_config(MockConfig())


# ==================== Next Interceptor Tests ====================


@pytest.mark.asyncio
async def test_calls_next_interceptor(soft_delete_interceptor, mock_session):
    """Test that the interceptor calls the next interceptor in chain."""
    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    next_called = False

    async def next_interceptor(ctx):
        nonlocal next_called
        next_called = True
        return "next_result"

    result = await soft_delete_interceptor.before_operation(context, next_interceptor)

    assert next_called
    assert result == "next_result"


# ==================== Actor Tests ====================


@pytest.mark.asyncio
async def test_default_actor_is_system(mock_session):
    """Test that default actor is 'system' when not specified."""
    interceptor = SoftDeleteInterceptor()  # No actor specified

    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="unused@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await interceptor.before_operation(context, next_interceptor)

    assert entity.is_deleted is True
    assert entity.deleted_by == "system"


@pytest.mark.asyncio
async def test_actor_from_interceptor_init(mock_session):
    """Test that actor from interceptor initialization is used."""
    interceptor = SoftDeleteInterceptor(actor="custom@example.com")

    entity = SoftDeletableEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SoftDeletableEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="context@example.com",  # Different actor in context
    )

    async def next_interceptor(ctx):
        return None

    await interceptor.before_operation(context, next_interceptor)

    # Should use interceptor's actor, not context's actor
    assert entity.deleted_by == "custom@example.com"
