"""Tests for CacheManager to improve coverage."""

from __future__ import annotations

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


def test_cache_manager_setup_with_dict_config() -> None:
    """Test setup with dict cache config."""
    runtime = Mock()
    runtime.config = Mock()
    runtime.config.cache = {
        "backend": "memory",
        "prefix": "test_",
        "ttl": 3600,
        "max_size": 5000,
    }
    runtime.container = Mock()
    manager = CacheManager(runtime)
    manager.setup()
