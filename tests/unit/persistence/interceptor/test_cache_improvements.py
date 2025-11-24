"""Tests for Phase 1 cache improvements."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory, SerializerType
from bento.persistence.interceptor.impl.cache import CACHE_NULL, CacheInterceptor


@pytest_asyncio.fixture
async def cache():
    return await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )


# ==================== 改进 1: Singleflight 超时控制测试 ====================


@pytest.mark.asyncio
async def test_singleflight_timeout_control(cache):
    """测试 Singleflight 超时控制功能"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_singleflight=True,
        singleflight_timeout=0.1,  # 100ms 超时
        fail_open=True,
    )

    # 模拟慢查询
    slow_cache = AsyncMock()

    async def slow_get(key):
        await asyncio.sleep(1.0)  # 1秒延迟，超过超时时间
        return "result"

    slow_cache.get = slow_get
    cache_interceptor._cache = slow_cache

    # 调用应该超时并降级
    result = await cache_interceptor._get_from_cache_with_fallback("test_key")

    # 验证：超时后返回 None（降级）
    assert result is None

    # 验证：超时计数增加
    stats = cache_interceptor.get_stats()
    assert stats["fail_open_count"] > 0


@pytest.mark.asyncio
async def test_singleflight_timeout_value_configurable(cache):
    """测试 Singleflight 超时值可配置"""
    cache_interceptor = CacheInterceptor(
        cache,
        singleflight_timeout=10.0,  # 10秒超时
    )

    assert cache_interceptor._singleflight_timeout == 10.0


# ==================== 改进 2: 序列化兼容性测试 ====================


@pytest.mark.asyncio
async def test_cache_null_pickle_serialization():
    """测试 CACHE_NULL 支持 pickle 序列化"""
    import pickle

    # 序列化
    serialized = pickle.dumps(CACHE_NULL)

    # 反序列化
    deserialized = pickle.loads(serialized)

    # 验证：反序列化后仍然是相同的标记
    assert isinstance(deserialized, type(CACHE_NULL))


@pytest.mark.asyncio
async def test_cache_null_repr():
    """测试 CACHE_NULL 的字符串表示"""
    assert repr(CACHE_NULL) == "<CacheNull>"


@pytest.mark.asyncio
async def test_null_value_cached_with_serialization(cache):
    """测试空值缓存支持序列化"""
    _ = CacheInterceptor(
        cache,
        enable_null_cache=True,
    )

    # 设置空值缓存
    await cache.set("test_key", CACHE_NULL, ttl=10)

    # 读取应该成功
    cached = await cache.get("test_key")

    # 验证：可以正确读取和识别
    assert isinstance(cached, type(CACHE_NULL))


# ==================== 改进 3: 监控指标测试 ====================


@pytest.mark.asyncio
async def test_get_stats_returns_all_metrics(cache):
    """测试 get_stats 返回所有指标"""
    cache_interceptor = CacheInterceptor(cache)

    stats = cache_interceptor.get_stats()

    # 验证：包含所有预期的指标
    assert "singleflight_saved" in stats
    assert "singleflight_timeout" in stats
    assert "fail_open_count" in stats
    assert "null_cache_hits" in stats
    assert "cache_hits" in stats
    assert "cache_misses" in stats

    # 验证：初始值为 0
    for value in stats.values():
        assert value == 0


@pytest.mark.asyncio
async def test_cache_hit_miss_tracking(cache):
    """测试缓存命中和未命中的统计"""
    from bento.persistence.interceptor import InterceptorChain, InterceptorContext, OperationType

    cache_interceptor = CacheInterceptor(cache)
    chain = InterceptorChain([cache_interceptor])

    class MockPO:
        pass

    # 创建上下文
    context = InterceptorContext(
        session=Mock(),
        entity_type=MockPO,
        operation=OperationType.AGGREGATE,
    )
    context.set_context_value("aggregate_method", "sum")
    context.set_context_value("field", "price")
    context.set_context_value("specification", None)

    # 第一次查询 - 缓存未命中
    _ = await chain.execute_before(context)
    stats1 = cache_interceptor.get_stats()
    assert stats1["cache_misses"] == 1
    assert stats1["cache_hits"] == 0

    # 设置缓存
    await chain.process_result(context, 100)

    # 第二次查询 - 缓存命中
    _ = await chain.execute_before(context)
    stats2 = cache_interceptor.get_stats()
    assert stats2["cache_hits"] == 1
    assert stats2["cache_misses"] == 1  # 仍然是 1


