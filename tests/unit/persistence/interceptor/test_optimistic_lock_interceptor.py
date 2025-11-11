"""Unit tests for OptimisticLockInterceptor.

Tests cover:
- Version initialization on CREATE
- Version increment on UPDATE
- Concurrent conflict detection
- OptimisticLockException raising
- Event publishing on version updates
- Batch operation support
- Custom version field mapping
- Priority ordering
"""

from unittest.mock import Mock

import pytest

from bento.persistence.interceptor import (
    InterceptorContext,
    OperationType,
    OptimisticLockException,
    OptimisticLockInterceptor,
)
from bento.persistence.interceptor.core.metadata import EntityMetadataRegistry

# ==================== Test Entities ====================


class VersionedEntity:
    """Test entity with standard version field."""

    def __init__(self) -> None:
        self.id = "test-001"
        self.name = "Test"
        self.version = 0


class CustomVersionEntity:
    """Test entity with custom version field name."""

    def __init__(self) -> None:
        self.id = "test-002"
        self.name = "Custom"
        self.revision = 0


class NonVersionedEntity:
    """Test entity without version field."""

    def __init__(self) -> None:
        self.id = "test-003"
        self.name = "NoVersion"


# ==================== Fixtures ====================


@pytest.fixture
def mock_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def lock_interceptor():
    """Create optimistic lock interceptor."""
    return OptimisticLockInterceptor()


@pytest.fixture
def disabled_lock_interceptor():
    """Create disabled optimistic lock interceptor."""

    class MockConfig:
        enable_optimistic_lock = False

    return OptimisticLockInterceptor(config=MockConfig())


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean up EntityMetadataRegistry after each test."""
    yield
    EntityMetadataRegistry.clear()


# ==================== Priority Tests ====================


def test_optimistic_lock_interceptor_priority(lock_interceptor):
    """Test that optimistic lock interceptor has HIGH priority."""
    from bento.persistence.interceptor import InterceptorPriority

    assert lock_interceptor.priority == InterceptorPriority.HIGH


def test_optimistic_lock_interceptor_type(lock_interceptor):
    """Test interceptor type identifier."""
    assert lock_interceptor.interceptor_type == "optimistic_lock"


# ==================== CREATE Operation Tests ====================


@pytest.mark.asyncio
async def test_create_initializes_version(lock_interceptor, mock_session):
    """Test that CREATE operation initializes version to 1."""
    entity = VersionedEntity()
    entity.version = 0

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    assert entity.version == 1


@pytest.mark.asyncio
async def test_create_with_existing_version(lock_interceptor, mock_session):
    """Test that CREATE still initializes version even if entity has one."""
    entity = VersionedEntity()
    entity.version = 5  # Pre-existing version

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    # Should be reset to 1
    assert entity.version == 1


# ==================== UPDATE Operation Tests ====================


@pytest.mark.asyncio
async def test_update_increments_version(lock_interceptor, mock_session):
    """Test that UPDATE operation increments version."""
    entity = VersionedEntity()
    entity.version = 5

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    assert entity.version == 6


@pytest.mark.asyncio
async def test_update_stores_old_version_in_context(lock_interceptor, mock_session):
    """Test that UPDATE stores old version in context for event notification."""
    entity = VersionedEntity()
    entity.version = 5

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    # Check old version is stored in context
    assert context.get_context_value("_old_version") == 5


@pytest.mark.asyncio
async def test_update_from_zero_version(lock_interceptor, mock_session):
    """Test UPDATE increments from 0 to 1."""
    entity = VersionedEntity()
    entity.version = 0

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    assert entity.version == 1


# ==================== Batch Operation Tests ====================


@pytest.mark.asyncio
async def test_batch_create_initializes_all_versions(lock_interceptor, mock_session):
    """Test that BATCH_CREATE initializes versions for all entities."""
    entities = [VersionedEntity() for _ in range(5)]

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.BATCH_CREATE,
        entities=entities,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    for entity in entities:
        assert entity.version == 1


@pytest.mark.asyncio
async def test_batch_update_increments_all_versions(lock_interceptor, mock_session):
    """Test that BATCH_UPDATE increments versions for all entities."""
    entities = []
    for i in range(5):
        entity = VersionedEntity()
        entity.version = i + 1  # Version 1, 2, 3, 4, 5
        entities.append(entity)

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.BATCH_UPDATE,
        entities=entities,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    for i, entity in enumerate(entities):
        assert entity.version == i + 2  # Version 2, 3, 4, 5, 6


@pytest.mark.asyncio
async def test_batch_create_empty_list(lock_interceptor, mock_session):
    """Test that BATCH_CREATE handles empty entity list."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.BATCH_CREATE,
        entities=[],
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await lock_interceptor.before_operation(context, next_interceptor)


