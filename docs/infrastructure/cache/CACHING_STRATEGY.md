# Repository Mixins 缓存策略指南

## 🎯 核心原则

### 什么时候需要缓存？

1. **高频访问** - 查询频率 > 1次/秒
2. **计算密集** - 聚合、统计、分组操作
3. **数据相对稳定** - 变化频率低于查询频率
4. **对实时性要求不高** - 可以容忍几分钟的延迟

### 什么时候不需要缓存？

1. **实时性要求高** - 库存、余额等
2. **数据变化频繁** - 每秒都在更新
3. **低频查询** - 每天只查询几次
4. **随机性要求** - random 相关方法

## 📊 Mixins 方法缓存建议

### ✅ 强烈推荐缓存（计算密集型）

```python
from bento.adapters.cache.decorators import cached

class OrderAnalyticsService:

    @cached(ttl=300, key_prefix="order:total_revenue")
    async def get_total_revenue(self) -> float:
        """总收入 - 缓存5分钟"""
        return await self._repo.sum_field("total")

    @cached(ttl=600, key_prefix="order:avg_order")
    async def get_average_order_value(self) -> float:
        """平均订单金额 - 缓存10分钟"""
        return await self._repo.avg_field("total")

    @cached(ttl=3600, key_prefix="order:status_dist")
    async def get_order_status_distribution(self) -> dict[str, int]:
        """状态分布 - 缓存1小时"""
        return await self._repo.group_by_field("status")

    @cached(ttl=86400, key_prefix="order:daily_trend")
    async def get_daily_order_trend(self) -> dict[str, int]:
        """每日趋势 - 历史数据缓存24小时"""
        return await self._repo.group_by_date("created_at", "day")
```

### ⚠️ 可选缓存（取决于场景）

```python
class ProductEnhancedService:

    @cached(ttl=60, key_prefix="product:latest")
    async def get_latest_product(self) -> Product | None:
        """最新产品 - 短期缓存1分钟"""
        return await self._repo.find_first(order_by="-created_at")

    @cached(ttl=300, key_prefix="product:top_expensive:{limit}")
    async def get_top_expensive_products(self, limit: int = 10) -> list[Product]:
        """Top N 最贵产品 - 缓存5分钟"""
        return await self._repo.find_top_n(limit, order_by="-price")
```

### ❌ 不推荐缓存

```python
class ProductEnhancedService:

    # ❌ 不要缓存：实时性要求高
    async def check_product_exists(self, product_id: ID) -> bool:
        return await self._repo.exists_by_id(product_id)

    # ❌ 不要缓存：每次都应该不同
    async def get_random_product(self) -> Product | None:
        return await self._repo.find_random()

    # ❌ 不要缓存：唯一性检查需要实时
    async def verify_sku_unique(self, sku: str) -> bool:
        return await self._repo.is_unique("sku", sku)
```

## 🔧 实现方案

### 方案1：使用装饰器（推荐）

**优点**：
- 简单易用
- 可以针对每个方法自定义 TTL
- 不侵入 Repository 层

**使用方式**：

```python
from bento.adapters.cache import MemoryCache, cached

# 初始化缓存
cache = MemoryCache()

class OrderAnalyticsService:
    def __init__(self, order_repo, cache):
        self._repo = order_repo
        self._cache = cache

    @cached(cache, ttl=300, key="order:revenue")
    async def get_total_revenue(self) -> float:
        return await self._repo.sum_field("total")
```

### 方案2：Repository 包装器

**优点**：
- 对调用方透明
- 统一的缓存策略

**实现**：

```python
class CachedRepository:
    """Repository 缓存包装器"""

    def __init__(self, repo, cache, default_ttl=300):
        self._repo = repo
        self._cache = cache
        self._default_ttl = default_ttl

    async def sum_field(self, field: str, spec=None) -> float:
        """带缓存的 sum_field"""
        cache_key = f"{self._repo.__class__.__name__}:sum:{field}"
        if spec:
            cache_key += f":{hash(str(spec))}"

        # 尝试从缓存获取
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        # 执行查询
        result = await self._repo.sum_field(field, spec)

        # 写入缓存
        await self._cache.set(cache_key, result, ttl=self._default_ttl)
        return result

    # 其他方法类似...
```

### 方案3：配置化缓存策略

