# 缓存配置指南

## 📋 概述

本指南介绍如何在 Bento Framework 中配置缓存拦截器，包括所有 Phase 1 优化参数。

---

## 🎯 **快速开始**

### 默认配置（推荐）

所有优化功能默认启用，开箱即用：

```python
from bento.adapters.cache import CacheFactory, CacheConfig, CacheBackend
from bento.persistence.interceptor.factory import InterceptorConfig, InterceptorFactory

# 1. 创建缓存实例
cache = await CacheFactory.create(
    CacheConfig(
        backend=CacheBackend.MEMORY,
        max_size=10000,
        ttl=300,
    )
)

# 2. 创建拦截器配置（所有优化默认启用）
config = InterceptorConfig(
    enable_cache=True,
    cache=cache,
    cache_ttl_seconds=300,
    # ✅ 所有优化参数都有合理的默认值
)

# 3. 创建拦截器链
factory = InterceptorFactory(config)
chain = factory.build_chain()

# 4. 在 Repository 中使用
repository._interceptor_chain = chain
```

---

## ⚙️ **配置参数详解**

### 基础配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_cache` | bool | False | 启用缓存拦截器 |
| `cache` | Cache | None | 缓存实例（必需） |
| `cache_ttl_seconds` | int | 300 | 默认TTL（秒） |
| `cache_prefix` | str | "" | 缓存键前缀 |

### Phase 1 优化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_singleflight` | bool | **True** | 启用Singleflight（防缓存击穿） |
| `singleflight_timeout` | float | **5.0** | Singleflight超时（秒） |
| `enable_jitter` | bool | **True** | 启用TTL抖动（防缓存雪崩） |
| `jitter_range` | float | **0.1** | TTL抖动范围（±10%） |
| `enable_null_cache` | bool | **True** | 启用空值缓存（防缓存穿透） |
| `null_cache_ttl` | int | **10** | 空值缓存TTL（秒） |
| `fail_open` | bool | **True** | 启用Fail-Open（故障降级） |
| `cache_timeout` | float | **0.1** | 缓存操作超时（秒） |

---

## 📝 **使用示例**

### 示例1：使用默认配置（推荐）

```python
from bento.adapters.cache import CacheFactory, CacheConfig, CacheBackend
from bento.persistence.interceptor.factory import InterceptorConfig, InterceptorFactory

async def setup_cache():
    # 创建缓存
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, max_size=10000)
    )

    # 使用默认配置（所有优化启用）
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
    )

    factory = InterceptorFactory(config)
    return factory.build_chain()
```

**效果：**
- ✅ Singleflight 防缓存击穿（5秒超时）
- ✅ TTL抖动防缓存雪崩（±10%）
- ✅ 空值缓存防缓存穿透（10秒）
- ✅ Fail-Open 故障降级（100ms超时）

---

### 示例2：自定义优化参数

```python
async def setup_cache_custom():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY)
    )

    # 自定义配置
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
        cache_ttl_seconds=600,  # 10分钟TTL
        cache_prefix="myapp:",

        # 自定义优化参数
        enable_singleflight=True,
        singleflight_timeout=10.0,  # 10秒超时（慢查询场景）

        enable_jitter=True,
        jitter_range=0.2,  # ±20%抖动（高并发场景）

        enable_null_cache=True,
        null_cache_ttl=5,  # 5秒空值缓存

        fail_open=True,
        cache_timeout=0.2,  # 200ms超时
    )

    factory = InterceptorFactory(config)
    return factory.build_chain()
```

**适用场景：**
- 数据库查询较慢：增加 `singleflight_timeout`
- 高并发场景：增加 `jitter_range`
- 网络不稳定：增加 `cache_timeout`

---

### 示例3：禁用某些优化

```python
async def setup_cache_minimal():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY)
    )

    # 只启用基本缓存，禁用优化
    config = InterceptorConfig(
        enable_cache=True,
        cache=cache,

        # 禁用优化
        enable_singleflight=False,  # 禁用Singleflight
        enable_jitter=False,         # 禁用TTL抖动
        enable_null_cache=False,     # 禁用空值缓存
    )

    factory = InterceptorFactory(config)
    return factory.build_chain()
```

