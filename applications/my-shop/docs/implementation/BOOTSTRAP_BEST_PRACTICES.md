# Bootstrap 最佳实践对比

本文档对比 `bootstrap_v2.py`（当前实现）与 Bento Runtime 的最佳实践。

## 📊 总体评估

| 方面 | 当前实现 | 最佳实践 | 状态 |
|------|---------|---------|------|
| RuntimeBuilder 使用 | ✅ 使用 | ✅ 使用 | ✅ 符合 |
| 链式配置 API | ✅ 使用 | ✅ 使用 | ✅ 符合 |
| 模块化设计 | ✅ 使用 | ✅ 使用 | ✅ 符合 |
| 异步初始化 | ❌ 缺少 | ✅ 必需 | ⚠️ **需改进** |
| 生命周期管理 | ❌ 缺少 | ✅ 必需 | ⚠️ **需改进** |
| 优雅关闭 | ❌ 缺少 | ✅ 必需 | ⚠️ **需改进** |

**结论**: 当前实现基本符合 Bento Runtime 的使用方式，但缺少关键的**异步初始化**和**生命周期管理**。

---

## 🔍 详细对比

### 1. Runtime 创建方式

#### ✅ 当前实现（基本正确）

```python
def create_runtime() -> BentoRuntime:
    """Create and configure the BentoRuntime."""
    return (
        RuntimeBuilder()
        .with_config(
            service_name="my-shop",
            environment=settings.app_env,
        )
        .with_database(url=settings.database_url)
        .with_modules(
            InfraModule(),
            CatalogModule(),
            IdentityModule(),
            OrderingModule(),
            create_service_discovery_module(),
        )
        .build_runtime()
    )
```

**优点**:
- ✅ 使用 `RuntimeBuilder` 链式 API
- ✅ 配置清晰，易于理解
- ✅ 模块化设计

**问题**:
- ❌ 返回的 Runtime 未调用 `build_async()`
- ❌ 模块的 `on_register` 钩子未执行
- ❌ 数据库连接未初始化
- ❌ 服务发现未注册到容器

#### ✅ 最佳实践

```python
async def create_runtime() -> BentoRuntime:
    """Create and initialize the BentoRuntime."""
    runtime = (
        RuntimeBuilder()
        .with_config(
            service_name="my-shop",
            environment=settings.app_env,
        )
        .with_database(url=settings.database_url)
        .with_modules(
            InfraModule(),
            CatalogModule(),
            IdentityModule(),
            OrderingModule(),
            create_service_discovery_module(),
        )
        .build_runtime()
    )

    # ✅ 关键步骤：异步初始化
    await runtime.build_async()

    return runtime
```

**改进点**:
- ✅ 函数改为 `async`
- ✅ 调用 `await runtime.build_async()`
- ✅ 确保所有模块正确初始化

---

### 2. 全局 Runtime 实例管理

#### ⚠️ 当前实现（有问题）

```python
_runtime: BentoRuntime | None = None

def get_runtime() -> BentoRuntime:
    """Get or create the global runtime instance."""
    global _runtime
    if _runtime is None:
        _runtime = create_runtime()  # ❌ 同步调用，未初始化
    return _runtime
```

**问题**:
- ❌ 同步函数无法调用 `build_async()`
- ❌ Runtime 未正确初始化
- ❌ 模块可能处于未就绪状态

#### ✅ 最佳实践

```python
_runtime: BentoRuntime | None = None

async def get_runtime() -> BentoRuntime:
    """Get or create and initialize the global runtime instance."""
    global _runtime
    if _runtime is None:
        _runtime = RuntimeBuilder().build_runtime()
        await _runtime.build_async()  # ✅ 异步初始化
        logger.info("BentoRuntime initialized successfully")
    return _runtime
```

**改进点**:
- ✅ 改为 `async` 函数
- ✅ 调用 `build_async()` 初始化
- ✅ 添加日志记录

---

### 3. FastAPI 应用创建

#### ⚠️ 当前实现（缺少生命周期管理）

```python
def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    runtime = create_runtime()  # ❌ 未初始化

    app = runtime.create_fastapi_app(
        title=settings.app_name,
        description="完整测试项目",
        version="0.2.0",
    )

    # ... 添加中间件和路由

    return app
```

**问题**:
- ❌ Runtime 未初始化
- ❌ 没有 lifespan 管理
- ❌ 应用关闭时资源未清理
- ❌ 数据库连接可能泄漏

#### ✅ 最佳实践

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan for runtime lifecycle."""
    # Startup
    logger.info("Starting application...")
    runtime = RuntimeBuilder().build_runtime()
    await runtime.build_async()  # ✅ 初始化

    app.state.runtime = runtime  # ✅ 存储到 app.state

    logger.info("Application started")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await runtime.shutdown_async()  # ✅ 优雅关闭
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create FastAPI application with proper lifecycle."""
    runtime = RuntimeBuilder().build_runtime()

    app = runtime.create_fastapi_app(
        title=settings.app_name,
        lifespan=lifespan,  # ✅ 添加生命周期管理
    )

    # ... 添加中间件和路由

    return app
