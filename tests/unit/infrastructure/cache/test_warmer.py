"""Tests for cache warmer."""

import asyncio

import pytest
import pytest_asyncio

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory, SerializerType
from bento.adapters.cache.warmer import CacheWarmer, WarmupStats

# ==================== Test Strategies ====================


class SimpleWarmupStrategy:
    """Simple test strategy."""

    def __init__(self, keys: list[str], data: dict[str, str]):
        self._keys = keys
        self._data = data

    async def get_keys_to_warmup(self) -> list[str]:
        return self._keys

    async def load_data(self, key: str) -> str | None:
        return self._data.get(key)

    def get_priority(self) -> int:
        return 0


class HighPriorityStrategy:
    """High priority test strategy."""

    async def get_keys_to_warmup(self) -> list[str]:
        return ["high:1", "high:2"]

    async def load_data(self, key: str) -> str:
        return f"data_{key}"

    def get_priority(self) -> int:
        return 100


class LowPriorityStrategy:
    """Low priority test strategy."""

    async def get_keys_to_warmup(self) -> list[str]:
        return ["low:1", "low:2"]

    async def load_data(self, key: str) -> str:
        return f"data_{key}"

    def get_priority(self) -> int:
        return 10


class SlowStrategy:
    """Slow loading strategy for concurrency testing."""

    def __init__(self, delay: float = 0.1):
        self._delay = delay
        self.load_count = 0

    async def get_keys_to_warmup(self) -> list[str]:
        return [f"key:{i}" for i in range(20)]

    async def load_data(self, key: str) -> str:
        await asyncio.sleep(self._delay)
        self.load_count += 1
        return f"data_{key}"

    def get_priority(self) -> int:
        return 0


class ErrorStrategy:
    """Strategy that raises errors."""

    async def get_keys_to_warmup(self) -> list[str]:
        return ["error:1", "error:2", "error:3"]

    async def load_data(self, key: str) -> str:
        if "2" in key:
            raise ValueError(f"Error loading {key}")
        return f"data_{key}"

    def get_priority(self) -> int:
        return 0


class CustomTTLStrategy:
    """Strategy with custom TTL."""

    async def get_keys_to_warmup(self) -> list[str]:
        return ["custom:1"]

    async def load_data(self, key: str) -> str:
        return "data"

    def get_priority(self) -> int:
        return 0

    def get_ttl(self) -> int:
        return 7200  # 2 hours


# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def cache():
    return await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, serializer=SerializerType.PICKLE)
    )


@pytest_asyncio.fixture
async def warmer(cache):
    return CacheWarmer(cache, max_concurrency=10, default_ttl=3600)


# ==================== Basic Warmup Tests ====================


@pytest.mark.asyncio
async def test_warmup_simple_strategy(warmer, cache):
    """测试基本预热功能"""
    strategy = SimpleWarmupStrategy(
        keys=["product:1", "product:2", "product:3"],
        data={
            "product:1": "data1",
            "product:2": "data2",
            "product:3": "data3",
        },
    )

    stats = await warmer.warmup(strategy)

    # 验证统计
    assert stats.total_keys == 3
    assert stats.warmed_keys == 3
    assert stats.failed_keys == 0
    assert stats.skipped_keys == 0
    assert stats.success_rate == 1.0

    # 验证缓存
    assert await cache.get("product:1") == "data1"
    assert await cache.get("product:2") == "data2"
    assert await cache.get("product:3") == "data3"


@pytest.mark.asyncio
async def test_warmup_with_missing_data(warmer, cache):
    """测试部分数据缺失的预热"""
    strategy = SimpleWarmupStrategy(
        keys=["key:1", "key:2", "key:3"],
        data={
            "key:1": "data1",
            # key:2 missing
            "key:3": "data3",
        },
    )

    stats = await warmer.warmup(strategy)

    # 验证统计
    assert stats.total_keys == 3
    assert stats.warmed_keys == 2  # 只有2个有数据
    assert stats.skipped_keys == 1  # 1个跳过
    assert stats.failed_keys == 0

    # 验证缓存
    assert await cache.get("key:1") == "data1"
    assert await cache.get("key:2") is None  # 未缓存
    assert await cache.get("key:3") == "data3"


@pytest.mark.asyncio
async def test_warmup_empty_keys(warmer):
    """测试空键列表"""
    strategy = SimpleWarmupStrategy(keys=[], data={})

    stats = await warmer.warmup(strategy)

    assert stats.total_keys == 0
    assert stats.warmed_keys == 0


# ==================== Concurrency Tests ====================


@pytest.mark.asyncio
async def test_warmup_concurrency(cache):
    """测试并发控制"""
    import time

    # 使用低并发数
    warmer = CacheWarmer(cache, max_concurrency=5)
    strategy = SlowStrategy(delay=0.1)

    start_time = time.time()
    stats = await warmer.warmup(strategy)
    duration = time.time() - start_time

    # 验证统计
    assert stats.total_keys == 20
    assert stats.warmed_keys == 20

    # 验证并发效果
    # 20个任务，每个0.1秒，最多5并发
    # 理论最快时间：20/5 * 0.1 = 0.4秒
    # 实际应该在0.4-0.6秒之间
    assert 0.3 < duration < 1.0, f"Duration {duration}s out of expected range"


# ==================== Error Handling Tests ====================