**适用场景：**
- 开发调试
- 问题排查
- 性能对比测试

---

### 示例4：生产环境配置

```python
import os
from bento.adapters.cache import CacheFactory, CacheConfig, CacheBackend

async def setup_production_cache():
    # 从环境变量读取配置
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"

    # 创建 Redis 缓存
    cache = await CacheFactory.create(
        CacheConfig(
            backend=CacheBackend.REDIS,
            redis_url=redis_url,
            ttl=300,
        )
    )

    # 生产环境配置
    config = InterceptorConfig(
        enable_cache=cache_enabled,
        cache=cache,
        cache_ttl_seconds=int(os.getenv("CACHE_TTL", "300")),
        cache_prefix=os.getenv("CACHE_PREFIX", "prod:"),

        # 优化参数（可通过环境变量覆盖）
        enable_singleflight=True,
        singleflight_timeout=float(os.getenv("SINGLEFLIGHT_TIMEOUT", "5.0")),

        enable_jitter=True,
        jitter_range=float(os.getenv("JITTER_RANGE", "0.1")),

        enable_null_cache=True,
        null_cache_ttl=int(os.getenv("NULL_CACHE_TTL", "10")),

        fail_open=True,
        cache_timeout=float(os.getenv("CACHE_TIMEOUT", "0.1")),
    )

    factory = InterceptorFactory(config)
    return factory.build_chain()
```

**环境变量：**
```bash
# .env
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL=600
CACHE_PREFIX=myapp:
SINGLEFLIGHT_TIMEOUT=10.0
JITTER_RANGE=0.2
NULL_CACHE_TTL=5
CACHE_TIMEOUT=0.2
```

---

### 示例5：在 FastAPI 中使用

```python
from fastapi import FastAPI
from bento.adapters.cache import CacheFactory, CacheConfig, CacheBackend
from bento.persistence.interceptor.factory import InterceptorConfig, InterceptorFactory

app = FastAPI()

# 全局缓存配置
cache_config: InterceptorConfig | None = None
interceptor_chain = None

@app.on_event("startup")
async def startup():
    global cache_config, interceptor_chain

    # 创建缓存
    cache = await CacheFactory.create(
        CacheConfig(
            backend=CacheBackend.REDIS,
            redis_url="redis://localhost:6379/0",
            max_size=10000,
        )
    )

    # 创建配置
    cache_config = InterceptorConfig(
        enable_cache=True,
        cache=cache,
        cache_ttl_seconds=300,
        # 所有优化默认启用
    )

    # 创建拦截器链
    factory = InterceptorFactory(cache_config)
    interceptor_chain = factory.build_chain()

    print("✅ 缓存配置完成")
    print(f"  - Singleflight: {cache_config.enable_singleflight}")
    print(f"  - TTL抖动: {cache_config.enable_jitter}")
    print(f"  - 空值缓存: {cache_config.enable_null_cache}")
    print(f"  - Fail-Open: {cache_config.fail_open}")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "cache_enabled": cache_config.enable_cache if cache_config else False,
    }
```

---

## 🔧 **配置调优建议**

### 根据场景调整参数

#### 高并发场景

```python
config = InterceptorConfig(
    enable_cache=True,
    cache=cache,

    # 强化Singleflight
    enable_singleflight=True,
    singleflight_timeout=10.0,  # 增加超时

    # 强化TTL抖动
    enable_jitter=True,
    jitter_range=0.2,  # ±20%抖动
)
```

#### 慢查询场景

```python
config = InterceptorConfig(
    enable_cache=True,
    cache=cache,

    # 增加超时时间
    singleflight_timeout=15.0,  # 15秒
    cache_timeout=0.5,  # 500ms

    # 增加TTL
    cache_ttl_seconds=1200,  # 20分钟
)
```

#### 网络不稳定场景

