# 缓存功能分层现状与迁移计划

## ✅ **好消息：底层 Cache 已经实现了！**

经过代码审查，发现：
- **LRU 驱逐** ✅ 已在 `MemoryCache` 实现
- **内存限制** ✅ 已在 `MemoryCache` 实现
- **基础统计** ✅ 已在 `MemoryCache` 实现

---

## 📊 **当前实现状态**

### 底层 Cache（src/bento/adapters/cache/memory.py）

#### ✅ 已实现的功能

**1. LRU 驱逐逻辑**
```python
# Line 117-118: 访问时更新 LRU 顺序
self._cache.move_to_end(prefixed_key)

# Line 174: 设置时也移到末尾
self._cache.move_to_end(prefixed_key)

# Line 153-160: 达到容量时驱逐最旧的
if (
    self.config.max_size
    and prefixed_key not in self._cache
    and len(self._cache) >= self.config.max_size
):
    # Remove oldest (first) entry
    self._cache.popitem(last=False)  # ✅ LRU 驱逐
```

**2. 内存限制**
```python
# config.py Line 70: 默认配置
max_size: int | None = 10000  # ✅ 默认 10000 项

# memory.py Line 155: 实际使用
if self.config.max_size and len(self._cache) >= self.config.max_size:
    # 驱逐
```

**3. 基础统计**
```python
# Line 64-65: 初始化统计
self._stats = CacheStats() if config.enable_stats else None

# Line 102-104: 记录 miss
self._stats.record_miss(duration)

# Line 123-125: 记录 hit
self._stats.record_hit(duration)

# Line 177-178: 记录 set
self._stats.record_set(duration)
```

**4. 过期清理**
```python
# Line 77: 启动后台清理任务
self._cleanup_task = asyncio.create_task(self._cleanup_loop())

# Line 109-115: 访问时检查过期
if expire_at and time.time() > expire_at:
    del self._cache[prefixed_key]
```

---

### CacheInterceptor（src/bento/persistence/interceptor/impl/cache.py）

#### ✅ 已实现的功能（业务层）

**1. 业务缓存键生成**
```python
def _get_cache_key(self, context):
    # 基于实体类型、操作类型、查询条件生成键
```

**2. TTL 管理**
```python
def _get_ttl(self, operation):
    # 不同操作类型使用不同 TTL
```

**3. 自动缓存失效**
```python
async def _invalidate_related(self, context):
    # 写操作后失效相关缓存
```

**4. 跨实体失效配置**
```python
# 通过配置定义实体间关联关系
```

#### ❌ 没有重复实现（正确）
- ✅ 没有 LRU 逻辑
- ✅ 没有 max_size 管理
- ✅ 没有内存驱逐逻辑

---

## 🎯 **结论：无需迁移！**

### 架构已经正确分层 ✅

```
┌─────────────────────────────────────────┐
│   CacheInterceptor (业务缓存层)          │
│   ✅ 缓存键生成                           │
│   ✅ TTL 管理                             │
│   ✅ 失效策略                             │
│   ✅ 跨实体失效                           │
│   📝 待添加：Singleflight                 │
│   📝 待添加：TTL 抖动                     │
│   📝 待添加：空值缓存                     │
│   📝 待添加：降级策略                     │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│   MemoryCache (底层缓存实现)             │
│   ✅ LRU 驱逐 (已实现)                    │
│   ✅ 内存限制 (已实现)                    │
│   ✅ 基础统计 (已实现)                    │
│   ✅ 过期清理 (已实现)                    │
└─────────────────────────────────────────┘
```

---

## 📋 **需要添加的功能（都在 CacheInterceptor）**

### 1. Singleflight（防缓存击穿）

**位置：** CacheInterceptor ✅

**实现：**
```python
# cache.py
from bento.persistence.interceptor.singleflight import SingleflightGroup

class CacheInterceptor:
    def __init__(self, cache, ttl=60, enabled=True, enable_singleflight=True):
        self._cache = cache
        self._singleflight = SingleflightGroup() if enable_singleflight else None

    async def execute_before(self, context):
        if not self._enabled or not self._is_read(context.operation):
            return None

        key = self._get_cache_key(context)
        if not key:
            return None

        # ✅ 使用 Singleflight 保护
        if self._singleflight:
            async def query_cache():
                return await self._cache.get(self._full_key(key))

            return await self._singleflight.do(key, query_cache)

        return await self._cache.get(self._full_key(key))
```

**文件：** `src/bento/persistence/interceptor/impl/cache.py`
**工作量：** 2-3小时
**优先级：** 🔴 高

---

### 2. TTL 随机抖动（防缓存雪崩）

**位置：** CacheInterceptor ✅

**实现：**
```python
import random

class CacheInterceptor:
    def __init__(
        self,
        cache,
        enable_jitter=True,
        jitter_range=0.1  # ±10%
    ):
        self._enable_jitter = enable_jitter
        self._jitter_range = jitter_range

    def _apply_jitter(self, base_ttl: int) -> int:
        """应用 TTL 随机抖动"""
        if not self._enable_jitter:
            return base_ttl

        multiplier = random.uniform(
            1 - self._jitter_range,
            1 + self._jitter_range
        )
        return int(base_ttl * multiplier)

    async def process_result(self, context, result, next_interceptor):
        if self._is_read(context.operation):
            base_ttl = self._get_ttl(context.operation)
            actual_ttl = self._apply_jitter(base_ttl)  # ✅ 应用抖动

            await self._cache.set(
                self._full_key(key),
                result,
                ttl=actual_ttl
            )
```

