# 缓存预热架构设计

## 🎯 **设计原则**

基于 **DDD** 和 **六边形架构** 原则：

> **框架提供机制（Mechanism），应用提供策略（Policy）**

---

## 📐 **架构分层**

### Bento Framework（基础设施层）

**职责：提供缓存预热的通用机制和工具**

✅ **应该提供：**
1. 缓存预热基础接口
2. 批量预热工具
3. 进度追踪机制
4. 统计和监控
5. 并发控制

❌ **不应该提供：**
1. 具体的业务逻辑
2. 领域特定的预热策略
3. 数据源选择

---

### Application Layer（应用层）

**职责：定义具体的预热策略和业务逻辑**

✅ **应该实现：**
1. 哪些数据需要预热
2. 预热的优先级
3. 预热的时机
4. 预热的数据源
5. 业务规则

---

## 🏗️ **实现方案**

### 方案：框架提供机制 + 应用实现策略

```
┌─────────────────────────────────────────────────────────┐
│  Application Layer (应用层)                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  ProductCacheWarmupStrategy                       │  │
│  │  - 预热热销商品                                    │  │
│  │  - 预热分类数据                                    │  │
│  │  - 预热推荐数据                                    │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓ 使用                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  CacheWarmupService (应用服务)                     │  │
│  │  - orchestrate warmup strategies                  │  │
│  │  - handle timing and priorities                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓ 依赖
┌─────────────────────────────────────────────────────────┐
│  Bento Framework (基础设施层)                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  CacheWarmup Protocol (接口/抽象)                  │  │
│  │  - warmup_single()                                │  │
│  │  - warmup_batch()                                 │  │
│  │  - track_progress()                               │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  CacheWarmer (实现)                               │  │
│  │  - 批量预热工具                                    │  │
│  │  - 并发控制                                        │  │
│  │  - 进度追踪                                        │  │
│  │  - 统计监控                                        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 **框架实现（Bento Framework）**

### 1. 缓存预热协议

```python
# src/bento/application/ports/cache_warmup.py
"""Cache warmup protocol."""

from typing import Protocol, TypeVar, Callable, Any
from collections.abc import Awaitable

T = TypeVar("T")


class CacheWarmupStrategy(Protocol[T]):
    """Cache warmup strategy protocol.

    Applications should implement this protocol to define
    their specific warmup logic.
    """

    async def get_keys_to_warmup(self) -> list[str]:
        """Get list of cache keys to warmup.

        Returns:
            List of cache keys that need to be warmed up
        """
        ...

    async def load_data(self, key: str) -> T | None:
        """Load data for a specific key.

        Args:
            key: Cache key to load data for

        Returns:
            Data to cache, or None if not found
        """
        ...

    def get_priority(self) -> int:
        """Get warmup priority (higher = more important).

        Returns:
            Priority value (default: 0)
        """
        return 0
```

### 2. 缓存预热器（通用工具）

```python
# src/bento/infrastructure/cache/warmer.py
"""Cache warmer implementation."""

import asyncio
import logging
from typing import TypeVar, Generic, Any
from dataclasses import dataclass

from bento.application.ports.cache import Cache
from bento.application.ports.cache_warmup import CacheWarmupStrategy

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class WarmupStats:
    """Warmup statistics."""
    total_keys: int = 0
    warmed_keys: int = 0
    failed_keys: int = 0
    duration_seconds: float = 0.0


