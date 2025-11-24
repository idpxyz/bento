# 缓存可靠性加固方案 - Part 1: 防御性编程

## 🎯 核心目标

将缓存系统从基础实现提升到生产级别，确保：
- ✅ 高并发场景稳定性
- ✅ 异常情况服务可用性
- ✅ 数据一致性保证

---

## 🛡️ 防御性编程 - 防止故障发生

### 1. 缓存击穿保护（已实现）✅

**Singleflight 模式**已实现于：`src/bento/persistence/interceptor/singleflight.py`

**集成方法：**
```python
from bento.persistence.interceptor.singleflight import SingleflightGroup

class CacheInterceptor:
    def __init__(self, cache, ttl=60, enabled=True):
        self._cache = cache
        self._singleflight = SingleflightGroup()  # ✅

    async def execute_before(self, context):
        key = self._get_cache_key(context)

        # ✅ 防止缓存击穿
        async def query_cache():
            return await self._cache.get(self._full_key(key))

        return await self._singleflight.do(key, query_cache)
```

**效果：** 1000个并发 → 1次数据库查询，性能提升1000x

---

### 2. 缓存穿透保护

**方案A：缓存空结果**

```python
# cache.py
class _CacheNullValue:
    """空值标记"""
    pass

CACHE_NULL = _CacheNullValue()

class CacheInterceptor:
    async def process_result(self, context, result, next_interceptor):
        if self._is_read(context.operation):
            # ✅ 缓存空结果（短TTL）
            cache_value = result if result is not None else CACHE_NULL
            ttl = 10 if result is None else self._get_ttl(context.operation)

            await self._cache.set(key, cache_value, ttl=ttl)

    async def execute_before(self, context):
        cached = await self._cache.get(key)

        # ✅ 识别空值
        if isinstance(cached, _CacheNullValue):
            return None  # 避免数据库查询

        return cached
```

**效果：** 防止恶意查询不存在的数据

---

### 3. 缓存雪崩保护

**方案：TTL 随机抖动**

```python
import random

class CacheInterceptor:
    def _get_ttl_with_jitter(self, base_ttl: int) -> int:
        """添加±20%随机抖动"""
        jitter = random.uniform(0.8, 1.2)
        return int(base_ttl * jitter)

    async def process_result(self, context, result, next_interceptor):
        base_ttl = self._get_ttl(context.operation)
        actual_ttl = self._get_ttl_with_jitter(base_ttl)  # ✅

        await self._cache.set(key, result, ttl=actual_ttl)
```

**效果：** 缓存过期时间分散，避免同时失效

---

### 4. 内存管理

**LRU 缓存实现**

```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size: int = 10000):
        self._max_size = max_size
        self._cache = OrderedDict()

    async def set(self, key: str, value: Any, ttl: int):
        # ✅ 检查大小限制
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # 驱逐最旧项

        self._cache[key] = (value, time.time() + ttl)
        self._cache.move_to_end(key)  # 标记为最新
```

**配置：**
```python
cache_config = CacheConfig(
    max_size=10000,  # ✅ 最多10000项
    eviction_policy="LRU"
)
```

**效果：** 内存可控，避免OOM

---

## 📋 实施检查清单

- [ ] 集成 Singleflight 到 CacheInterceptor
- [ ] 实现空值缓存
- [ ] 添加 TTL 随机抖动
- [ ] 设置内存限制（max_size=10000）
- [ ] 实现 LRU 驱逐策略
- [ ] 编写单元测试

---

## 🎯 预期效果

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| **缓存击穿保护** | ❌ 1000次DB查询 | ✅ 1次DB查询 |
| **缓存穿透防御** | ❌ 无防御 | ✅ 空值缓存 |
| **缓存雪崩风险** | ❌ 同时过期 | ✅ 时间分散 |
| **内存使用** | ❌ 无限增长 | ✅ ≤10000项 |
| **性能提升** | - | **1000x** |