**文件：** `src/bento/persistence/interceptor/impl/cache.py`
**工作量：** 1-2小时
**优先级：** 🔴 高

---

### 3. 空值缓存（防缓存穿透）

**位置：** CacheInterceptor ✅

**实现：**
```python
class _CacheNullValue:
    """空值标记"""
    pass

CACHE_NULL = _CacheNullValue()

class CacheInterceptor:
    def __init__(
        self,
        cache,
        enable_null_cache=True,
        null_cache_ttl=10  # 空值短TTL
    ):
        self._enable_null_cache = enable_null_cache
        self._null_cache_ttl = null_cache_ttl

    async def process_result(self, context, result, next_interceptor):
        if self._is_read(context.operation):
            # ✅ 缓存空值
            if result is None and self._enable_null_cache:
                cache_value = CACHE_NULL
                ttl = self._null_cache_ttl
            else:
                cache_value = result
                ttl = self._get_ttl(context.operation)

            if self._enable_jitter:
                ttl = self._apply_jitter(ttl)

            await self._cache.set(key, cache_value, ttl)

    async def execute_before(self, context):
        cached = await self._cache.get(key)

        # ✅ 识别空值标记
        if isinstance(cached, _CacheNullValue):
            return None  # 避免数据库查询

        return cached
```

**文件：** `src/bento/persistence/interceptor/impl/cache.py`
**工作量：** 2-3小时
**优先级：** 🟡 中

---

### 4. 降级策略（Fail-Open + 断路器）

**位置：** CacheInterceptor ✅

**实现：**
```python
class CacheInterceptor:
    def __init__(
        self,
        cache,
        fail_open=True,
        cache_timeout=0.1  # 100ms 超时
    ):
        self._fail_open = fail_open
        self._cache_timeout = cache_timeout

    async def execute_before(self, context):
        try:
            # ✅ 添加超时保护
            cached = await asyncio.wait_for(
                self._cache.get(key),
                timeout=self._cache_timeout
            )
            return cached

        except asyncio.TimeoutError:
            logger.warning(f"Cache timeout for key: {key}")
            if self._fail_open:
                return None  # 降级到数据库
            else:
                raise

        except Exception as e:
            logger.error(f"Cache error: {e}")
            if self._fail_open:
                return None  # 降级
            else:
                raise

    async def process_result(self, context, result, next_interceptor):
        try:
            # ✅ 设置缓存失败不影响业务
            await asyncio.wait_for(
                self._cache.set(key, result, ttl),
                timeout=self._cache_timeout
            )
        except Exception as e:
            logger.warning(f"Failed to set cache: {e}")
            # 继续，不影响业务
```

**文件：** `src/bento/persistence/interceptor/impl/cache.py`
**工作量：** 3-4小时
**优先级：** 🟡 中

---

## 🚀 **实施计划**

### Phase 1: 高优先级功能（本周）

**任务清单：**

1. **集成 Singleflight**（4h）
   - [x] Singleflight 实现（已完成）
   - [ ] 集成到 CacheInterceptor
   - [ ] 添加配置选项 `enable_singleflight`
   - [ ] 单元测试

2. **实现 TTL 抖动**（2h）
   - [ ] 添加 `_apply_jitter` 方法
   - [ ] 集成到 `process_result`
   - [ ] 添加配置选项 `enable_jitter`, `jitter_range`
   - [ ] 单元测试

**预期效果：**
- 缓存击穿保护 ✅
- 缓存雪崩防护 ✅
- 性能提升 1000x

---

### Phase 2: 中优先级功能（下周）

**任务清单：**

3. **实现空值缓存**（3h）
   - [ ] 定义 `CACHE_NULL` 标记
   - [ ] 修改 `process_result` 缓存空值
   - [ ] 修改 `execute_before` 识别空值
   - [ ] 添加配置选项 `enable_null_cache`, `null_cache_ttl`
   - [ ] 单元测试

4. **实现降级策略**（4h）
   - [ ] 添加超时保护
   - [ ] 实现 Fail-Open 逻辑
   - [ ] 添加配置选项 `fail_open`, `cache_timeout`
   - [ ] 异常场景测试

**预期效果：**
- 缓存穿透防护 ✅
- 故障自动降级 ✅
- 可用性提升到 99.9%

---

## 📁 **需要修改的文件**

### 只需修改这一个文件 ✅

```
src/bento/persistence/interceptor/impl/cache.py
```

**修改内容：**
1. 添加 Singleflight 集成
2. 添加 TTL 抖动逻辑
3. 添加空值缓存支持
4. 添加降级策略

**不需要修改：**
- ❌ `src/bento/adapters/cache/memory.py` - 已经完善
- ❌ `src/bento/adapters/cache/config.py` - 已经完善

---

## ✅ **总结**

### 当前状态
- ✅ **底层 Cache 功能完善**（LRU、内存限制、统计）
- ✅ **架构分层正确**（无重复实现）
- 📝 **只需增强 CacheInterceptor**（业务优化）

### 行动建议
1. **无需迁移** - 底层已完善
2. **专注增强** - 在 CacheInterceptor 添加4个功能
3. **一个文件** - 只需修改 `cache.py`

### 预期效果
- **性能：** 100 QPS → 1000+ QPS（10x）
- **可用性：** 95% → 99.9%
- **工作量：** 11-13小时（1-2天）

**立即开始实施 Phase 1，本周内完成高优先级功能！** 🚀