```python
# config/cache_config.py
CACHE_STRATEGIES = {
    # 聚合查询 - 长期缓存
    "aggregate": {
        "ttl": 3600,
        "methods": ["sum_field", "avg_field", "min_field", "max_field", "count_field"]
    },

    # 分组统计 - 长期缓存
    "groupby": {
        "ttl": 3600,
        "methods": ["group_by_field", "group_by_date", "group_by_multiple_fields"]
    },

    # 排序查询 - 短期缓存
    "sorting": {
        "ttl": 300,
        "methods": ["find_first", "find_last", "find_top_n"]
    },

    # 存在性检查 - 短期缓存
    "existence": {
        "ttl": 60,
        "methods": ["exists_by_id", "exists_by_ids"]
    }
}
```

## 🔄 缓存失效策略

### 自动失效

```python
class OrderAnalyticsService:

    async def create_order(self, command) -> Order:
        """创建订单"""
        order = await self._order_service.create(command)

        # 自动失效相关缓存
        await self._cache.delete_pattern("order:*")

        return order
```

### 智能失效

```python
class CacheInvalidationHandler:
    """缓存失效处理器"""

    async def handle_order_created(self, event: OrderCreated):
        """订单创建后失效统计缓存"""
        # 失效聚合统计
        await cache.delete("order:total_revenue")
        await cache.delete("order:avg_order")
        await cache.delete("order:count")

        # 失效分组统计
        await cache.delete("order:status_dist")
        await cache.delete("order:daily_trend")
```

### 定时刷新

```python
import asyncio

async def refresh_cache_periodically():
    """定时刷新缓存"""
    while True:
        # 每小时刷新一次统计数据
        await asyncio.sleep(3600)

        # 预热缓存
        await analytics_service.get_total_revenue()
        await analytics_service.get_daily_trend()
```

## 📊 缓存 TTL 建议

| 数据类型 | TTL | 说明 |
|---------|-----|------|
| 实时统计 | 60s | 总收入、订单数等 |
| 分类统计 | 5-10分钟 | 类别分布、状态分布 |
| 排行榜 | 5-15分钟 | Top N 产品 |
| 历史数据 | 1-24小时 | 每日/每月统计 |
| 聚合计算 | 10-30分钟 | sum, avg, min, max |

## ⚡ 性能对比

### 不使用缓存

```python
# 每次都查询数据库
async def get_dashboard():
    return {
        "revenue": await repo.sum_field("total"),      # 100ms
        "avg": await repo.avg_field("total"),          # 100ms
        "count": await repo.count_field("id"),         # 50ms
        "distribution": await repo.group_by_field(),   # 200ms
    }
# 总耗时：450ms
```

### 使用缓存（第二次请求）

```python
# 从缓存读取
async def get_dashboard():
    return {
        "revenue": await cached_service.get_revenue(),  # 2ms
        "avg": await cached_service.get_avg(),          # 2ms
        "count": await cached_service.get_count(),      # 2ms
        "distribution": await cached_service.get_dist(),# 2ms
    }
# 总耗时：8ms（性能提升 56x）
```

## 💡 最佳实践

### 1. 渐进式采用

```python
# 第一步：只缓存最频繁的查询
@cached(ttl=300)
async def get_total_revenue():
    ...

# 第二步：监控缓存命中率
# 第三步：逐步扩展到其他方法
```

### 2. 监控缓存效果

```python
from bento.adapters.cache.stats import CacheStats

stats = CacheStats(cache)

# 查看缓存统计
print(f"命中率: {stats.hit_rate}%")
print(f"命中次数: {stats.hits}")
print(f"未命中次数: {stats.misses}")
```

### 3. 缓存预热

```python
async def warmup_cache():
    """应用启动时预热缓存"""
    print("预热缓存中...")

    # 预加载常用统计
    await analytics_service.get_total_revenue()
    await analytics_service.get_order_status_distribution()
    await analytics_service.get_daily_trend()

    print("缓存预热完成")
```

## 🎯 总结

### 需要缓存的场景

- ✅ 高频访问的聚合统计（sum, avg, count）
- ✅ 分组统计和趋势分析
- ✅ Top N 排行榜
- ✅ 历史数据查询

### 不需要缓存的场景

- ❌ 实时性要求高的查询
- ❌ 随机采样方法
- ❌ 唯一性验证
- ❌ 低频查询

### 推荐工具

- **应用层缓存**: `@cached` 装饰器
- **缓存后端**: Redis（生产）、MemoryCache（开发）
- **失效策略**: 事件驱动自动失效

---

**记住**：缓存是性能优化的利器，但也要注意数据一致性问题。在生产环境中，建议从最高频的查询开始逐步采用缓存策略。