```

**改进点**:
- ✅ 使用 `@asynccontextmanager` 定义 lifespan
- ✅ 在 startup 时调用 `build_async()`
- ✅ 在 shutdown 时调用 `shutdown_async()`
- ✅ 资源正确清理

---

## 🚨 关键问题说明

### 问题 1: 缺少 `build_async()` 调用

**影响**:
```python
# 当前代码
runtime = create_runtime()
discovery = runtime.container.get("service.discovery")  # ❌ 可能为 None！
```

**原因**:
- `ServiceDiscoveryModule.on_register()` 未执行
- 服务未注册到容器
- 容器中找不到 `"service.discovery"`

**解决**:
```python
# 正确做法
runtime = RuntimeBuilder().build_runtime()
await runtime.build_async()  # ✅ 执行所有模块的 on_register
discovery = runtime.container.get("service.discovery")  # ✅ 正常获取
```

### 问题 2: 缺少生命周期管理

**影响**:
- 数据库连接未正确关闭
- 可能导致连接池耗尽
- 资源泄漏

**解决**: 使用 FastAPI lifespan 管理生命周期

### 问题 3: 同步 vs 异步

**错误示例**:
```python
def get_runtime() -> BentoRuntime:
    runtime = create_runtime()
    # ❌ 无法调用 await runtime.build_async()
    return runtime
```

**正确示例**:
```python
async def get_runtime() -> BentoRuntime:
    runtime = RuntimeBuilder().build_runtime()
    await runtime.build_async()  # ✅ 可以调用
    return runtime
```

---

## 📋 迁移指南

### 步骤 1: 更新 `create_runtime()`

```python
# 修改前
def create_runtime() -> BentoRuntime:
    return RuntimeBuilder().build_runtime()

# 修改后
async def create_runtime() -> BentoRuntime:
    runtime = RuntimeBuilder().build_runtime()
    await runtime.build_async()
    return runtime
```

### 步骤 2: 添加 lifespan

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    runtime = RuntimeBuilder().build_runtime()
    await runtime.build_async()
    app.state.runtime = runtime
    yield
    # Shutdown
    await runtime.shutdown_async()
```

### 步骤 3: 更新 `create_app()`

```python
def create_app() -> FastAPI:
    runtime = RuntimeBuilder().build_runtime()
    app = runtime.create_fastapi_app(
        lifespan=lifespan,  # ✅ 添加这一行
    )
    return app
```

### 步骤 4: 更新 `get_runtime()`

```python
async def get_runtime() -> BentoRuntime:
    global _runtime
    if _runtime is None:
        _runtime = RuntimeBuilder().build_runtime()
        await _runtime.build_async()
    return _runtime
```

---

## 🧪 验证方法

### 测试 1: 验证模块初始化

```python
import pytest

@pytest.mark.asyncio
async def test_runtime_initialization():
    """验证 Runtime 正确初始化"""
    runtime = RuntimeBuilder().build_runtime()
    await runtime.build_async()

    # 验证服务发现已注册
    discovery = runtime.container.get("service.discovery")
    assert discovery is not None
    assert hasattr(discovery, "discover")
```

### 测试 2: 验证生命周期

```python
@pytest.mark.asyncio
async def test_runtime_lifecycle():
    """验证 Runtime 生命周期"""
    runtime = RuntimeBuilder().build_runtime()

    # 初始化
    await runtime.build_async()
    assert runtime._built is True

    # 关闭
    await runtime.shutdown_async()
    # 验证资源已清理
```

### 测试 3: 验证 FastAPI 集成

```python
from fastapi.testclient import TestClient

def test_app_with_lifespan():
    """验证 FastAPI lifespan 正常工作"""
    app = create_app()

    with TestClient(app) as client:
        # 应用启动，lifespan 执行
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["runtime"] == "initialized"

    # 应用关闭，lifespan 清理
```

---

## 📚 参考资料

### Bento Runtime 官方文档

- `src/bento/runtime/bootstrap.py` - Runtime 核心实现
- `src/bento/runtime/builder/runtime_builder.py` - Builder 模式
- `tests/unit/runtime/` - 单元测试示例

### FastAPI Lifespan 文档

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Async Context Managers](https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager)

---

## ✅ 检查清单

在部署前，确保以下项目都已完成：

- [ ] `create_runtime()` 是 `async` 函数
- [ ] 调用了 `await runtime.build_async()`
- [ ] 定义了 `lifespan` context manager
- [ ] `create_app()` 传入了 `lifespan` 参数
- [ ] 添加了 `await runtime.shutdown_async()`
- [ ] 更新了 `get_runtime()` 为 `async`
- [ ] 编写了集成测试验证初始化
- [ ] 测试了应用的启动和关闭

---

## 🎯 总结

### 当前实现状态

`bootstrap_v2.py` 的实现**基本正确**，使用了 Bento Runtime 的推荐 API，但缺少以下关键步骤：

1. ❌ 异步初始化（`build_async()`）
2. ❌ 生命周期管理（lifespan）
3. ❌ 优雅关闭（`shutdown_async()`）

### 建议行动

**选项 1: 快速修复（推荐）**
- 使用 `bootstrap_best_practice.py` 替换 `bootstrap_v2.py`
- 运行测试验证
- 部署到生产环境

**选项 2: 渐进式改进**
1. 先添加 `build_async()` 调用
2. 再添加 lifespan 管理
3. 最后添加 shutdown 逻辑

**选项 3: 保持现状**
- 如果当前运行正常，可以暂时保持
- 但需要注意可能的资源泄漏问题
- 建议在下次重构时改进

### 优先级

🔴 **高优先级**: 添加 `build_async()` 调用（确保模块正确初始化）
🟡 **中优先级**: 添加 lifespan 管理（防止资源泄漏）
🟢 **低优先级**: 优化日志和监控

---

**参考实现**: `runtime/bootstrap_best_practice.py`