class CacheWarmer(Generic[T]):
    """Generic cache warmer.

    Provides mechanisms for cache warmup with:
    - Batch processing
    - Concurrency control
    - Progress tracking
    - Error handling

    Example:
        ```python
        # Framework provides the warmer
        warmer = CacheWarmer(cache, max_concurrency=10)

        # Application provides the strategy
        await warmer.warmup(my_product_strategy)
        ```
    """

    def __init__(
        self,
        cache: Cache,
        *,
        max_concurrency: int = 10,
        batch_size: int = 100,
        ttl: int = 3600,
    ) -> None:
        """Initialize cache warmer.

        Args:
            cache: Cache instance
            max_concurrency: Max concurrent warmup tasks
            batch_size: Batch size for processing
            ttl: Default TTL for warmed cache entries
        """
        self._cache = cache
        self._max_concurrency = max_concurrency
        self._batch_size = batch_size
        self._ttl = ttl
        self._stats = WarmupStats()

    async def warmup(
        self,
        strategy: CacheWarmupStrategy[T],
        *,
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> WarmupStats:
        """Warmup cache using provided strategy.

        Args:
            strategy: Warmup strategy (application-provided)
            progress_callback: Optional callback(current, total)

        Returns:
            Warmup statistics
        """
        import time
        start_time = time.time()

        # Get keys from strategy (application logic)
        keys = await strategy.get_keys_to_warmup()
        self._stats.total_keys = len(keys)

        logger.info(f"Starting cache warmup: {len(keys)} keys")

        # Process in batches with concurrency control
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def warmup_key(key: str) -> None:
            async with semaphore:
                try:
                    # Load data using strategy (application logic)
                    data = await strategy.load_data(key)

                    if data is not None:
                        # Cache the data (framework mechanism)
                        await self._cache.set(key, data, ttl=self._ttl)
                        self._stats.warmed_keys += 1
                    else:
                        self._stats.failed_keys += 1

                    # Progress callback
                    if progress_callback:
                        await progress_callback(
                            self._stats.warmed_keys + self._stats.failed_keys,
                            self._stats.total_keys
                        )

                except Exception as e:
                    logger.error(f"Failed to warmup key {key}: {e}")
                    self._stats.failed_keys += 1

        # Execute warmup tasks
        tasks = [warmup_key(key) for key in keys]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._stats.duration_seconds = time.time() - start_time

        logger.info(
            f"Cache warmup completed: "
            f"{self._stats.warmed_keys}/{self._stats.total_keys} keys, "
            f"{self._stats.duration_seconds:.2f}s"
        )

        return self._stats

    async def warmup_multiple(
        self,
        strategies: list[CacheWarmupStrategy[Any]],
    ) -> dict[str, WarmupStats]:
        """Warmup cache using multiple strategies.

        Strategies are executed in priority order.

        Args:
            strategies: List of warmup strategies

        Returns:
            Statistics per strategy
        """
        # Sort by priority (higher first)
        sorted_strategies = sorted(
            strategies,
            key=lambda s: s.get_priority(),
            reverse=True
        )

        results = {}
        for strategy in sorted_strategies:
            strategy_name = strategy.__class__.__name__
            logger.info(f"Executing warmup strategy: {strategy_name}")

            stats = await self.warmup(strategy)
            results[strategy_name] = stats

        return results

    def get_stats(self) -> WarmupStats:
        """Get current warmup statistics."""
        return self._stats
```

---

## 📝 **应用实现示例**

### 1. 定义预热策略（应用层）

```python
# applications/my-shop/warmup/strategies.py
"""Application-specific cache warmup strategies."""

from bento.application.ports.cache_warmup import CacheWarmupStrategy
from contexts.catalog.domain.product import Product
from contexts.catalog.application.cqrs import QueryHandler


class HotProductsWarmupStrategy:
    """预热热销商品缓存.

    业务逻辑：预热最近30天销量前100的商品
    """

    def __init__(self, product_service: ProductService):
        self._product_service = product_service

    async def get_keys_to_warmup(self) -> list[str]:
        """获取需要预热的商品ID."""
        # 业务逻辑：从数据库查询热销商品
        hot_products = await self._product_service.get_hot_products(
            days=30,
            limit=100
        )
        return [f"Product:id:{p.id}" for p in hot_products]

    async def load_data(self, key: str) -> Product | None:
        """加载商品数据."""
        product_id = key.split(":")[-1]
        return await self._product_service.get_by_id(product_id)

    def get_priority(self) -> int:
        """高优先级（热销商品最重要）."""
        return 100


class CategoryCacheWarmupStrategy:
    """预热分类缓存.

    业务逻辑：预热所有一级和二级分类
    """

    def __init__(self, category_service):
        self._category_service = category_service

    async def get_keys_to_warmup(self) -> list[str]:
        """获取需要预热的分类."""
        # 业务逻辑：查询所有一级和二级分类
        categories = await self._category_service.get_categories(
            max_level=2
        )
        return [f"Category:id:{c.id}" for c in categories]

    async def load_data(self, key: str) -> Any:
        category_id = key.split(":")[-1]
        return await self._category_service.get_by_id(category_id)

    def get_priority(self) -> int:
        """中优先级."""
        return 50


class RecommendationWarmupStrategy:
    """预热推荐数据缓存."""

    def __init__(self, recommendation_service):
        self._recommendation_service = recommendation_service

    async def get_keys_to_warmup(self) -> list[str]:
        # 业务逻辑：预热热门推荐位
        return ["recommendations:homepage", "recommendations:trending"]

    async def load_data(self, key: str) -> Any:
        if key == "recommendations:homepage":
            return await self._recommendation_service.get_homepage_recommendations()
        elif key == "recommendations:trending":
            return await self._recommendation_service.get_trending_products()
        return None

    def get_priority(self) -> int:
        """中等优先级."""
        return 60
```

### 2. 应用启动时执行预热

```python
# applications/my-shop/app.py
"""Application startup with cache warmup."""

from fastapi import FastAPI
from bento.adapters.cache import CacheFactory, CacheConfig, CacheBackend
from bento.infrastructure.cache.warmer import CacheWarmer

from warmup.strategies import (
    HotProductsWarmupStrategy,
    CategoryCacheWarmupStrategy,
    RecommendationWarmupStrategy,
)

app = FastAPI()


@app.on_event("startup")
async def startup():
    # 1. 创建缓存
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.REDIS)
    )

    # 2. 创建预热器（框架提供）
    warmer = CacheWarmer(
        cache,
        max_concurrency=20,  # 并发控制
        ttl=3600,            # 1小时TTL
    )

    # 3. 定义预热策略（应用提供）
    strategies = [
        HotProductsWarmupStrategy(product_service),      # 高优先级
        RecommendationWarmupStrategy(rec_service),       # 中优先级
        CategoryCacheWarmupStrategy(category_service),   # 中优先级
    ]

    # 4. 执行预热
    print("🔥 开始缓存预热...")
    results = await warmer.warmup_multiple(strategies)

    # 5. 打印结果
    for strategy_name, stats in results.items():
        print(f"  ✅ {strategy_name}:")
        print(f"     - 预热键数: {stats.warmed_keys}/{stats.total_keys}")
        print(f"     - 耗时: {stats.duration_seconds:.2f}s")
