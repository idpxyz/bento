"""Unit tests for AuditInterceptor.

Tests cover:
- Automatic creation timestamp and user tracking (created_at, created_by)
- Automatic update timestamp and user tracking (updated_at, updated_by)
- Batch operation support
- Custom field mapping via EntityMetadataRegistry
- Priority ordering
- Entity feature enablement
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from bento.persistence.interceptor import (
    AuditInterceptor,
    InterceptorContext,
    OperationType,
)
from bento.persistence.interceptor.core.metadata import EntityMetadataRegistry

# ==================== Test Entities ====================


class AuditedEntity:
    """Test entity with standard audit fields."""

    def __init__(self) -> None:
        self.id = "test-001"
        self.name = "Test"
        self.created_at = None
        self.created_by = None
        self.updated_at = None
        self.updated_by = None


class CustomAuditEntity:
    """Test entity with custom audit field names."""

    def __init__(self) -> None:
        self.id = "test-002"
        self.name = "Custom"
        self.creation_time = None
        self.creator = None
        self.modification_time = None
        self.modifier = None


class NonAuditedEntity:
    """Test entity without audit fields."""

    def __init__(self) -> None:
        self.id = "test-003"
        self.name = "NoAudit"


# ==================== Fixtures ====================


@pytest.fixture
def mock_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def audit_interceptor():
    """Create audit interceptor with default actor."""
    return AuditInterceptor(actor="test@example.com")


@pytest.fixture
def system_interceptor():
    """Create audit interceptor with system actor."""
    return AuditInterceptor(actor="system")


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean up EntityMetadataRegistry after each test."""
    yield
    EntityMetadataRegistry.clear()


# ==================== Priority Tests ====================


def test_audit_interceptor_priority(audit_interceptor):
    """Test that audit interceptor has NORMAL priority."""
    from bento.persistence.interceptor import InterceptorPriority

    assert audit_interceptor.priority == InterceptorPriority.NORMAL


def test_audit_interceptor_type(audit_interceptor):
    """Test interceptor type identifier."""
    assert audit_interceptor.interceptor_type == "audit"


# ==================== CREATE Operation Tests ====================


@pytest.mark.asyncio
async def test_create_sets_created_at(audit_interceptor, mock_session):
    """Test that CREATE operation sets created_at timestamp."""
    entity = AuditedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    before_time = datetime.now(UTC)

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    after_time = datetime.now(UTC)

    assert entity.created_at is not None
    assert before_time <= entity.created_at <= after_time


@pytest.mark.asyncio
async def test_create_sets_created_by(audit_interceptor, mock_session):
    """Test that CREATE operation sets created_by to actor."""
    entity = AuditedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="john@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    assert entity.created_by == "test@example.com"  # Uses interceptor's actor


@pytest.mark.asyncio
async def test_create_also_sets_updated_fields(audit_interceptor, mock_session):
    """Test that CREATE operation also sets updated_at and updated_by."""
    entity = AuditedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    assert entity.updated_at is not None
    assert entity.updated_by == "test@example.com"
    # created_at and updated_at should be the same
    assert entity.created_at == entity.updated_at


@pytest.mark.asyncio
async def test_create_with_system_actor(system_interceptor, mock_session):
    """Test CREATE operation with system actor."""
    entity = AuditedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="admin@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await system_interceptor.before_operation(context, next_interceptor)

    assert entity.created_by == "system"
    assert entity.updated_by == "system"


# ==================== UPDATE Operation Tests ====================


@pytest.mark.asyncio
async def test_update_sets_updated_at(audit_interceptor, mock_session):
    """Test that UPDATE operation sets updated_at timestamp."""
    entity = AuditedEntity()
    entity.created_at = datetime.now(UTC)
    entity.created_by = "original@example.com"

    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )

    before_time = datetime.now(UTC)

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    after_time = datetime.now(UTC)

    assert entity.updated_at is not None
    assert before_time <= entity.updated_at <= after_time


@pytest.mark.asyncio
async def test_update_sets_updated_by(audit_interceptor, mock_session):
    """Test that UPDATE operation sets updated_by to actor."""
    entity = AuditedEntity()
    entity.created_at = datetime.now(UTC)
    entity.created_by = "original@example.com"

    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="updater@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    assert entity.updated_by == "test@example.com"  # Uses interceptor's actor


@pytest.mark.asyncio
async def test_update_does_not_modify_created_fields(audit_interceptor, mock_session):
    """Test that UPDATE operation does not modify created_at and created_by."""
    entity = AuditedEntity()
    original_created_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    original_created_by = "original@example.com"
    entity.created_at = original_created_at
    entity.created_by = original_created_by

    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    assert entity.created_at == original_created_at
    assert entity.created_by == original_created_by


# ==================== Batch Operation Tests ====================


@pytest.mark.asyncio
async def test_batch_create_all_entities(audit_interceptor, mock_session):
    """Test that BATCH_CREATE sets audit fields on all entities."""
    entities = [AuditedEntity() for _ in range(5)]

    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.BATCH_CREATE,
        entities=entities,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    for entity in entities:
        assert entity.created_at is not None
        assert entity.created_by == "test@example.com"
        assert entity.updated_at is not None
        assert entity.updated_by == "test@example.com"


@pytest.mark.asyncio
async def test_batch_update_all_entities(audit_interceptor, mock_session):
    """Test that BATCH_UPDATE sets updated fields on all entities."""
    entities = []
    original_created_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    for i in range(5):
        entity = AuditedEntity()
        entity.created_at = original_created_at
        entity.created_by = "original@example.com"
        entities.append(entity)

    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.BATCH_UPDATE,
        entities=entities,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    for entity in entities:
        assert entity.updated_at is not None
        assert entity.updated_by == "test@example.com"
        # created fields should not change
        assert entity.created_at == original_created_at
        assert entity.created_by == "original@example.com"