@pytest.mark.asyncio
async def test_null_cache_hits_tracking(cache):
    """测试空值缓存命中统计"""
    from bento.persistence.interceptor import InterceptorChain, InterceptorContext, OperationType

    cache_interceptor = CacheInterceptor(
        cache,
        enable_null_cache=True,
    )
    chain = InterceptorChain([cache_interceptor])

    class MockPO:
        pass

    context = InterceptorContext(
        session=Mock(),
        entity_type=MockPO,
        operation=OperationType.GET,
    )
    context.set_context_value("entity_id", "non_existent")

    # 缓存空值
    await chain.process_result(context, None)

    # 查询空值缓存
    _ = await chain.execute_before(context)

    # 验证：空值缓存命中统计增加
    stats = cache_interceptor.get_stats()
    assert stats["null_cache_hits"] > 0


@pytest.mark.asyncio
async def test_fail_open_count_tracking(cache):
    """测试 Fail-Open 降级次数统计"""
    # 创建总是出错的 mock cache
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))

    cache_interceptor = CacheInterceptor(
        mock_cache,
        fail_open=True,
    )

    # 调用应该降级
    _ = await cache_interceptor._get_from_cache_with_fallback("test_key")

    # 验证：降级计数增加
    stats = cache_interceptor.get_stats()
    assert stats["fail_open_count"] == 1


@pytest.mark.asyncio
async def test_reset_stats(cache):
    """测试重置统计功能"""
    cache_interceptor = CacheInterceptor(cache)

    # 修改统计值
    cache_interceptor._stats["cache_hits"] = 100
    cache_interceptor._stats["cache_misses"] = 50

    # 重置
    cache_interceptor.reset_stats()

    # 验证：所有统计值归零
    stats = cache_interceptor.get_stats()
    for value in stats.values():
        assert value == 0


@pytest.mark.asyncio
async def test_get_stats_returns_copy(cache):
    """测试 get_stats 返回的是副本"""
    cache_interceptor = CacheInterceptor(cache)

    stats = cache_interceptor.get_stats()

    # 修改返回的统计
    stats["cache_hits"] = 999

    # 验证：不影响原始统计
    actual_stats = cache_interceptor.get_stats()
    assert actual_stats["cache_hits"] == 0


# ==================== 集成测试 ====================


@pytest.mark.asyncio
async def test_all_improvements_work_together(cache):
    """测试所有改进功能协同工作"""
    cache_interceptor = CacheInterceptor(
        cache,
        enable_singleflight=True,
        singleflight_timeout=5.0,  # ✅ 超时控制
        enable_null_cache=True,  # ✅ 序列化支持
        fail_open=True,
    )

    # 验证：配置正确
    assert cache_interceptor._singleflight is not None
    assert cache_interceptor._singleflight_timeout == 5.0

    # 验证：统计功能可用
    stats = cache_interceptor.get_stats()
    assert isinstance(stats, dict)
    assert len(stats) == 6

    # 验证：序列化支持
    import pickle

    serialized = pickle.dumps(CACHE_NULL)
    deserialized = pickle.loads(serialized)
    assert isinstance(deserialized, type(CACHE_NULL))


@pytest.mark.asyncio
async def test_calculate_hit_rate_from_stats(cache):
    """测试从统计计算命中率"""
    cache_interceptor = CacheInterceptor(cache)

    # 模拟一些统计数据
    cache_interceptor._stats["cache_hits"] = 80
    cache_interceptor._stats["cache_misses"] = 20

    stats = cache_interceptor.get_stats()

    # 计算命中率
    total = stats["cache_hits"] + stats["cache_misses"]
    hit_rate = stats["cache_hits"] / total if total > 0 else 0

    assert hit_rate == 0.8  # 80%