```

### 3. 定时预热

```python
# applications/my-shop/tasks/warmup.py
"""Scheduled cache warmup tasks."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job('cron', hour=2)  # 每天凌晨2点
async def nightly_cache_warmup():
    """夜间缓存预热."""
    print("🌙 执行夜间缓存预热...")

    warmer = CacheWarmer(cache, max_concurrency=50)

    # 预热所有数据（低峰期，可以全量）
    strategies = [
        HotProductsWarmupStrategy(product_service),
        CategoryCacheWarmupStrategy(category_service),
        RecommendationWarmupStrategy(rec_service),
    ]

    results = await warmer.warmup_multiple(strategies)
    print(f"✅ 预热完成: {sum(s.warmed_keys for s in results.values())} keys")


@scheduler.scheduled_job('interval', minutes=30)
async def incremental_warmup():
    """增量预热（仅热点数据）."""
    warmer = CacheWarmer(cache, max_concurrency=10)

    # 只预热热销商品（增量）
    strategy = HotProductsWarmupStrategy(product_service)
    stats = await warmer.warmup(strategy)

    print(f"🔄 增量预热完成: {stats.warmed_keys} keys")


# 启动调度器
scheduler.start()
```

---

## 📊 **职责对比**

| 功能 | Bento Framework | Application |
|------|-----------------|-------------|
| **预热机制** | ✅ 提供 | ❌ 使用 |
| **批量处理** | ✅ 提供 | ❌ 使用 |
| **并发控制** | ✅ 提供 | ❌ 配置 |
| **进度追踪** | ✅ 提供 | ❌ 可选使用 |
| **统计监控** | ✅ 提供 | ❌ 使用 |
| **业务逻辑** | ❌ 不提供 | ✅ 实现 |
| **数据源** | ❌ 不关心 | ✅ 决定 |
| **预热策略** | ❌ 不定义 | ✅ 定义 |
| **预热时机** | ❌ 不决定 | ✅ 决定 |
| **优先级** | ❌ 不决定 | ✅ 决定 |

---

## 🎯 **设计优势**

### 1. **关注点分离**

- **框架：** 专注于技术实现（如何预热）
- **应用：** 专注于业务逻辑（预热什么）

### 2. **高内聚低耦合**

- 框架不依赖具体业务
- 应用可以自由定义策略
- 两者通过接口解耦

### 3. **灵活性**

- 应用可以定义任意数量的策略
- 可以动态调整优先级
- 可以根据业务变化调整

### 4. **可测试性**

```python
# 框架测试（通用性）
async def test_cache_warmer_basic():
    warmer = CacheWarmer(cache)
    strategy = MockStrategy()  # 简单mock
    stats = await warmer.warmup(strategy)
    assert stats.warmed_keys > 0

# 应用测试（业务逻辑）
async def test_hot_products_strategy():
    strategy = HotProductsWarmupStrategy(product_service)
    keys = await strategy.get_keys_to_warmup()
    assert len(keys) == 100  # 业务规则：前100个
```

---

## ✅ **总结**

### 推荐方案

**框架层（Bento）：**
```
✅ 提供 CacheWarmupStrategy 协议
✅ 提供 CacheWarmer 工具类
✅ 提供 批量处理、并发控制、统计监控
```

**应用层（my-shop）：**
```
✅ 实现具体的预热策略
✅ 定义业务规则和优先级
✅ 决定预热时机和数据源
```

### 为什么这样设计？

1. **符合 DDD 原则**
   - 领域逻辑在应用层
   - 技术实现在基础设施层

2. **符合六边形架构**
   - 框架是端口（Port）
   - 应用是适配器（Adapter）

3. **符合开闭原则**
   - 框架对扩展开放（可以实现任意策略）
   - 框架对修改封闭（不需要修改框架代码）

4. **符合单一职责**
   - 框架：提供机制
   - 应用：提供策略

**这样设计既保持了框架的通用性，又给了应用足够的灵活性！** ✅