@pytest.mark.asyncio
async def test_batch_create_empty_list(audit_interceptor, mock_session):
    """Test that BATCH_CREATE handles empty entity list."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.BATCH_CREATE,
        entities=[],
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await audit_interceptor.before_operation(context, next_interceptor)


@pytest.mark.asyncio
async def test_batch_create_none_entities(audit_interceptor, mock_session):
    """Test that BATCH_CREATE handles None entities gracefully."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.BATCH_CREATE,
        entities=None,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await audit_interceptor.before_operation(context, next_interceptor)


# ==================== Custom Field Mapping Tests ====================


@pytest.mark.asyncio
async def test_custom_audit_fields(audit_interceptor, mock_session):
    """Test audit with custom field names via EntityMetadataRegistry."""
    # Register custom field mappings
    EntityMetadataRegistry.register(
        CustomAuditEntity,
        fields={
            "audit_fields": {
                "created_at": "creation_time",
                "created_by": "creator",
                "updated_at": "modification_time",
                "updated_by": "modifier",
            }
        },
    )

    entity = CustomAuditEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=CustomAuditEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    # Custom fields should be set
    assert entity.creation_time is not None
    assert entity.creator == "test@example.com"
    assert entity.modification_time is not None
    assert entity.modifier == "test@example.com"


@pytest.mark.asyncio
async def test_partial_audit_fields(audit_interceptor, mock_session):
    """Test entity with only some audit fields present."""

    class PartialAuditEntity:
        def __init__(self):
            self.id = "partial-001"
            self.created_at = None
            # Missing: created_by, updated_at, updated_by

    entity = PartialAuditEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=PartialAuditEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await audit_interceptor.before_operation(context, next_interceptor)

    # Only existing field should be set
    assert entity.created_at is not None
    assert not hasattr(entity, "created_by")


# ==================== Non-Audited Entity Tests ====================


@pytest.mark.asyncio
async def test_non_audited_entity_ignored(audit_interceptor, mock_session):
    """Test that entities without audit fields are handled gracefully."""
    entity = NonAuditedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=NonAuditedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await audit_interceptor.before_operation(context, next_interceptor)

    # Entity should remain unchanged
    assert not hasattr(entity, "created_at")
    assert not hasattr(entity, "created_by")


# ==================== DELETE Operation Tests ====================


@pytest.mark.asyncio
async def test_delete_operation_ignored(audit_interceptor, mock_session):
    """Test that DELETE operations don't trigger audit updates."""
    entity = AuditedEntity()
    entity.created_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    entity.created_by = "original@example.com"
    entity.updated_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    entity.updated_by = "original@example.com"

    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    # Audit fields should not change
    assert entity.updated_at == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert entity.updated_by == "original@example.com"


# ==================== READ Operation Tests ====================


@pytest.mark.asyncio
async def test_read_operation_ignored(audit_interceptor, mock_session):
    """Test that READ operations don't trigger audit updates."""
    entity = AuditedEntity()

    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.READ,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await audit_interceptor.before_operation(context, next_interceptor)

    # No audit fields should be set
    assert entity.created_at is None
    assert entity.created_by is None
    assert entity.updated_at is None
    assert entity.updated_by is None


# ==================== Context Null Tests ====================


@pytest.mark.asyncio
async def test_null_entity_context(audit_interceptor, mock_session):
    """Test that null entity in context is handled gracefully."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.CREATE,
        entity=None,  # No entity
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await audit_interceptor.before_operation(context, next_interceptor)


# ==================== Configuration Tests ====================


def test_is_enabled_in_config():
    """Test is_enabled_in_config method."""

    class MockConfig:
        enable_audit = True

    assert AuditInterceptor.is_enabled_in_config(MockConfig())


def test_is_disabled_in_config():
    """Test is_enabled_in_config with disabled config."""

    class MockConfig:
        enable_audit = False

    assert not AuditInterceptor.is_enabled_in_config(MockConfig())


def test_is_enabled_default():
    """Test is_enabled_in_config with missing attribute (default True)."""

    class MockConfig:
        pass

    # Default should be True
    assert AuditInterceptor.is_enabled_in_config(MockConfig())


# ==================== Next Interceptor Tests ====================


@pytest.mark.asyncio
async def test_calls_next_interceptor(audit_interceptor, mock_session):
    """Test that the interceptor calls the next interceptor in chain."""
    entity = AuditedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    next_called = False

    async def next_interceptor(ctx):
        nonlocal next_called
        next_called = True
        return "next_result"

    result = await audit_interceptor.before_operation(context, next_interceptor)

    assert next_called
    assert result == "next_result"


# ==================== Actor Tests ====================


@pytest.mark.asyncio
async def test_default_actor_is_system(mock_session):
    """Test that default actor is 'system' when not specified."""
    interceptor = AuditInterceptor()  # No actor specified

    entity = AuditedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="unused@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await interceptor.before_operation(context, next_interceptor)

    assert entity.created_by == "system"
    assert entity.updated_by == "system"


@pytest.mark.asyncio
async def test_actor_from_interceptor_init(mock_session):
    """Test that actor from interceptor initialization is used."""
    interceptor = AuditInterceptor(actor="custom@example.com")

    entity = AuditedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=AuditedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="context@example.com",  # Different actor in context
    )

    async def next_interceptor(ctx):
        return None

    await interceptor.before_operation(context, next_interceptor)

    # Should use interceptor's actor, not context's actor
    assert entity.created_by == "custom@example.com"
    assert entity.updated_by == "custom@example.com"