@pytest.mark.asyncio
async def test_batch_update_none_entities(lock_interceptor, mock_session):
    """Test that BATCH_UPDATE handles None entities gracefully."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.BATCH_UPDATE,
        entities=None,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await lock_interceptor.before_operation(context, next_interceptor)


# ==================== Custom Version Field Tests ====================


@pytest.mark.asyncio
async def test_custom_version_field(lock_interceptor, mock_session):
    """Test with custom version field name via EntityMetadataRegistry."""
    # Register custom version field (as top-level metadata, not under "fields")
    EntityMetadataRegistry.register(
        CustomVersionEntity,
        version_field="revision",
    )

    entity = CustomVersionEntity()
    entity.revision = 0

    context = InterceptorContext(
        session=mock_session,
        entity_type=CustomVersionEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    # Custom field should be set
    assert entity.revision == 1


@pytest.mark.asyncio
async def test_custom_version_field_update(lock_interceptor, mock_session):
    """Test UPDATE with custom version field."""
    # Register custom version field (as top-level metadata, not under "fields")
    EntityMetadataRegistry.register(
        CustomVersionEntity,
        version_field="revision",
    )

    entity = CustomVersionEntity()
    entity.revision = 3

    context = InterceptorContext(
        session=mock_session,
        entity_type=CustomVersionEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    assert entity.revision == 4


# ==================== Non-Versioned Entity Tests ====================


@pytest.mark.asyncio
async def test_non_versioned_entity_ignored(lock_interceptor, mock_session):
    """Test that entities without version field are ignored."""
    entity = NonVersionedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=NonVersionedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await lock_interceptor.before_operation(context, next_interceptor)

    # Entity should remain unchanged
    assert not hasattr(entity, "version")


# ==================== Non-CRUD Operations ====================


@pytest.mark.asyncio
async def test_delete_operation_ignored(lock_interceptor, mock_session):
    """Test that DELETE operations don't affect version."""
    entity = VersionedEntity()
    entity.version = 5

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.DELETE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    # Version should not change
    assert entity.version == 5


@pytest.mark.asyncio
async def test_read_operation_ignored(lock_interceptor, mock_session):
    """Test that READ operations don't affect version."""
    entity = VersionedEntity()
    entity.version = 5

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.READ,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await lock_interceptor.before_operation(context, next_interceptor)

    # Version should not change
    assert entity.version == 5


# ==================== Process Result Tests (Event Publishing) ====================


@pytest.mark.asyncio
async def test_process_result_for_update(lock_interceptor, mock_session):
    """Test that process_result is called for UPDATE operations."""
    entity = VersionedEntity()
    entity.id = "test-123"
    entity.version = 6  # After increment

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )
    context.set_context_value("_old_version", 5)

    async def next_interceptor(ctx, result):
        return result

    result = await lock_interceptor.process_result(context, entity, next_interceptor)

    assert result == entity


@pytest.mark.asyncio
async def test_process_result_for_non_update(lock_interceptor, mock_session):
    """Test that process_result passes through for non-UPDATE operations."""
    entity = VersionedEntity()
    entity.version = 1

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx, result):
        return result

    result = await lock_interceptor.process_result(context, entity, next_interceptor)

    assert result == entity


# ==================== Configuration Tests ====================


