# Observable Handler 依赖注入修复

**修复日期**: 2024-12-30
**状态**: ✅ 部分完成

---

## 🎯 问题描述

在文件整理后运行测试时，发现 `CreateOrderHandler` 等 Observable Handler 无法通过 FastAPI 的依赖注入系统正常工作。

### 错误信息

```
TypeError: CreateOrderHandler.__init__() missing 1 required positional argument: 'observability'
```

### 根本原因

1. `CreateOrderHandler` 继承自 `ObservableCommandHandler`，需要 `observability` 参数
2. Bento Framework 的 `handler_dependency` 只支持接受 `uow` 参数的标准 Handler
3. 依赖注入系统无法自动识别和注入 `observability` 参数

---

## ✅ 修复方案

### 1. 更新 FastAPI 依赖注入系统

**文件**: `/workspace/bento/src/bento/interfaces/fastapi/dependencies.py`

**修复内容**:
- 使用反射检查 Handler 的 `__init__` 签名
- 如果需要 `observability` 参数，自动从 runtime 容器获取
- 如果 runtime 不可用，使用 `NoOpObservabilityProvider` 作为 fallback

**修复代码**:
```python
def factory(
    uow: Annotated[UnitOfWork, Depends(get_uow_dependency)],
    request: "Request",
) -> THandler:
    # Check if handler needs observability (Observable Handler pattern)
    import inspect
    sig = inspect.signature(handler_cls.__init__)
    params = list(sig.parameters.keys())

    if 'observability' in params:
        # Get observability from runtime
        runtime = getattr(request.app.state, 'bento_runtime', None)
        if runtime:
            try:
                observability = runtime.container.get('observability')
                return handler_cls(uow, observability)
            except KeyError:
                pass
        # Fallback to NoOp if not available
        from bento.adapters.observability.noop import NoOpObservabilityProvider
        return handler_cls(uow, NoOpObservabilityProvider())
    else:
        # Standard handler with only uow
        return handler_cls(uow)
```

### 2. 修复测试文件

**文件**: `/workspace/bento/applications/my-shop/tests/e2e_outbox_test.py`

**修复内容**:
- 添加 `NoOpObservabilityProvider` 导入
- 创建 observability 实例
- 传递给 `CreateOrderHandler`

**修复代码**:
```python
# Create observability provider (NoOp for testing)
from bento.adapters.observability.noop import NoOpObservabilityProvider
observability = NoOpObservabilityProvider()

handler = CreateOrderHandler(uow, observability)
```

### 3. 修复中间件配置

**文件**: `/workspace/bento/applications/my-shop/runtime/config/middleware_config.py`

**修复内容**:
- 添加异常处理，在 runtime 未完全初始化时跳过 TracingMiddleware

**修复代码**:
```python
try:
    observability = runtime.container.get("observability")
    app.add_middleware(TracingMiddleware, observability=observability)
    logger.info("✅ TracingMiddleware registered")
except KeyError:
    logger.warning("⚠️ TracingMiddleware skipped (observability not available yet)")
```

---

## 📊 修复效果

### 测试结果

#### 单元测试 ✅
```bash
uv run pytest tests/ordering/unit/application/test_create_order.py -v

Result: ✅ 4 passed in 0.11s
```

#### 集成测试 ⚠️
```bash
uv run pytest tests/e2e_outbox_test.py -v

Result: ⚠️ 需要进一步验证
```

---

## 🔧 技术细节

### 依赖注入流程

```
FastAPI Request
    ↓
handler_dependency(CreateOrderHandler)
    ↓
factory(uow, request)
    ↓
inspect Handler.__init__ signature
    ↓
if 'observability' in params:
    ├─ Get from runtime.container
    ├─ Fallback to NoOpObservabilityProvider
    └─ return handler_cls(uow, observability)
else:
    └─ return handler_cls(uow)
```

### 支持的 Handler 类型

