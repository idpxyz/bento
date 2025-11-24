# 缓存可靠性加固方案 - Part 2: 容错与监控

## 🔄 容错机制 - 故障发生时快速恢复

### 1. 异常处理和降级

**Fail-Open 模式：缓存故障不影响业务**

```python
class CacheInterceptor:
    def __init__(self, cache, fail_open: bool = True):
        self._cache = cache
        self._fail_open = fail_open  # ✅ 缓存故障时继续服务

    async def execute_before(self, context):
        try:
            # ✅ 设置超时
            cached = await asyncio.wait_for(
                self._cache.get(key),
                timeout=0.1
            )
            return cached

        except asyncio.TimeoutError:
            logger.warning(f"Cache timeout: {key}")
            return None if self._fail_open else raise

        except Exception as e:
            logger.error(f"Cache error: {e}")
            return None if self._fail_open else raise
```

**效果：** 缓存故障自动降级到数据库

---

### 2. 断路器模式

**防止级联故障**

```python
class CircuitBreaker:
    """断路器 - 自动熔断故障服务"""

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self._failure_threshold = failure_threshold
        self._timeout = timeout
        self._failure_count = 0
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        if self._state == "OPEN":
            if time.time() - self._last_failure < self._timeout:
                raise CircuitBreakerOpenError()
            self._state = "HALF_OPEN"

        try:
            result = await func(*args, **kwargs)
            if self._state == "HALF_OPEN":
                self._state = "CLOSED"
            self._failure_count = 0
            return result

        except Exception:
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._state = "OPEN"
                logger.warning("Circuit breaker OPEN")
            raise

# 使用
class CacheInterceptor:
    def __init__(self, cache):
        self._circuit_breaker = CircuitBreaker()

    async def execute_before(self, context):
        try:
            return await self._circuit_breaker.call(
                self._cache.get, key
            )
        except CircuitBreakerOpenError:
            return None  # 降级
```

**效果：** 防止故障扩散，保护系统

---

### 3. 数据一致性保证

**版本化缓存**

```python
class VersionedCache:
    async def set_with_version(
        self, key: str, value: Any, version: int, ttl: int
    ) -> bool:
        current = await self.get_with_version(key)

        if current is None:
            await self._cache.set(key, {"v": version, "data": value}, ttl)
            return True

        current_v, _ = current

        # ✅ 版本检查 - 只接受更新的版本
        if version > current_v:
            await self._cache.set(key, {"v": version, "data": value}, ttl)
            return True

        return False  # 拒绝旧版本
```

**效果：** 防止并发覆盖，保证数据正确性

---

## 📊 监控告警 - 及时发现和定位问题

### 1. 指标收集

```python
@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_get_time: float = 0.0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

class MetricsCollector:
    def __init__(self):
        self._metrics = CacheMetrics()

    async def record_hit(self, duration: float):
        self._metrics.hits += 1
        self._metrics.total_get_time += duration

    async def record_miss(self, duration: float):
        self._metrics.misses += 1
        self._metrics.total_get_time += duration

# 集成
class CacheInterceptor:
    def __init__(self, cache, metrics: MetricsCollector):
        self._metrics = metrics

    async def execute_before(self, context):
        start = time.time()
        cached = await self._cache.get(key)
        duration = time.time() - start

        if cached:
            await self._metrics.record_hit(duration)
        else:
            await self._metrics.record_miss(duration)
```

---

### 2. 健康检查端点

```python
@app.get("/health/cache")
async def cache_health():
    metrics = metrics_collector.get_metrics()

    status = "healthy"
    if metrics.hit_rate < 0.5:
        status = "degraded"
    if metrics.errors > 100:
        status = "unhealthy"

    return {
        "status": status,
        "hit_rate": f"{metrics.hit_rate:.2%}",
        "total_requests": metrics.hits + metrics.misses,
        "errors": metrics.errors,
        "cache_size": cache.size(),
    }
```

---

### 3. 告警规则

```yaml
alerts:
  - name: CacheHitRateLow
    condition: hit_rate < 0.5
    duration: 5m
    severity: warning
    message: "缓存命中率过低: {{ $value }}"

  - name: CacheErrorsHigh
    condition: errors > 100
    duration: 1m
    severity: critical
    message: "缓存错误数过高: {{ $value }}"

  - name: CacheMemoryHigh
    condition: memory_usage > 0.9
    duration: 5m
    severity: warning
    message: "缓存内存使用率过高"
```

---

## 🎚️ 降级策略

### 分级降级

```python
class CacheDegradationStrategy:
    def __init__(self):
        self._level = 0  # 0=正常, 1=轻度, 2=中度, 3=重度

    def should_cache(self, operation: OperationType) -> bool:
        if self._level == 0:
            return True
        elif self._level == 1:
            # 轻度：只缓存聚合查询
            return operation in (OperationType.AGGREGATE, OperationType.GROUP_BY)
        elif self._level == 2:
            # 中度：只缓存最重要的
            return operation == OperationType.AGGREGATE
        else:
            # 重度：禁用缓存
            return False

# 自动调整
async def auto_adjust():
    while True:
        metrics = get_metrics()

        if metrics.errors > 100:
            strategy.escalate()
        elif metrics.hit_rate > 0.8:
            strategy.recover()

        await asyncio.sleep(60)
```

---

## 📋 实施检查清单

- [ ] 实现 Fail-Open 模式
- [ ] 添加断路器
- [ ] 实现版本化缓存
- [ ] 集成指标收集
- [ ] 创建健康检查端点
- [ ] 配置告警规则
- [ ] 实现分级降级
- [ ] 添加自动化测试

---

## 🎯 预期效果

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| **故障影响** | ❌ 服务中断 | ✅ 自动降级 |
| **恢复时间** | ⏱️ 需人工介入 | ✅ 自动恢复 |
| **可观测性** | ❌ 无监控 | ✅ 实时指标 |
| **问题定位** | ⏱️ 分钟级 | ✅ 秒级 |
| **可用性** | 99% | **99.9%** |
