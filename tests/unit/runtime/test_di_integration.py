"""Tests for DIIntegration."""

import pytest

from bento.runtime import RuntimeBuilder
from bento.runtime.integrations.di import DIIntegration


@pytest.mark.asyncio
async def test_get_uow_without_database_raises_error():
    """Test that get_uow raises error when database not configured."""
    runtime = RuntimeBuilder().build_runtime()
    di_integration = DIIntegration(runtime)

    with pytest.raises(RuntimeError, match="Database not configured"):
        di_integration.get_uow()


@pytest.mark.asyncio
async def test_get_uow_returns_generator(tmp_path):
    """Test that get_uow returns async generator function."""
    db_path = tmp_path / "test.db"
    runtime = RuntimeBuilder().with_database(url=f"sqlite+aiosqlite:///{db_path}").build_runtime()
    await runtime.build_async()

    di_integration = DIIntegration(runtime)
    uow_func = di_integration.get_uow()

    assert callable(uow_func)

    # Test that it's an async generator
    gen = uow_func()
    uow = await gen.__anext__()
    assert uow is not None


@pytest.mark.asyncio
async def test_get_repository_dependency_returns_generator(tmp_path):
    """Test that get_repository_dependency returns async generator."""
    from bento.domain.aggregate import AggregateRoot

    class TestAggregate(AggregateRoot):
        pass

    db_path = tmp_path / "test.db"
    runtime = RuntimeBuilder().with_database(url=f"sqlite+aiosqlite:///{db_path}").build_runtime()
    await runtime.build_async()

    di_integration = DIIntegration(runtime)
    repo_func = di_integration.get_repository_dependency(TestAggregate)

    assert callable(repo_func)


def test_get_event_bus_returns_none_when_not_configured():
    """Test that get_event_bus returns None when not configured."""
    runtime = RuntimeBuilder().build_runtime()
    di_integration = DIIntegration(runtime)

    event_bus_func = di_integration.get_event_bus()
    result = event_bus_func()

    assert result is None


def test_get_container_returns_container():
    """Test that get_container returns the runtime container."""
    runtime = RuntimeBuilder().build_runtime()
    di_integration = DIIntegration(runtime)

    container_func = di_integration.get_container()
    container = container_func()

    assert container is runtime.container


def test_get_handler_dependency_returns_dict():
    """Test that get_handler_dependency returns dependency dict."""
    runtime = RuntimeBuilder().build_runtime()
    di_integration = DIIntegration(runtime)

    handler_func = di_integration.get_handler_dependency()
    result = handler_func()

    assert isinstance(result, dict)
    assert "uow_factory" in result
    assert "event_bus" in result
    assert "container" in result


@pytest.mark.asyncio
async def test_get_uow_caches_function(tmp_path):
    """Test that get_uow caches the generated function."""
    db_path = tmp_path / "test.db"
    runtime = RuntimeBuilder().with_database(url=f"sqlite+aiosqlite:///{db_path}").build_runtime()
    await runtime.build_async()

    di_integration = DIIntegration(runtime)

    func1 = di_integration.get_uow()
    func2 = di_integration.get_uow()

    # Should return same cached function
    assert func1 is func2
