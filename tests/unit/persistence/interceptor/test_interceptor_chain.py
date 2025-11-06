"""Unit tests for InterceptorChain.

Tests cover:
- Priority-based interceptor ordering
- Before operation hook execution
- After operation hook execution
- Error handling chain
- Process result chain
- Process batch results
- Adding/removing interceptors dynamically
- Empty chain behavior
"""

from unittest.mock import Mock

import pytest

from bento.persistence.interceptor import (
    Interceptor,
    InterceptorChain,
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)

# ==================== Test Interceptors ====================


class SimpleEntity:
    """Simple test entity."""

    def __init__(self, value: str = "test") -> None:
        self.value = value


class HighPriorityInterceptor(Interceptor[SimpleEntity]):
    """Interceptor with HIGH priority."""

    @property
    def priority(self) -> InterceptorPriority:
        return InterceptorPriority.HIGH

    async def before_operation(self, context, next_interceptor):
        context.set_context_value(
            "execution_order", context.get_context_value("execution_order", []) + ["high_before"]
        )
        return await next_interceptor(context)

    async def after_operation(self, context, result, next_interceptor):
        context.set_context_value(
            "execution_order", context.get_context_value("execution_order", []) + ["high_after"]
        )
        return await next_interceptor(context, result)


class NormalPriorityInterceptor(Interceptor[SimpleEntity]):
    """Interceptor with NORMAL priority."""

    @property
    def priority(self) -> InterceptorPriority:
        return InterceptorPriority.NORMAL

    async def before_operation(self, context, next_interceptor):
        context.set_context_value(
            "execution_order", context.get_context_value("execution_order", []) + ["normal_before"]
        )
        return await next_interceptor(context)

    async def after_operation(self, context, result, next_interceptor):
        context.set_context_value(
            "execution_order", context.get_context_value("execution_order", []) + ["normal_after"]
        )
        return await next_interceptor(context, result)


class LowPriorityInterceptor(Interceptor[SimpleEntity]):
    """Interceptor with LOW priority."""

    @property
    def priority(self) -> InterceptorPriority:
        return InterceptorPriority.LOW

    async def before_operation(self, context, next_interceptor):
        context.set_context_value(
            "execution_order", context.get_context_value("execution_order", []) + ["low_before"]
        )
        return await next_interceptor(context)

    async def after_operation(self, context, result, next_interceptor):
        context.set_context_value(
            "execution_order", context.get_context_value("execution_order", []) + ["low_after"]
        )
        return await next_interceptor(context, result)


class ModifyingInterceptor(Interceptor[SimpleEntity]):
    """Interceptor that modifies entity."""

    async def before_operation(self, context, next_interceptor):
        if context.entity:
            context.entity.value = context.entity.value + "_modified"
        return await next_interceptor(context)


class ResultModifyingInterceptor(Interceptor[SimpleEntity]):
    """Interceptor that modifies result."""

    async def process_result(self, context, result, next_interceptor):
        if result:
            result.value = result.value + "_result"
        return await next_interceptor(context, result)


class ErrorHandlingInterceptor(Interceptor[SimpleEntity]):
    """Interceptor that handles errors."""

    def __init__(self, should_catch: bool = False) -> None:
        self.should_catch = should_catch
        self.error_caught = None

    async def on_error(self, context, error, next_interceptor):
        self.error_caught = error
        if self.should_catch:
            return None  # Swallow error
        return await next_interceptor(context, error)


# ==================== Fixtures ====================


@pytest.fixture
def mock_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def empty_chain():
    """Create empty interceptor chain."""
    return InterceptorChain()


@pytest.fixture
def single_interceptor_chain():
    """Create chain with single interceptor."""
    return InterceptorChain([NormalPriorityInterceptor()])


@pytest.fixture
def multi_interceptor_chain():
    """Create chain with multiple interceptors in different priorities."""
    return InterceptorChain(
        [
            LowPriorityInterceptor(),
            HighPriorityInterceptor(),
            NormalPriorityInterceptor(),
        ]
    )


# ==================== Initialization Tests ====================


def test_create_empty_chain():
    """Test creating an empty interceptor chain."""
    chain = InterceptorChain()
    assert chain is not None


def test_create_chain_with_interceptors():
    """Test creating chain with interceptors."""
    interceptors = [
        HighPriorityInterceptor(),
        NormalPriorityInterceptor(),
    ]
    chain = InterceptorChain(interceptors)
    assert chain is not None


