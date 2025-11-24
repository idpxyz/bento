"""Tests for InterceptorConfig with cache optimization parameters."""

import pytest
import pytest_asyncio

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory, SerializerType
from bento.persistence.interceptor.factory import InterceptorConfig, InterceptorFactory
from bento.persistence.interceptor.impl.cache import CacheInterceptor


@pytest_asyncio.fixture
async def cache():
    return await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )


# ==================== 默认配置测试 ====================


@pytest.mark.asyncio
async def test_default_cache_optimization_config(cache):
    """测试默认缓存优化配置"""
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
    )

    # 验证：所有优化默认启用
    assert config.enable_singleflight is True
    assert config.enable_jitter is True
    assert config.enable_null_cache is True
    assert config.fail_open is True

    # 验证：默认值正确
    assert config.singleflight_timeout == 5.0
    assert config.jitter_range == 0.1
    assert config.null_cache_ttl == 10
    assert config.cache_timeout == 0.1


@pytest.mark.asyncio
async def test_factory_creates_cache_interceptor_with_optimizations(cache):
    """测试工厂创建带优化参数的缓存拦截器"""
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
    )

    factory = InterceptorFactory(config)
    chain = factory.build_chain()

    # 获取 CacheInterceptor
    cache_interceptor = None
    for interceptor in chain._interceptors:
        if isinstance(interceptor, CacheInterceptor):
            cache_interceptor = interceptor
            break

    # 验证：CacheInterceptor 已创建
    assert cache_interceptor is not None

    # 验证：优化参数已应用
    assert cache_interceptor._singleflight is not None
    assert cache_interceptor._singleflight_timeout == 5.0
    assert cache_interceptor._enable_jitter is True
    assert cache_interceptor._jitter_range == 0.1
    assert cache_interceptor._enable_null_cache is True
    assert cache_interceptor._null_cache_ttl == 10
    assert cache_interceptor._fail_open is True
    assert cache_interceptor._cache_timeout == 0.1


# ==================== 自定义配置测试 ====================


@pytest.mark.asyncio
async def test_custom_cache_optimization_config(cache):
    """测试自定义缓存优化配置"""
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
        # 自定义优化参数
        enable_singleflight=True,
        singleflight_timeout=10.0,
        enable_jitter=True,
        jitter_range=0.2,
        enable_null_cache=True,
        null_cache_ttl=5,
        fail_open=True,
        cache_timeout=0.2,
    )

    # 验证：自定义值已设置
    assert config.singleflight_timeout == 10.0
    assert config.jitter_range == 0.2
    assert config.null_cache_ttl == 5
    assert config.cache_timeout == 0.2


@pytest.mark.asyncio
async def test_factory_applies_custom_optimization_params(cache):
    """测试工厂应用自定义优化参数"""
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
        singleflight_timeout=15.0,
        jitter_range=0.3,
        null_cache_ttl=20,
        cache_timeout=0.5,
    )

    factory = InterceptorFactory(config)
    chain = factory.build_chain()

    # 获取 CacheInterceptor
    cache_interceptor = None
    for interceptor in chain._interceptors:
        if isinstance(interceptor, CacheInterceptor):
            cache_interceptor = interceptor
            break

    assert cache_interceptor is not None

    # 验证：自定义参数已应用
    assert cache_interceptor._singleflight_timeout == 15.0
    assert cache_interceptor._jitter_range == 0.3
    assert cache_interceptor._null_cache_ttl == 20
    assert cache_interceptor._cache_timeout == 0.5


# ==================== 禁用优化测试 ====================


@pytest.mark.asyncio
async def test_disable_specific_optimizations(cache):
    """测试禁用特定优化"""
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
        enable_singleflight=False,
        enable_jitter=False,
        enable_null_cache=False,
    )

    factory = InterceptorFactory(config)
    chain = factory.build_chain()

    cache_interceptor = None
    for interceptor in chain._interceptors:
        if isinstance(interceptor, CacheInterceptor):
            cache_interceptor = interceptor
            break

    assert cache_interceptor is not None

    # 验证：优化已禁用
    assert cache_interceptor._singleflight is None
    assert cache_interceptor._enable_jitter is False
    assert cache_interceptor._enable_null_cache is False


# ==================== 向后兼容测试 ====================


@pytest.mark.asyncio
async def test_backward_compatibility(cache):
    """测试向后兼容性"""
    # 旧的配置方式（只指定基本参数）
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
        cache_ttl_seconds=600,
        cache_prefix="test:",
    )

    factory = InterceptorFactory(config)
    chain = factory.build_chain()

    # 验证：仍然可以正常工作
    assert chain is not None
    assert len(chain._interceptors) > 0

    # 验证：优化参数使用默认值
    cache_interceptor = None
    for interceptor in chain._interceptors:
        if isinstance(interceptor, CacheInterceptor):
            cache_interceptor = interceptor
            break

    assert cache_interceptor is not None
    assert cache_interceptor._ttl == 600
    assert cache_interceptor._prefix == "test:"
    # 优化参数使用默认值
    assert cache_interceptor._singleflight is not None
    assert cache_interceptor._enable_jitter is True


# ==================== 配置验证测试 ====================


@pytest.mark.asyncio
async def test_all_optimization_params_available(cache):
    """测试所有优化参数都可配置"""
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
        cache_ttl_seconds=300,
        cache_prefix="app:",
        # 确保所有参数都可以配置
        enable_singleflight=True,
        singleflight_timeout=5.0,
        enable_jitter=True,
        jitter_range=0.1,
        enable_null_cache=True,
        null_cache_ttl=10,
        fail_open=True,
        cache_timeout=0.1,
    )

    # 验证：所有参数都已保存
    assert hasattr(config, "enable_singleflight")
    assert hasattr(config, "singleflight_timeout")
    assert hasattr(config, "enable_jitter")
    assert hasattr(config, "jitter_range")
    assert hasattr(config, "enable_null_cache")
    assert hasattr(config, "null_cache_ttl")
    assert hasattr(config, "fail_open")
    assert hasattr(config, "cache_timeout")


# ==================== 监控集成测试 ====================


@pytest.mark.asyncio
async def test_cache_stats_available_through_config(cache):
    """测试通过配置创建的拦截器可以获取统计"""
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
    )

    factory = InterceptorFactory(config)
    chain = factory.build_chain()

    cache_interceptor = None
    for interceptor in chain._interceptors:
        if isinstance(interceptor, CacheInterceptor):
            cache_interceptor = interceptor
            break

    assert cache_interceptor is not None

    # 验证：统计功能可用
    stats = cache_interceptor.get_stats()
    assert "singleflight_saved" in stats
    assert "singleflight_timeout" in stats
    assert "fail_open_count" in stats
    assert "null_cache_hits" in stats
    assert "cache_hits" in stats
    assert "cache_misses" in stats
