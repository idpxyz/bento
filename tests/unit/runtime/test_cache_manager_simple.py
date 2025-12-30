"""Simple unit tests for CacheManager."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from bento.runtime.cache.manager import CacheManager


def test_cache_manager_init() -> None:
    """Test CacheManager initialization."""
    runtime = Mock()
    manager = CacheManager(runtime)
    assert manager.runtime is runtime


def test_cache_manager_setup_no_config() -> None:
    """Test setup with no cache config."""
    runtime = Mock()
    runtime.config = Mock(spec=[])
    manager = CacheManager(runtime)
    manager.setup()
    runtime.container.set.assert_not_called()


def test_cache_manager_setup_none_config() -> None:
    """Test setup with None cache config."""
    runtime = Mock()
    runtime.config = Mock()
    runtime.config.cache = None
    manager = CacheManager(runtime)
    manager.setup()
    runtime.container.set.assert_not_called()


@pytest.mark.asyncio
async def test_cache_manager_cleanup_no_cache() -> None:
    """Test cleanup when no cache exists."""
    runtime = Mock()
    runtime.container = Mock()
    runtime.container.get.side_effect = KeyError("cache")
    manager = CacheManager(runtime)
    await manager.cleanup()