def test_create_chain_with_none():
    """Test creating chain with None."""
    chain = InterceptorChain(None)
    assert chain is not None


# ==================== Priority Ordering Tests ====================


def test_interceptors_sorted_by_priority(multi_interceptor_chain):
    """Test that interceptors are sorted by priority (lower number = higher priority)."""
    # Access internal interceptors list (implementation detail for testing)
    interceptors = multi_interceptor_chain._interceptors

    # Should be ordered: HIGH (100) < NORMAL (200) < LOW (300)
    assert isinstance(interceptors[0], HighPriorityInterceptor)
    assert isinstance(interceptors[1], NormalPriorityInterceptor)
    assert isinstance(interceptors[2], LowPriorityInterceptor)


def test_same_priority_stable_order():
    """Test that interceptors with same priority maintain stable order."""
    i1 = NormalPriorityInterceptor()
    i2 = NormalPriorityInterceptor()
    i3 = NormalPriorityInterceptor()

    chain = InterceptorChain([i1, i2, i3])
    interceptors = chain._interceptors

    # Should have all three interceptors
    assert len(interceptors) == 3
    # All should be NormalPriorityInterceptor
    assert all(isinstance(i, NormalPriorityInterceptor) for i in interceptors)


# ==================== Before Operation Tests ====================


@pytest.mark.asyncio
async def test_empty_chain_before_operation(empty_chain, mock_session):
    """Test before_operation on empty chain."""
    entity = SimpleEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    result = await empty_chain.execute_before(context)
    assert result is None


@pytest.mark.asyncio
async def test_single_interceptor_before_operation(single_interceptor_chain, mock_session):
    """Test before_operation with single interceptor."""
    entity = SimpleEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    await single_interceptor_chain.execute_before(context)

    # Check execution
    order = context.get_context_value("execution_order", [])
    assert "normal_before" in order


@pytest.mark.asyncio
async def test_multi_interceptor_before_execution_order(multi_interceptor_chain, mock_session):
    """Test that before_operation executes in priority order."""
    entity = SimpleEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    await multi_interceptor_chain.execute_before(context)

    order = context.get_context_value("execution_order", [])
    # Should execute in priority order: high -> normal -> low
    assert order == ["high_before", "normal_before", "low_before"]


@pytest.mark.asyncio
async def test_before_operation_modifies_entity(mock_session):
    """Test that interceptor can modify entity in before_operation."""
    chain = InterceptorChain([ModifyingInterceptor()])
    entity = SimpleEntity("original")

    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    await chain.execute_before(context)

    assert entity.value == "original_modified"


# ==================== After Operation Tests ====================


@pytest.mark.asyncio
async def test_empty_chain_after_operation(empty_chain, mock_session):
    """Test after_operation on empty chain."""
    entity = SimpleEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    result = await empty_chain.execute_after(context, "result")
    assert result == "result"


@pytest.mark.asyncio
async def test_multi_interceptor_after_execution_order(multi_interceptor_chain, mock_session):
    """Test that after_operation executes in priority order."""
    entity = SimpleEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    await multi_interceptor_chain.execute_after(context, "result")

    order = context.get_context_value("execution_order", [])
    # Should execute in priority order: high -> normal -> low
    assert order == ["high_after", "normal_after", "low_after"]


# ==================== Process Result Tests ====================


@pytest.mark.asyncio
async def test_empty_chain_process_result(empty_chain, mock_session):
    """Test process_result on empty chain."""
    entity = SimpleEntity("original")
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    result = await empty_chain.process_result(context, entity)
    assert result.value == "original"


@pytest.mark.asyncio
async def test_process_result_modifies_entity(mock_session):
    """Test that interceptor can modify result."""
    chain = InterceptorChain([ResultModifyingInterceptor()])
    entity = SimpleEntity("original")

    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    result = await chain.process_result(context, entity)

    assert result.value == "original_result"


@pytest.mark.asyncio
async def test_process_result_chain(mock_session):
    """Test that multiple interceptors can chain process_result."""
    chain = InterceptorChain(
        [
            ResultModifyingInterceptor(),
            ResultModifyingInterceptor(),
        ]
    )
    entity = SimpleEntity("original")

    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    result = await chain.process_result(context, entity)

    # Should be modified twice
    assert result.value == "original_result_result"


# ==================== Process Batch Results Tests ====================


