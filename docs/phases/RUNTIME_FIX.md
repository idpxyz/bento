# Runtime 目录修复完成

**修复时间**: 2025-11-04  
**状态**: ✅ 完成

---

## 🎯 **问题分析**

### 原始问题

之前的 `runtime/bootstrap.py` 引用了已删除的 `modules/order/`：

```python
# ❌ 错误的引用
from modules.order.interfaces.http.router import router as order_router
#      ^^^^^^^^^^^^^^ 这个目录已被删除
```

导致：
- `examples/minimal_app/main.py` 无法正常工作
- `tests/e2e/test_order_flow.py` 测试失败
- 误导用户认为这是"旧代码"

### 根本原因

**误解了 `runtime/` 的角色**！

`runtime/` 不是"旧代码"，而是框架设计的核心部分：

> **README.md 说明**:
> - `src/` core packages (domain, application, messaging, persistence, etc.)
> - **`runtime/` composition root (DI, wiring)** 👈 框架组成部分！
> - `examples/minimal_app` runnable FastAPI demo

---

## ✅ **修复方案**

### 1. **runtime/bootstrap.py** - 改为通用模板

**之前**（引用具体业务）:
```python
from modules.order.interfaces.http.router import router as order_router
from persistence.sqlalchemy.base import _engine, Base

def create_app() -> FastAPI:
    app = FastAPI(title="Bento Framework Minimal")
    app.include_router(order_router, prefix="/api")  # ❌ 业务路由
    # ... 数据库初始化等
```

**现在**（纯通用模板）:
```python
def create_app() -> FastAPI:
    """Create a minimal Bento Framework application.
    
    This is a framework-level template providing basic FastAPI setup.
    Applications can extend this or create their own bootstrap.
    """
    app = FastAPI(
        title="Bento Framework",
        description="A minimal DDD framework with hexagonal architecture",
        version="0.1.0",
    )
    
    @app.get("/health", tags=["system"])
    async def health_check():
        return {
            "status": "healthy",
            "framework": "bento",
            "version": "0.1.0",
        }
    
    @app.get("/", tags=["system"])
    async def root():
        return {
            "framework": "Bento Framework",
            "description": "Domain-Driven Design with Hexagonal Architecture",
            "docs": "/docs",
            "health": "/health",
        }
    
    return app
```

### 2. **runtime/composition.py** - 添加文档和类型提示

**之前**:
```python
def wire(): pass
```

**现在**:
```python
def wire() -> None:
    """Wire up dependencies (placeholder).
    
    This is a framework-level placeholder. Applications should implement
    their own dependency injection in:
    applications/{app_name}/runtime/composition.py
    """
    pass
```

### 3. **runtime/jobs.py** - 添加文档和示例

**之前**:
```python
async def run(): pass
```

**现在**:
```python
async def run() -> None:
    """Run background jobs (placeholder).
    
    This is a framework-level placeholder. Applications should implement
    their own background jobs in:
    applications/{app_name}/runtime/jobs.py
    
    Example:
        ```python
        async def run():
            # Start outbox publisher
            publisher = OutboxPublisher(...)
            await publisher.start()
            
            # Start other background tasks
            tasks = [
                asyncio.create_task(publish_events()),
                asyncio.create_task(cleanup_expired_data()),
            ]
            await asyncio.gather(*tasks)
        ```
    """
    pass


async def run_background_jobs() -> None:
    """Run all background jobs."""
    await run()
```

### 4. **runtime/README.md** - 新增使用文档

创建了完整的使用说明，包括：
- 目录说明
- 用途解释
- 使用方法
- 框架 vs 应用 runtime 对比
- 最佳实践

---

## 📊 **修复效果**

### ✅ **现在的 runtime/** 

```
runtime/                        # ✅ 框架级 Composition Root
├── bootstrap.py               # ✅ 通用 FastAPI 启动模板
├── composition.py             # ✅ 依赖注入占位符
├── jobs.py                    # ✅ 后台任务占位符
└── README.md                  # ✅ 使用文档（新增）
```

**特点**:
- ✅ 不依赖任何具体业务模块
- ✅ 可被 `examples/minimal_app/` 使用
- ✅ 可被 `tests/` 使用
- ✅ 提供清晰的文档和示例
- ✅ 完整的类型提示和文档字符串

---

## 🎯 **架构清晰度**

### 框架级 vs 应用级 Runtime

| 特性 | 框架 Runtime | 应用 Runtime |
|------|-------------|-------------|
| **位置** | `runtime/` | `applications/{app}/runtime/` |
| **用途** | 通用模板、示例 | 特定应用配置 |
| **配置** | 最小化、通用 | 完整、业务特定 |
| **依赖** | 框架核心 | 框架 + 应用依赖 |
| **修改频率** | 低（影响所有示例） | 高（仅影响应用） |
| **示例** | `examples/minimal_app/` | `applications/ecommerce/` |

### 使用场景

**框架 Runtime** (`runtime/`):
```python
# 快速开始 / 学习 / 原型
from runtime.bootstrap import create_app

app = create_app()  # 最小配置
```

**应用 Runtime** (`applications/ecommerce/runtime/`):
```python
# 生产应用 / 完整功能
from applications.ecommerce.runtime.bootstrap import create_app

app = create_app()  # 完整配置，包含所有业务路由、中间件等
```

---

## 🔄 **兼容性验证**

### 验证点

- [x] `examples/minimal_app/main.py` 仍然可以导入 `runtime.bootstrap`
- [x] `tests/e2e/test_order_flow.py` 需要更新（因为依赖已删除的 modules/order/）
- [x] 0 linter 错误
- [x] 完整的类型提示
- [x] 完整的文档字符串

### 需要更新的文件

`tests/e2e/test_order_flow.py` 需要更新，因为它依赖已删除的 `modules/order/`：

**选项 1**: 删除此测试（旧业务逻辑）  
**选项 2**: 改为测试新的电商应用  
**选项 3**: 改为测试框架基础功能

---

## 📚 **更新的文档**

1. ✅ `runtime/README.md` - 新增完整使用文档
2. ✅ `runtime/bootstrap.py` - 添加详细文档字符串
3. ✅ `runtime/composition.py` - 添加文档和示例
4. ✅ `runtime/jobs.py` - 添加文档和示例
5. ✅ `applications/ecommerce/docs/DIRECTORY_STRUCTURE.md` - 更新说明

---

## 🎉 **总结**

### 之前的误解 ❌

- ❌ 认为 `runtime/` 是"旧代码"
- ❌ 建议删除 `runtime/`
- ❌ 没有理解框架设计意图

### 现在的理解 ✅

- ✅ `runtime/` 是框架的核心组成部分
- ✅ 提供通用的启动模板
- ✅ 用于示例、测试和快速开始
- ✅ 应用应创建自己的 runtime 进行定制

### 关键收获 💡

1. **Composition Root 模式**: 框架提供基础模板，应用进行定制
2. **分层架构**: 框架层 → 应用层，清晰分离
3. **文档重要性**: README.md 是理解设计意图的关键

---

**修复完成！`runtime/` 现在是一个干净、通用、有良好文档的框架模板。** ✅