@pytest.mark.asyncio
async def test_warmup_with_errors(warmer, cache):
    """测试错误处理"""
    strategy = ErrorStrategy()

    stats = await warmer.warmup(strategy)

    # 验证统计
    assert stats.total_keys == 3
    assert stats.warmed_keys == 2  # error:1 和 error:3
    assert stats.failed_keys == 1  # error:2
    assert len(stats.errors) == 1

    # 验证缓存
    assert await cache.get("error:1") == "data_error:1"
    assert await cache.get("error:2") is None  # 失败未缓存
    assert await cache.get("error:3") == "data_error:3"


# ==================== Multiple Strategies Tests ====================


@pytest.mark.asyncio
async def test_warmup_multiple_strategies(warmer):
    """测试多策略预热"""
    strategies = [
        LowPriorityStrategy(),  # priority: 10
        HighPriorityStrategy(),  # priority: 100
    ]

    results = await warmer.warmup_multiple(strategies)

    # 验证两个策略都执行了
    assert len(results) == 2
    assert "HighPriorityStrategy" in results
    assert "LowPriorityStrategy" in results

    # 验证统计
    assert results["HighPriorityStrategy"].warmed_keys == 2
    assert results["LowPriorityStrategy"].warmed_keys == 2


@pytest.mark.asyncio
async def test_warmup_multiple_priority_order(warmer, cache):
    """测试多策略按优先级执行"""
    execution_order = []

    class TrackedHighStrategy:
        async def get_keys_to_warmup(self):
            execution_order.append("high")
            return ["h:1"]

        async def load_data(self, key: str):
            return "data"

        def get_priority(self):
            return 100

    class TrackedLowStrategy:
        async def get_keys_to_warmup(self):
            execution_order.append("low")
            return ["l:1"]

        async def load_data(self, key: str):
            return "data"

        def get_priority(self):
            return 10

    strategies = [
        TrackedLowStrategy(),  # 定义时是低优先级
        TrackedHighStrategy(),  # 定义时是高优先级
    ]

    await warmer.warmup_multiple(strategies)

    # 验证执行顺序（高优先级先执行）
    assert execution_order == ["high", "low"]


@pytest.mark.asyncio
async def test_warmup_multiple_with_errors(warmer):
    """测试多策略中有错误的情况"""
    strategies = [
        HighPriorityStrategy(),  # 正常
        ErrorStrategy(),  # 部分失败
        LowPriorityStrategy(),  # 正常
    ]

    results = await warmer.warmup_multiple(strategies)

    # 验证：所有策略都执行了
    assert len(results) == 3
    assert results["HighPriorityStrategy"].warmed_keys == 2
    assert results["ErrorStrategy"].failed_keys == 1  # 有1个失败
    assert results["LowPriorityStrategy"].warmed_keys == 2


# ==================== Custom TTL Tests ====================


@pytest.mark.asyncio
async def test_warmup_custom_ttl(cache):
    """测试自定义TTL"""
    warmer = CacheWarmer(cache, default_ttl=1000)
    strategy = CustomTTLStrategy()

    await warmer.warmup(strategy)

    # 验证缓存已设置（TTL由策略决定）
    data = await cache.get("custom:1")
    assert data == "data"


# ==================== Single Key Warmup Tests ====================


@pytest.mark.asyncio
async def test_warmup_single_key(warmer, cache):
    """测试单键预热"""

    async def load_data(key: str) -> str:
        return f"data_for_{key}"

    success = await warmer.warmup_single_key("test:key", load_data)

    assert success is True
    assert await cache.get("test:key") == "data_for_test:key"


@pytest.mark.asyncio
async def test_warmup_single_key_with_error(warmer, cache):
    """测试单键预热错误处理"""

    async def load_with_error(key: str) -> str:
        raise ValueError("Load error")

    success = await warmer.warmup_single_key("error:key", load_with_error)

    assert success is False
    assert await cache.get("error:key") is None


# ==================== Progress Callback Tests ====================


@pytest.mark.asyncio
async def test_warmup_with_progress_callback(warmer):
    """测试进度回调"""
    progress_calls = []

    async def on_progress(current: int, total: int):
        progress_calls.append((current, total))

    strategy = SimpleWarmupStrategy(
        keys=["k:1", "k:2", "k:3"], data={"k:1": "d1", "k:2": "d2", "k:3": "d3"}
    )

    await warmer.warmup(strategy, progress_callback=on_progress)

    # 验证进度回调被调用
    assert len(progress_calls) == 3
    assert progress_calls[-1] == (3, 3)  # 最后一次是100%


# ==================== Stats Tests ====================


@pytest.mark.asyncio
async def test_warmup_stats_string_representation():
    """测试统计信息字符串表示"""
    stats = WarmupStats(
        total_keys=100, warmed_keys=80, failed_keys=10, skipped_keys=10, duration_seconds=5.5
    )

    str_repr = str(stats)

    assert "total=100" in str_repr
    assert "warmed=80" in str_repr
    assert "failed=10" in str_repr
    assert "success_rate=80.0%" in str_repr


@pytest.mark.asyncio
async def test_warmup_stats_success_rate():
    """测试成功率计算"""
    stats = WarmupStats(total_keys=100, warmed_keys=75)
    assert stats.success_rate == 0.75

    empty_stats = WarmupStats(total_keys=0)
    assert empty_stats.success_rate == 0.0
