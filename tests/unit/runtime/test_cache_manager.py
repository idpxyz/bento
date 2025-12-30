"""Unit tests for CacheManager."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from bento.runtime.cache.manager import CacheManager


class TestCacheManager:
    """Tests for CacheManager."""

    def test_init(self) -> None:
        """Test CacheManager initialization."""
        runtime = Mock()
        manager = CacheManager(runtime)
        assert manager.runtime is runtime

    def test_setup_no_cache_config(self) -> None:
        """Test setup when no cache config is provided."""
        runtime = Mock()
        runtime.config = Mock(spec=[])
        manager = CacheManager(runtime)

        manager.setup()

        # Should not set cache in container
        runtime.container.set.assert_not_called()

    def test_setup_with_none_cache_config(self) -> None:
        """Test setup when cache config is None."""
        runtime = Mock()
        runtime.config = Mock()
        runtime.config.cache = None
        manager = CacheManager(runtime)

        manager.setup()

        runtime.container.set.assert_not_called()

    def test_setup_cache_adapters_not_available(self) -> None:
        """Test setup when cache adapters are not available."""
        runtime = Mock()
        runtime.config = Mock()
        runtime.config.cache = {"backend": "memory"}
        manager = CacheManager(runtime)

        with patch("bento.runtime.cache.manager.logger") as mock_logger:
            with patch.dict("sys.modules", {"bento.adapters.cache.config": None}):
                manager.setup()

                # Should log warning and return
                assert mock_logger.warning.called

    def test_setup_memory_cache_from_dict(self) -> None:
        """Test setup with memory cache from dict config."""
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

        mock_cache = Mock()
        with patch.object(manager, "_create_cache", return_value=mock_cache):
            manager.setup()

            runtime.container.set.assert_called_once_with("cache", mock_cache)

    def test_setup_cache_config_object(self) -> None:
        """Test setup with CacheConfig object."""
        runtime = Mock()
        cache_config = Mock()
        runtime.config = Mock()
        runtime.config.cache = cache_config
        runtime.container = Mock()
        manager = CacheManager(runtime)

        mock_cache = Mock()
        with patch.object(manager, "_create_cache", return_value=mock_cache):
            manager.setup()

            runtime.container.set.assert_called_once_with("cache", mock_cache)

    def test_setup_create_cache_returns_none(self) -> None:
        """Test setup when _create_cache returns None."""
        runtime = Mock()
        runtime.config = Mock()
        runtime.config.cache = {"backend": "memory"}
        runtime.container = Mock()
        manager = CacheManager(runtime)

        with patch.object(manager, "_create_cache", return_value=None):
            manager.setup()

            runtime.container.set.assert_not_called()

    def test_setup_exception_handling(self) -> None:
        """Test setup exception handling."""
        runtime = Mock()
        runtime.config = Mock()
        runtime.config.cache = {"backend": "memory"}
        manager = CacheManager(runtime)

        with patch.object(manager, "_create_cache", side_effect=Exception("Test error")):
            manager.setup()

            # Should not raise, just log warning

    def test_create_cache_memory_backend(self) -> None:
        """Test _create_cache with memory backend."""
        runtime = Mock()
        manager = CacheManager(runtime)

        config = Mock()
        config.backend = Mock()
        config.prefix = "test_"
        config.ttl = 3600
        config.max_size = 5000

        with patch("bento.runtime.cache.manager.CacheBackend") as mock_backend:
            with patch("bento.runtime.cache.manager.MemoryCache") as mock_memory:
                mock_backend.MEMORY = "memory"
                config.backend = "memory"

                mock_cache_instance = Mock()
                mock_memory.return_value = mock_cache_instance

                with patch("bento.runtime.cache.manager.logger"):
                    result = manager._create_cache(config)

                assert result is mock_cache_instance

    def test_create_cache_redis_backend_no_url(self) -> None:
        """Test _create_cache with Redis backend but no URL."""
        runtime = Mock()
        manager = CacheManager(runtime)

        config = Mock()
        config.backend = "redis"
        config.redis_url = None

        with patch("bento.runtime.cache.manager.CacheBackend") as mock_backend:
            mock_backend.REDIS = "redis"

            result = manager._create_cache(config)

            assert result is None

    def test_create_cache_redis_backend_with_url(self) -> None:
        """Test _create_cache with Redis backend and URL."""
        runtime = Mock()
        manager = CacheManager(runtime)

        config = Mock()
        config.backend = "redis"
        config.redis_url = "redis://localhost:6379"
        config.prefix = "test_"
        config.ttl = 3600

        with patch("bento.runtime.cache.manager.CacheBackend") as mock_backend:
            with patch("bento.runtime.cache.manager.RedisCache") as mock_redis:
                mock_backend.REDIS = "redis"
                config.backend = "redis"

                mock_cache_instance = Mock()
                mock_redis.return_value = mock_cache_instance

                with patch("bento.runtime.cache.manager.logger"):
                    result = manager._create_cache(config)

                assert result is mock_cache_instance

    def test_create_cache_redis_import_error_fallback(self) -> None:
        """Test _create_cache Redis import error fallback to memory."""
        runtime = Mock()
        manager = CacheManager(runtime)

        config = Mock()
        config.backend = "redis"
        config.redis_url = "redis://localhost:6379"
        config.prefix = "test_"
        config.ttl = 3600
        config.max_size = 5000

        with patch("bento.runtime.cache.manager.CacheBackend") as mock_backend:
            with patch("bento.runtime.cache.manager.MemoryCache") as mock_memory:
                mock_backend.REDIS = "redis"
                config.backend = "redis"

                # Simulate RedisCache import error
                with patch("bento.runtime.cache.manager.RedisCache", side_effect=ImportError):
                    mock_cache_instance = Mock()
                    mock_memory.return_value = mock_cache_instance

                    with patch("bento.runtime.cache.manager.logger"):
                        result = manager._create_cache(config)

                    assert result is mock_cache_instance

    def test_create_cache_unknown_backend(self) -> None:
        """Test _create_cache with unknown backend."""
        runtime = Mock()
        manager = CacheManager(runtime)

        config = Mock()
        config.backend = "unknown"

        with patch("bento.runtime.cache.manager.CacheBackend") as mock_backend:
            mock_backend.MEMORY = "memory"
            mock_backend.REDIS = "redis"

            result = manager._create_cache(config)

            assert result is None

    def test_create_cache_exception(self) -> None:
        """Test _create_cache exception handling."""
        runtime = Mock()
        manager = CacheManager(runtime)

        config = Mock()
        config.backend = "memory"

        with patch("bento.runtime.cache.manager.CacheBackend", side_effect=Exception("Test error")):
            result = manager._create_cache(config)

            assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_with_cache(self) -> None:
        """Test cleanup with cache present."""
        runtime = Mock()
        runtime.container = Mock()

        mock_cache = Mock()
        mock_cache.close = Mock()
        runtime.container.get.return_value = mock_cache

        manager = CacheManager(runtime)
        await manager.cleanup()

        mock_cache.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_no_cache(self) -> None:
        """Test cleanup when no cache is configured."""
        runtime = Mock()
        runtime.container = Mock()
        runtime.container.get.side_effect = KeyError("cache")

        manager = CacheManager(runtime)
        await manager.cleanup()

        # Should not raise

    @pytest.mark.asyncio
    async def test_cleanup_cache_without_close(self) -> None:
        """Test cleanup with cache that has no close method."""
        runtime = Mock()
        runtime.container = Mock()

        mock_cache = Mock(spec=[])  # No close method
        runtime.container.get.return_value = mock_cache

        manager = CacheManager(runtime)
        await manager.cleanup()

        # Should not raise
