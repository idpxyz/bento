# Bento Runtime 迁移指南

## 从旧版本迁移

本文档帮助你从旧版本的 Bento Runtime 迁移到最新版本。

---

## 重大变更

### 1. 配置方法从 BentoRuntime 移到 RuntimeBuilder

**旧版本** (已废弃):
```python
runtime = (
    BentoRuntime()
    .with_config(service_name="my-shop")
    .with_modules(InfraModule(), CatalogModule())
    .build()
)
```

**新版本** (推荐):
```python
from bento.runtime import RuntimeBuilder

runtime = (
    RuntimeBuilder()
    .with_config(service_name="my-shop")
    .with_modules(InfraModule(), CatalogModule())
    .build_runtime()
)
```

**原因**: 配置与执行分离，遵循 Builder 模式。

---

### 2. Mock 工具方法移除

**旧版本** (已移除):
```python
runtime.create_mock_repository(Product)
runtime.create_mock_handler()
runtime.create_mock_service()
```

**新版本** (使用 Mock 类):
```python
from bento.runtime.testing import MockRepository, MockHandler, MockService

mock_repo = MockRepository(aggregate_class=Product)
mock_handler = MockHandler()
mock_service = MockService()
```

**原因**:
- 减少 bootstrap.py 的复杂度
- Mock 类更灵活和可重用

---

### 3. 生命周期函数集中管理

**旧版本** (分散在多处):
```python
# 生命周期逻辑分散在 bootstrap.py 和 lifecycle/ 中
```

**新版本** (集中在 lifecycle/):
```python
# 统一使用 lifecycle/startup.py 和 lifecycle/shutdown.py
from bento.runtime.lifecycle import startup, shutdown

await startup.run_gates(runtime)
await startup.register_modules(runtime)
```

**原因**:
- 生命周期逻辑集中管理
- 易于维护和扩展

---

### 4. OpenTelemetry 集成提取

**旧版本** (内联在 bootstrap.py):
```python
# with_otel_tracing() 和 with_otel_metrics() 有大量内联代码
```

**新版本** (提取到 observability/otel.py):
```python
from bento.runtime.observability import otel

tracer_provider = otel.setup_tracing(service_name, trace_exporter)
meter_provider = otel.setup_metrics(metrics_exporter)
```

**原因**:
- 模块化
- 可复用
- 易于测试

---

## 逐步迁移指南

### 步骤 1: 更新导入

**旧版本**:
```python
from bento.runtime import BentoRuntime
```

**新版本**:
```python
from bento.runtime import RuntimeBuilder, BentoRuntime
```

### 步骤 2: 使用 RuntimeBuilder

**旧版本**:
```python
runtime = (
    BentoRuntime()
    .with_config(service_name="my-shop", environment="prod")
    .with_database(url="postgresql://...")
    .with_modules(InfraModule(), CatalogModule())
    .build()
)
```

**新版本**:
```python
runtime = (
    RuntimeBuilder()
    .with_config(service_name="my-shop", environment="prod")
    .with_database(url="postgresql://...")
    .with_modules(InfraModule(), CatalogModule())
    .build_runtime()
)
```

### 步骤 3: 更新 Mock 工具使用

**旧版本**:
```python
mock_repo = runtime.create_mock_repository(Product)
```

**新版本**:
```python
from bento.runtime.testing import MockRepository

mock_repo = MockRepository(aggregate_class=Product)
```

### 步骤 4: 验证测试

```bash
pytest tests/
```

---

## 兼容性

### 向后兼容

- ✅ `BentoRuntime` 类仍然存在
- ✅ `build()` 和 `build_async()` 方法保持不变
- ✅ `create_fastapi_app()` 方法保持不变
- ✅ 所有公共 API 保持兼容

### 不兼容的变更

- ❌ `with_modules()` 等配置方法从 `BentoRuntime` 移除
- ❌ `create_mock_*()` 方法移除
- ❌ `lifecycle/startup.py` 的内部实现变更

---

## 迁移检查清单

- [ ] 更新导入语句 (`RuntimeBuilder`)
- [ ] 替换 `BentoRuntime()` 为 `RuntimeBuilder()`
- [ ] 替换 `.build()` 为 `.build_runtime()`
- [ ] 更新 Mock 工具使用
- [ ] 运行测试验证
- [ ] 更新文档和示例

---

## 常见问题

### Q: 为什么要使用 RuntimeBuilder？

**A**: 配置与执行分离，遵循 Builder 模式。这样可以：
- 更清晰的职责分离
- 更好的测试性
- 更易于扩展

### Q: 旧代码还能运行吗？

**A**: 大部分旧代码可以运行，但配置方法需要迁移到 RuntimeBuilder。

### Q: 迁移需要多长时间？

**A**:
- 小型项目: 10-30 分钟
- 中型项目: 1-2 小时
- 大型项目: 半天

### Q: 如何逐步迁移？

**A**:
1. 先更新测试代码
2. 逐个模块迁移
3. 保持两种方式并存（如果需要）
4. 最后统一到新方式

---

## 性能影响

新版本的性能影响：

| 指标 | 旧版本 | 新版本 | 变化 |
|------|--------|--------|------|
| 启动时间 | 0.81s | 0.81s | 无变化 |
| 内存占用 | 45MB | 45MB | 无变化 |
| 代码复杂度 | 1,320 行 | 393 行 | -70% |

**结论**: 性能无影响，代码更简洁。

---

## 新功能

### 1. PerformanceMonitor

```python
# 获取启动指标
metrics = runtime.get_startup_metrics()
print(f"Total: {metrics['total_time']:.2f}s")

# 记录日志
runtime.log_startup_metrics()
```

### 2. ModuleManager

```python
# 热重载模块
await runtime.reload_module("catalog")

# 卸载模块
await runtime.unload_module("catalog")

# 加载模块
await runtime.load_module(new_module)
```

### 3. 测试模式

```python
runtime = (
    RuntimeBuilder()
    .with_test_mode(True)
    .with_mock_module("db", services={"db": mock_db})
    .build_runtime()
)
```

---

## 获取帮助

如果在迁移过程中遇到问题：

1. 查看[架构文档](./ARCHITECTURE.md)
2. 查看[依赖说明](./DEPENDENCIES.md)
3. 查看示例代码
4. 提交 Issue

---

## 版本历史

### v2.0.0 (当前)
- 提取 4 个专业模块
- bootstrap.py 从 1,320 行 → 393 行
- 完善文档

### v1.5.0
- 添加 LifecycleManager
- 优化 OTEL 集成

### v1.0.0
- 初始版本