@pytest.mark.asyncio
async def test_empty_chain_process_batch_results(empty_chain, mock_session):
    """Test process_batch_results on empty chain."""
    entities = [SimpleEntity(f"entity_{i}") for i in range(3)]
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.BATCH_CREATE,
        entities=entities,
    )

    results = await empty_chain.process_batch_results(context, entities)

    assert len(results) == 3
    assert results[0].value == "entity_0"


@pytest.mark.asyncio
async def test_process_batch_results_modifies_all(mock_session):
    """Test that batch processing modifies all entities."""
    chain = InterceptorChain([ResultModifyingInterceptor()])
    entities = [SimpleEntity(f"entity_{i}") for i in range(3)]

    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.BATCH_CREATE,
        entities=entities,
    )

    results = await chain.process_batch_results(context, entities)

    assert len(results) == 3
    for i, result in enumerate(results):
        assert result.value == f"entity_{i}_result"


# ==================== Error Handling Tests ====================


@pytest.mark.asyncio
async def test_empty_chain_on_error(empty_chain, mock_session):
    """Test on_error on empty chain re-raises."""
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
    )

    test_error = ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        await empty_chain.execute_on_error(context, test_error)


@pytest.mark.asyncio
async def test_error_handler_catches_error(mock_session):
    """Test that error handler can catch and swallow error."""
    handler = ErrorHandlingInterceptor(should_catch=True)
    chain = InterceptorChain([handler])

    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
    )

    test_error = ValueError("Test error")

    # Should not raise
    result = await chain.execute_on_error(context, test_error)

    assert handler.error_caught is test_error
    assert result is None


@pytest.mark.asyncio
async def test_error_handler_propagates_error(mock_session):
    """Test that error handler can propagate error."""
    handler = ErrorHandlingInterceptor(should_catch=False)
    chain = InterceptorChain([handler])

    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
    )

    test_error = ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        await chain.execute_on_error(context, test_error)

    assert handler.error_caught is test_error


# ==================== Dynamic Add/Remove Tests ====================


def test_add_interceptor():
    """Test adding interceptor to chain."""
    chain = InterceptorChain([NormalPriorityInterceptor()])
    high_priority = HighPriorityInterceptor()

    chain.add_interceptor(high_priority)

    # Should be re-sorted, high priority first
    interceptors = chain._interceptors
    assert len(interceptors) == 2
    assert isinstance(interceptors[0], HighPriorityInterceptor)


def test_remove_interceptor():
    """Test removing interceptor from chain."""
    normal = NormalPriorityInterceptor()
    high = HighPriorityInterceptor()
    chain = InterceptorChain([normal, high])

    chain.remove_interceptor(normal)

    interceptors = chain._interceptors
    assert len(interceptors) == 1
    assert isinstance(interceptors[0], HighPriorityInterceptor)


def test_remove_non_existent_interceptor():
    """Test removing interceptor that doesn't exist."""
    chain = InterceptorChain([NormalPriorityInterceptor()])
    other = HighPriorityInterceptor()

    # Should not raise
    chain.remove_interceptor(other)

    interceptors = chain._interceptors
    assert len(interceptors) == 1


# ==================== Complex Scenarios ====================


@pytest.mark.asyncio
async def test_full_lifecycle(multi_interceptor_chain, mock_session):
    """Test full before -> after lifecycle."""
    entity = SimpleEntity()
    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    # Execute before
    await multi_interceptor_chain.execute_before(context)
    before_order = context.get_context_value("execution_order", [])

    # Execute after
    await multi_interceptor_chain.execute_after(context, entity)
    after_order = context.get_context_value("execution_order", [])

    # Both should execute in priority order
    assert before_order == ["high_before", "normal_before", "low_before"]
    assert after_order == [
        "high_before",
        "normal_before",
        "low_before",
        "high_after",
        "normal_after",
        "low_after",
    ]


@pytest.mark.asyncio
async def test_chain_with_multiple_modifying_interceptors(mock_session):
    """Test chain with multiple interceptors that modify entity."""
    chain = InterceptorChain(
        [
            ModifyingInterceptor(),
            ModifyingInterceptor(),
        ]
    )
    entity = SimpleEntity("original")

    context = InterceptorContext(
        session=mock_session,
        entity_type=SimpleEntity,
        operation=OperationType.CREATE,
        entity=entity,
    )

    await chain.execute_before(context)

    # Should be modified twice
    assert entity.value == "original_modified_modified"