def test_is_enabled_in_config():
    """Test is_enabled_in_config method."""

    class MockConfig:
        enable_optimistic_lock = True

    assert OptimisticLockInterceptor.is_enabled_in_config(MockConfig())


def test_is_disabled_in_config():
    """Test is_enabled_in_config with disabled config."""

    class MockConfig:
        enable_optimistic_lock = False

    assert not OptimisticLockInterceptor.is_enabled_in_config(MockConfig())


def test_is_enabled_default():
    """Test is_enabled_in_config with missing attribute (default True)."""

    class MockConfig:
        pass

    # Default should be True
    assert OptimisticLockInterceptor.is_enabled_in_config(MockConfig())


def test_enabled_property(lock_interceptor):
    """Test enabled property getter."""
    assert lock_interceptor.enabled is True


def test_enabled_property_setter(lock_interceptor):
    """Test enabled property setter."""
    lock_interceptor.enabled = False
    assert lock_interceptor.enabled is False

    lock_interceptor.enabled = True
    assert lock_interceptor.enabled is True


def test_disabled_interceptor(disabled_lock_interceptor):
    """Test creating interceptor with disabled config."""
    assert disabled_lock_interceptor.enabled is False


# ==================== Disabled Interceptor Tests ====================


@pytest.mark.asyncio
async def test_disabled_interceptor_skips_create(disabled_lock_interceptor, mock_session):
    """Test that disabled interceptor doesn't initialize version."""
    entity = VersionedEntity()
    entity.version = 0

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await disabled_lock_interceptor.before_operation(context, next_interceptor)

    # Version should remain unchanged
    assert entity.version == 0


@pytest.mark.asyncio
async def test_disabled_interceptor_skips_update(disabled_lock_interceptor, mock_session):
    """Test that disabled interceptor doesn't increment version."""
    entity = VersionedEntity()
    entity.version = 5

    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.UPDATE,
        entity=entity,
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    await disabled_lock_interceptor.before_operation(context, next_interceptor)

    # Version should remain unchanged
    assert entity.version == 5


# ==================== Context Tests ====================


@pytest.mark.asyncio
async def test_null_entity_context(lock_interceptor, mock_session):
    """Test that null entity in context is handled gracefully."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.CREATE,
        entity=None,  # No entity
        actor="test@example.com",
    )

    async def next_interceptor(ctx):
        return None

    # Should not raise exception
    await lock_interceptor.before_operation(context, next_interceptor)


# ==================== Next Interceptor Tests ====================


@pytest.mark.asyncio
async def test_calls_next_interceptor(lock_interceptor, mock_session):
    """Test that the interceptor calls the next interceptor in chain."""
    entity = VersionedEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=VersionedEntity,
        operation=OperationType.CREATE,
        entity=entity,
        actor="test@example.com",
    )

    next_called = False

    async def next_interceptor(ctx):
        nonlocal next_called
        next_called = True
        return "next_result"

    result = await lock_interceptor.before_operation(context, next_interceptor)

    assert next_called
    assert result == "next_result"


# ==================== Exception Tests ====================


def test_optimistic_lock_exception_creation():
    """Test OptimisticLockException creation."""
    exc = OptimisticLockException(
        entity_type="User",
        entity_id="user-123",
        expected_version=5,
        actual_version=7,
    )

    assert exc.entity_type == "User"
    assert exc.entity_id == "user-123"
    assert exc.expected_version == 5
    assert exc.actual_version == 7
    assert "user-123" in str(exc)
    assert "User" in str(exc)
    assert "5" in str(exc)
    assert "7" in str(exc)


def test_optimistic_lock_exception_message():
    """Test OptimisticLockException message format."""
    exc = OptimisticLockException(
        entity_type="Order",
        entity_id=12345,
        expected_version=10,
        actual_version=15,
    )

    message = str(exc)
    assert "Optimistic lock conflict" in message
    assert "Order#12345" in message
    assert "expected version 10" in message
    assert "found 15" in message
    assert "modified by another transaction" in message
