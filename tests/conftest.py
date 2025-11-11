"""Pytest configuration and shared fixtures.

This module provides common fixtures and configuration for all tests.
"""

from collections.abc import AsyncGenerator

import pytest

# ============================================================================
# Async test configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


# ============================================================================
# Test markers
# ============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance benchmarks")


# ============================================================================
# Common fixtures
# ============================================================================

@pytest.fixture
def fake_id() -> str:
    """Generate a fake entity ID for testing."""
    return "test-id-123"


@pytest.fixture
async def async_noop() -> AsyncGenerator[None, None]:
    """Async no-op fixture for testing."""
    yield

