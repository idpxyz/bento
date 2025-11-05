# Runtime - Framework Composition Root

这是 Bento 框架的**运行时模块**，提供应用启动和依赖注入的默认模板。

## 📋 **目录说明**

```
runtime/
├── bootstrap.py        # FastAPI 应用启动模板
├── composition.py      # 依赖注入配置（占位符）
├── jobs.py            # 后台任务管理（占位符）
└── README.md          # 本文档
```

## 🎯 **用途**

### 1. **框架级模板**

这是框架提供的**通用启动模板**，用于：
- ✅ 快速开始和原型开发
- ✅ 示例应用（`examples/minimal_app/`）
- ✅ 测试（`tests/`）

### 2. **应用级定制**

实际应用应该创建**自己的 runtime**：

```
applications/{your_app}/
└── runtime/
    ├── bootstrap.py       # 应用特定的启动配置
    ├── composition.py     # 应用特定的依赖注入
    └── jobs.py           # 应用特定的后台任务
```

## 📖 **使用方法**

### 快速开始（使用框架模板）

```python
# examples/minimal_app/main.py
from runtime.bootstrap import create_app

app = create_app()

@app.on_event("startup")
async def startup():
    # 初始化数据库等
    pass
```

### 应用定制（推荐）

```python
# applications/ecommerce/runtime/bootstrap.py
from fastapi import FastAPI
from core.error_handler import register_exception_handlers
from applications.ecommerce.modules.order.interfaces import router

def create_app() -> FastAPI:
    app = FastAPI(title="E-commerce API")
    
    # 注册异常处理
    register_exception_handlers(app)
    
    # 注册路由
    app.include_router(router, prefix="/api/orders")
    
    return app
```

## 🔄 **框架 vs 应用 Runtime**

| 特性 | 框架 Runtime (`runtime/`) | 应用 Runtime (`applications/{app}/runtime/`) |
|------|--------------------------|---------------------------------------------|
| **用途** | 通用模板、示例 | 特定应用配置 |
| **配置** | 最小化、通用 | 完整、特定业务 |
| **依赖** | 框架核心 | 框架 + 应用依赖 |
| **修改** | 谨慎（影响所有示例） | 自由（仅影响应用） |

## ✅ **最佳实践**

### 1. **框架模板用于学习**

```python
# 学习框架时使用
from runtime.bootstrap import create_app

app = create_app()  # 快速启动
```

### 2. **应用创建自己的 Runtime**

```python
# 生产应用使用自己的 runtime
from applications.ecommerce.runtime.bootstrap import create_app

app = create_app()  # 完整配置
```

### 3. **不要在框架 Runtime 中添加业务逻辑**

❌ **错误**:
```python
# runtime/bootstrap.py (框架级)
from applications.ecommerce.modules.order.interfaces import router
app.include_router(router)  # 不要在框架级添加应用路由
```

✅ **正确**:
```python
# applications/ecommerce/runtime/bootstrap.py (应用级)
from applications.ecommerce.modules.order.interfaces import router
app.include_router(router)  # 在应用级添加
```

## 📚 **相关文档**

- [Bento Framework Documentation](../docs/README.md)
- [E-commerce Application Runtime](../applications/ecommerce/runtime/)
- [Minimal App Example](../examples/minimal_app/)

## 🔮 **未来增强**

框架级 runtime 未来可能提供：

- [ ] 通用的健康检查端点
- [ ] 通用的监控端点
- [ ] 通用的依赖注入容器
- [ ] 通用的后台任务调度器

---

**总结**: `runtime/` 是框架的组成部分，提供通用模板。应用应创建自己的 runtime 目录进行定制。

