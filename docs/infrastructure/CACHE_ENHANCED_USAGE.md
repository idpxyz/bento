# 缓存增强功能使用指南

**版本**: 2.0  
**最后更新**: 2025-11-04

---

## 📖 新增功能

本指南介绍缓存系统的两大增强功能：

1. ✅ **监控统计** (CacheStats) - 实时监控缓存性能
2. ✅ **防击穿机制** (Breakdown Protection) - 防止缓存失效时的并发查询

---

## 🎯 功能 1: 缓存监控统计

### 什么是缓存统计？

缓存统计帮助你了解缓存的性能表现，包括：
- 命中率（Hit Rate）
- 响应时间
- 操作次数

### 基础用法

```python
from adapters.cache import create_cache

# 创建缓存（默认启用统计）
cache = await create_cache(backend="memory", prefix="myapp:")

# 执行操作
await cache.set("user:123", user_data)
await cache.get("user:123")  # Hit
await cache.get("user:999")  # Miss

# 获取统计信息
stats = cache.get_stats()
if stats:
    print(f"Hit Rate: {stats['hit_rate']:.2%}")
    print(f"Total Operations: {stats['total_operations']}")
    print(f"Avg Get Time: {stats['avg_get_time']:.4f}s")
```

### 统计指标详解

| 指标 | 说明 | 用途 |
|------|------|------|
| `hits` | 缓存命中次数 | 衡量缓存有效性 |
| `misses` | 缓存未命中次数 | 识别未缓存的数据 |
| `hit_rate` | 命中率 (0.0-1.0) | **最重要指标** |
| `sets` | 写入次数 | 监控写入频率 |
| `deletes` | 删除次数 | 监控失效操作 |
| `errors` | 错误次数 | 发现问题 |
| `avg_get_time` | 平均读取时间 | 性能监控 |
| `avg_set_time` | 平均写入时间 | 性能监控 |
| `uptime` | 运行时间 | 统计周期 |

### 完整示例

```python
from adapters.cache import create_cache
import json

# 创建缓存
cache = await create_cache(backend="memory", prefix="user:", ttl=3600)

# 模拟业务操作
for i in range(100):
    await cache.set(f"user:{i}", {"id": i, "name": f"User{i}"})

# 模拟查询（80% 命中，20% 未命中）
for _ in range(1000):
    user_id = random.randint(0, 119)  # 0-99存在，100-119不存在
    await cache.get(f"user:{user_id}")

# 查看统计
stats = cache.get_stats()
print(json.dumps(stats, indent=2))

# 输出示例：
# {
#   "hits": 800,
#   "misses": 200,
#   "hit_rate": 0.8,
#   "total_operations": 1100,
#   "avg_get_time": 0.000023,
#   ...
# }

# 重置统计（用于周期性监控）
cache.reset_stats()
```

### 禁用统计

如果不需要统计（提升性能）：

```python
config = CacheConfig(
    backend=CacheBackend.MEMORY,
    enable_stats=False  # 禁用统计
)
cache = MemoryCache(config)
```

---

## 🛡️ 功能 2: 防缓存击穿

### 什么是缓存击穿？

**问题场景**：
- 热点数据（如首页内容）的缓存过期
- 瞬间大量请求同时访问
- 所有请求都穿透到数据库
- **数据库瞬间被打垮** ❌

```python
# ❌ 没有防护的代码
async def get_hot_data(key):
    cached = await cache.get(key)
    if cached:
        return cached
    
    # 缓存失效时，100个并发请求都会执行这里！
    data = await expensive_db_query()  # 数据库压力爆炸 💥
    await cache.set(key, data)
    return data
```

### 解决方案：互斥锁

使用 `get_or_set()` 方法，确保同一时间只有一个请求查询数据库：

```python
# ✅ 有防护的代码
async def get_hot_data(key):
    return await cache.get_or_set(
        key,
        loader=expensive_db_query,  # 只有一个请求会执行
        ttl=3600
    )

# 100个并发请求 → 只有1个查询数据库，其他等待并共享结果！
```

### Memory Cache 防击穿（本地锁）

```python
from adapters.cache import create_cache

cache = await create_cache(backend="memory")

async def load_user_from_db(user_id):
    """模拟慢速数据库查询"""
    await asyncio.sleep(2)  # 2秒
    return {"id": user_id, "name": f"User{user_id}"}

# 使用 get_or_set 防击穿
user = await cache.get_or_set(
    f"user:{user_id}",
    lambda: load_user_from_db(user_id),
    ttl=3600
)

# 即使100个并发请求，也只会执行1次数据库查询！
```

### Redis Cache 防击穿（分布式锁）

