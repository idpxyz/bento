"""Simple tests for cache optimizations."""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory, SerializerType
from bento.persistence.interceptor.impl.cache import CacheInterceptor


class MockPO:
    pass


@pytest_asyncio.fixture
async def cache():
    return await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )


# ==================== TTL 抖动测试 ====================


@pytest.mark.asyncio
async def test_ttl_jitter_applied(cache):
    """测试 TTL 抖动被正确应用"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_jitter=True,
        jitter_range=0.1,
    )

    base_ttl = 600
    jittered_ttls = []

    # 生成多个抖动后的 TTL
    for _ in range(100):
        jittered_ttl = cache_interceptor._apply_jitter(base_ttl)
        jittered_ttls.append(jittered_ttl)

    # 验证：所有 TTL 都在 ±10% 范围内
    min_expected = int(base_ttl * 0.9)
    max_expected = int(base_ttl * 1.1)

    for ttl in jittered_ttls:
        assert min_expected <= ttl <= max_expected, (
            f"TTL {ttl} out of range [{min_expected}, {max_expected}]"
        )

    # 验证：TTL 值有变化（不是所有都相同）
    assert len(set(jittered_ttls)) > 1, "Jittered TTLs should vary"


@pytest.mark.asyncio
async def test_ttl_jitter_disabled(cache):
    """测试禁用 TTL 抖动"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_jitter=False,  # 禁用抖动
    )

    base_ttl = 600
    jittered_ttl = cache_interceptor._apply_jitter(base_ttl)

    # 验证：禁用后应返回原始 TTL
    assert jittered_ttl == base_ttl


# ==================== Fail-Open 测试 ====================


@pytest.mark.asyncio
async def test_fail_open_on_cache_timeout():
    """测试缓存超时时的 Fail-Open 行为"""
    # 创建一个总是超时的 mock cache
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(side_effect=TimeoutError("Cache timeout"))

    cache_interceptor = CacheInterceptor(
        mock_cache,
        fail_open=True,  # 启用 Fail-Open
        cache_timeout=0.1,
    )

    # 调用缓存（应该超时但不抛出异常）
    result = await cache_interceptor._get_from_cache_with_fallback("test_key")

    # 验证：返回 None（降级）而不是抛出异常
    assert result is None


@pytest.mark.asyncio
async def test_fail_open_on_cache_error():
    """测试缓存错误时的 Fail-Open 行为"""
    # 创建一个总是出错的 mock cache
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))

    cache_interceptor = CacheInterceptor(
        mock_cache,
        fail_open=True,  # 启用 Fail-Open
    )

    # 调用缓存（应该出错但不抛出异常）
    result = await cache_interceptor._get_from_cache_with_fallback("test_key")

    # 验证：返回 None（降级）而不是抛出异常
    assert result is None


@pytest.mark.asyncio
async def test_fail_closed_raises_exception():
    """测试 Fail-Closed 模式会抛出异常"""
    # 创建一个总是出错的 mock cache
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))

    cache_interceptor = CacheInterceptor(
        mock_cache,
        fail_open=False,  # 禁用 Fail-Open（Fail-Closed）
    )

    # 验证：应该抛出异常
    with pytest.raises(Exception, match="Cache error"):
        await cache_interceptor._get_from_cache_with_fallback("test_key")


# ==================== Singleflight 集成测试 ====================


@pytest.mark.asyncio
async def test_singleflight_enabled(cache):
    """测试 Singleflight 功能已启用"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_singleflight=True,
    )

    # 验证：Singleflight 实例已创建
    assert cache_interceptor._singleflight is not None


@pytest.mark.asyncio
async def test_singleflight_disabled(cache):
    """测试可以禁用 Singleflight"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_singleflight=False,
    )

    # 验证：Singleflight 未创建
    assert cache_interceptor._singleflight is None


# ==================== 空值缓存配置测试 ====================


@pytest.mark.asyncio
async def test_null_cache_configuration(cache):
    """测试空值缓存配置"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_null_cache=True,
        null_cache_ttl=10,
    )

    assert cache_interceptor._enable_null_cache is True
    assert cache_interceptor._null_cache_ttl == 10


@pytest.mark.asyncio
async def test_null_cache_disabled(cache):
    """测试禁用空值缓存"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_null_cache=False,
    )

    assert cache_interceptor._enable_null_cache is False


# ==================== 集成配置测试 ====================


@pytest.mark.asyncio
async def test_all_optimizations_configured(cache):
    """测试所有优化功能可以同时配置"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_singleflight=True,  # ✅ 防缓存击穿
        enable_jitter=True,  # ✅ 防缓存雪崩
        jitter_range=0.1,
        enable_null_cache=True,  # ✅ 防缓存穿透
        null_cache_ttl=10,
        fail_open=True,  # ✅ 容错
        cache_timeout=0.1,
    )

    # 验证所有配置
    assert cache_interceptor._singleflight is not None
    assert cache_interceptor._enable_jitter is True
    assert cache_interceptor._jitter_range == 0.1
    assert cache_interceptor._enable_null_cache is True
    assert cache_interceptor._null_cache_ttl == 10
    assert cache_interceptor._fail_open is True
    assert cache_interceptor._cache_timeout == 0.1