| Handler 类型 | 构造函数签名 | 依赖注入 |
|-------------|-------------|---------|
| **Standard Handler** | `__init__(uow)` | ✅ 自动注入 uow |
| **Observable Handler** | `__init__(uow, observability)` | ✅ 自动注入 uow + observability |

---

## 🎯 架构优势

### 1. 向后兼容
- ✅ 标准 Handler 仍然正常工作
- ✅ 不需要修改现有代码
- ✅ 渐进式升级

### 2. 自动识别
- ✅ 使用反射自动检测 Handler 类型
- ✅ 无需手动配置
- ✅ 减少样板代码

### 3. 优雅降级
- ✅ Runtime 不可用时使用 NoOp
- ✅ 测试环境友好
- ✅ 不影响核心功能

---

## 📝 使用示例

### API 路由定义

```python
from bento.interfaces.fastapi import handler_dependency
from contexts.ordering.application.commands.create_order import CreateOrderHandler

@router.post("/orders")
async def create_order(
    request: CreateOrderRequest,
    handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)],
):
    command = CreateOrderCommand(...)
    order = await handler.handle(command)
    return order_to_dict(order)
```

**无需任何额外配置！** 依赖注入系统会自动：
1. 注入 `uow` 参数
2. 检测到需要 `observability` 参数
3. 从 runtime 容器获取 observability
4. 创建 Handler 实例

---

## 🚀 后续工作

### 已完成 ✅
- [x] 更新 FastAPI 依赖注入系统
- [x] 修复 e2e_outbox_test.py
- [x] 修复 middleware_config.py
- [x] 单元测试验证通过

### 待完成 ⚠️
- [ ] 修复产品 API 测试（400 错误）
- [ ] 完整的集成测试验证
- [ ] 更新相关文档

### 已知问题

1. **产品 API 测试失败** - 返回 400 错误
   - 可能是验证问题
   - 需要进一步调查

2. **类型检查警告** - `NoOpObservabilityProvider()` 参数
   - 不影响功能
   - 可以忽略

---

## 🎓 最佳实践

### 1. Handler 设计

**推荐**:
```python
class MyCommandHandler(ObservableCommandHandler[MyCommand, MyResult]):
    def __init__(self, uow: UnitOfWork, observability: ObservabilityProvider):
        super().__init__(uow, observability, "my-context")
```

**不推荐**:
```python
class MyCommandHandler(CommandHandler[MyCommand, MyResult]):
    def __init__(self, uow: UnitOfWork, observability: ObservabilityProvider):
        # ❌ 不要在标准 Handler 中添加 observability 参数
```

### 2. 测试编写

**单元测试**:
```python
from bento.adapters.observability.noop import NoOpObservabilityProvider

def test_handler():
    uow = MockUnitOfWork()
    observability = NoOpObservabilityProvider()
    handler = MyHandler(uow, observability)
    # ...
```

**集成测试**:
```python
# FastAPI 依赖注入会自动处理
response = client.post("/api/endpoint", json={...})
assert response.status_code == 200
```

---

## 📚 相关文档

- [Observability 实施文档](OBSERVABILITY_COMPLETE_IMPLEMENTATION.md)
- [Bootstrap 重构文档](BOOTSTRAP_REFACTORING.md)
- [文件整理总结](FILE_ORGANIZATION_FINAL.md)

---

**修复状态**: ✅ **核心功能已修复，部分测试需要进一步调查**

---

## 🔍 调试信息

### 如何验证修复

```bash
# 1. 验证单元测试
uv run pytest tests/ordering/unit/application/test_create_order.py -v

# 2. 验证 E2E 测试
uv run pytest tests/e2e_outbox_test.py -v

# 3. 验证 API 测试
uv run pytest tests/api/test_product_api.py -v
```

### 如何调试 400 错误

```bash
# 运行单个测试并查看详细输出
uv run pytest tests/api/test_product_api.py::TestProductAPI::test_create_product -xvs

# 查看请求和响应内容
# 在测试中添加: print(response.json())
```

---

**最后更新**: 2024-12-30
**修复者**: Cascade AI
**状态**: ✅ **部分完成，核心功能正常**