```python
from adapters.cache import create_cache

cache = await create_cache(
    backend="redis",
    redis_url="redis://localhost:6379/0"
)

# 多个服务实例并发请求
# 使用 Redis SETNX 实现分布式锁
user = await cache.get_or_set(
    f"user:{user_id}",
    lambda: load_user_from_db(user_id),
    ttl=3600,
    lock_timeout=10  # 锁超时时间
)

# 跨服务的并发请求也只会执行1次数据库查询！
```

### 工作原理

#### Memory Cache（本地）
```
请求1: 获取锁 ✅ → 查询DB → 缓存结果 → 释放锁
请求2: 等待锁... → 从缓存获取 ✅
请求3: 等待锁... → 从缓存获取 ✅
...
请求100: 等待锁... → 从缓存获取 ✅
```

#### Redis Cache（分布式）
```
服务A-请求1: SETNX成功 ✅ → 查询DB → 缓存结果 → DEL锁
服务B-请求2: SETNX失败 → 轮询等待 → 从缓存获取 ✅
服务C-请求3: SETNX失败 → 轮询等待 → 从缓存获取 ✅
```

### 配置选项

```python
# 启用/禁用防击穿
config = CacheConfig(
    enable_breakdown_protection=True  # 默认启用
)

# 环境变量
# CACHE_ENABLE_BREAKDOWN_PROTECTION=true
```

---

## 📊 性能对比

### 测试场景

- 热点数据缓存过期
- 100个并发请求
- 数据库查询耗时：2秒

### 结果对比

| 场景 | 数据库查询次数 | 总耗时 | 结果 |
|------|---------------|--------|------|
| **无防护** | 100次 | ~2秒 | ❌ 数据库崩溃 |
| **有防护** | 1次 | ~2秒 | ✅ 性能稳定 |

### 代码示例

```python
import asyncio
import time

db_query_count = 0

async def slow_db_query():
    global db_query_count
    db_query_count += 1
    await asyncio.sleep(2)
    return {"data": "value"}

# ❌ 无防护
async def without_protection():
    global db_query_count
    db_query_count = 0
    
    async def get_data(cache, key):
        cached = await cache.get(key)
        if cached:
            return cached
        data = await slow_db_query()
        await cache.set(key, data)
        return data
    
    tasks = [get_data(cache, "key") for _ in range(100)]
    start = time.time()
    await asyncio.gather(*tasks)
    
    print(f"DB Queries: {db_query_count}")  # 100次！❌
    print(f"Time: {time.time() - start:.2f}s")

# ✅ 有防护
async def with_protection():
    global db_query_count
    db_query_count = 0
    
    tasks = [
        cache.get_or_set("key", slow_db_query)
        for _ in range(100)
    ]
    start = time.time()
    await asyncio.gather(*tasks)
    
    print(f"DB Queries: {db_query_count}")  # 1次！✅
    print(f"Time: {time.time() - start:.2f}s")
```

---

## 🎯 最佳实践

### 1. 始终启用统计（生产环境）

```python
# 监控缓存性能
stats = cache.get_stats()
if stats['hit_rate'] < 0.7:
    logger.warning("Cache hit rate too low!")
```

### 2. 热点数据必须防击穿

```python
# 首页、热门商品等高并发场景
hot_product = await cache.get_or_set(
    f"product:{product_id}",
    lambda: db.get_product(product_id),
    ttl=3600
)
```

### 3. 定期重置统计

```python
# 每天重置统计
async def daily_reset():
    cache.reset_stats()

# 定时任务
scheduler.add_job(daily_reset, 'cron', hour=0)
```

### 4. 监控关键指标

```python
# Prometheus metrics
from prometheus_client import Gauge

cache_hit_rate = Gauge('cache_hit_rate', 'Cache hit rate')

async def update_metrics():
    stats = cache.get_stats()
    if stats:
        cache_hit_rate.set(stats['hit_rate'])
```

---

## 🔧 环境变量配置

```bash
# 启用统计（默认）
CACHE_ENABLE_STATS=true

# 启用防击穿（默认）
CACHE_ENABLE_BREAKDOWN_PROTECTION=true

# 禁用统计（提升性能）
CACHE_ENABLE_STATS=false

# 禁用防击穿（特殊场景）
CACHE_ENABLE_BREAKDOWN_PROTECTION=false
```

---

## 📝 完整示例

查看：`examples/cache/breakdown_protection_example.py`

运行示例：
```bash
python examples/cache/breakdown_protection_example.py
```

---

## 💡 总结

| 功能 | 用途 | 默认状态 |
|------|------|---------|
| **监控统计** | 性能分析、问题诊断 | ✅ 启用 |
| **防击穿** | 保护数据库、提升稳定性 | ✅ 启用 |

**推荐**: 两个功能都保持启用，对性能影响极小但收益巨大！

---

查看更多：
- 基础用法：`docs/infrastructure/CACHE_USAGE.md`
- 示例代码：`examples/cache/`