```python
config = InterceptorConfig(
    enable_cache=True,
    cache=cache,

    # 启用Fail-Open
    fail_open=True,
    cache_timeout=0.3,  # 300ms超时

    # 本地缓存降级
    # 考虑使用 MEMORY backend 作为 L1 cache
)
```

---

## 📊 **监控配置**

### 获取缓存统计

```python
from bento.persistence.interceptor.impl.cache import CacheInterceptor

# 从拦截器链获取 CacheInterceptor
cache_interceptor = None
for interceptor in interceptor_chain._interceptors:
    if isinstance(interceptor, CacheInterceptor):
        cache_interceptor = interceptor
        break

if cache_interceptor:
    # 获取统计
    stats = cache_interceptor.get_stats()

    print(f"""
    缓存统计:
    - 命中率: {stats['cache_hits']/(stats['cache_hits']+stats['cache_misses']):.2%}
    - Singleflight节省: {stats['singleflight_saved']} 次
    - 超时次数: {stats['singleflight_timeout']} 次
    - 降级次数: {stats['fail_open_count']} 次
    - 空值命中: {stats['null_cache_hits']} 次
    """)
```

### 集成到监控系统

```python
import asyncio
from prometheus_client import Gauge, Counter

# 定义 Prometheus 指标
cache_hit_rate = Gauge('cache_hit_rate', 'Cache hit rate')
singleflight_saved = Counter('singleflight_saved_total', 'Queries saved by singleflight')
fail_open_count = Counter('fail_open_total', 'Fail-open degradations')

async def collect_cache_metrics():
    """定期收集缓存指标"""
    while True:
        if cache_interceptor:
            stats = cache_interceptor.get_stats()

            # 更新 Prometheus 指标
            total = stats['cache_hits'] + stats['cache_misses']
            if total > 0:
                cache_hit_rate.set(stats['cache_hits'] / total)

            singleflight_saved.inc(stats['singleflight_saved'])
            fail_open_count.inc(stats['fail_open_count'])

            # 重置统计
            cache_interceptor.reset_stats()

        await asyncio.sleep(60)  # 每分钟收集一次
```

---

## ✅ **配置检查清单**

### 部署前检查

- [ ] ✅ `enable_cache=True` 已设置
- [ ] ✅ `cache` 实例已创建
- [ ] ✅ `cache_ttl_seconds` 根据业务设置
- [ ] ✅ 优化参数使用默认值或已调优
- [ ] ✅ 监控指标已集成
- [ ] ✅ 日志级别已配置

### 生产环境检查

- [ ] ✅ 使用 Redis 而不是 Memory
- [ ] ✅ `cache_prefix` 已设置（避免冲突）
- [ ] ✅ `fail_open=True`（保证可用性）
- [ ] ✅ 超时参数已根据网络情况调整
- [ ] ✅ 监控告警已配置

---

## 🎓 **总结**

### 配置原则

1. **默认优先**：大多数场景使用默认配置即可
2. **按需调整**：根据实际场景调整参数
3. **持续监控**：通过监控数据优化配置
4. **测试验证**：配置变更前先测试

### 推荐配置

**开发环境：**
```python
config = InterceptorConfig(
    enable_cache=True,
    cache=memory_cache,  # 使用内存缓存
    # 其他使用默认值
)
```

**生产环境：**
```python
config = InterceptorConfig(
    enable_cache=True,
    cache=redis_cache,  # 使用 Redis
    cache_prefix="prod:",
    # 优化参数使用默认值（已经过优化）
)
```

**高并发场景：**
```python
config = InterceptorConfig(
    enable_cache=True,
    cache=redis_cache,
    singleflight_timeout=10.0,  # 增加超时
    jitter_range=0.2,  # 增加抖动
)
```

---

## 📚 **相关文档**

- [缓存优化完成报告](./CACHE_OPTIMIZATION_COMPLETED.md)
- [全量发布指南](./CACHE_FULL_DEPLOYMENT_GUIDE.md)
- [Phase 1 完成报告](./CACHE_PHASE1_COMPLETED.md)
- [架构分析](./CACHE_ARCHITECTURE_ANALYSIS.md)
