# Idempotency 最佳实践 - 纯 Header 方式

## 🎯 设计原则

作为一个全新的 framework，我们采用**纯 HTTP Header 方式**处理幂等性，遵循以下原则：

### 1. 遵循 HTTP 标准
- 幂等性是 HTTP 层的概念，应该在 Header 中处理
- 符合 RESTful API 最佳实践
- 与其他主流 API（Stripe, AWS, GitHub）保持一致

### 2. 关注点分离
- **Middleware 层**：处理基础设施关注点（幂等性、认证、日志）
- **应用层**：处理业务逻辑（订单、支付、发货）
- 清晰的职责边界

### 3. 简单性
- 一个地方定义（HTTP Header）
- 一个地方使用（IdempotencyMiddleware）
- 不需要在 Request Body 和 Command 中传递

## 📋 重构内容

### 已移除的字段

#### API Request 模型
```python
# ❌ 旧设计
class CreateOrderRequest(BaseModel):
    customer_id: str
    items: list[OrderItemRequest]
    idempotency_key: str | None = None  # 不再需要

# ✅ 新设计
class CreateOrderRequest(BaseModel):
    """Create order request model.

    Note: For idempotency, pass x-idempotency-key in HTTP Header.
    """
    customer_id: str
    items: list[OrderItemRequest]
```

#### Command 模型
```python
# ❌ 旧设计
@dataclass
class CreateOrderCommand:
    customer_id: str
    items: list[OrderItemInput]
    idempotency_key: str | None = None  # 不再需要

# ✅ 新设计
@dataclass
class CreateOrderCommand:
    """Create order command.

    Note: Idempotency is handled by IdempotencyMiddleware at HTTP layer.
    """
    customer_id: str
    items: list[OrderItemInput]
```

### 修复的问题

#### IdempotencyMiddleware Session 获取

**问题**：Middleware 无法获取数据库 session，导致幂等性检查被跳过

**解决方案**：依赖注入 session_factory

```python
# ❌ 旧方式（容易失败）
try:
    from runtime.bootstrap_v2 import get_runtime
    runtime = get_runtime()
    session_factory = runtime.container.get("db.session_factory")
except Exception:
    return await call_next(request)  # 跳过幂等性检查

# ✅ 新方式（可靠）
def __init__(self, app, session_factory=None, ...):
    self.session_factory = session_factory

# 在 bootstrap 中注入
session_factory = runtime.container.get("db.session_factory")
app.add_middleware(
    IdempotencyMiddleware,
    session_factory=session_factory,
    ...
)
```

## 🔧 使用方式

### 客户端使用

```bash
# 创建订单
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: order-20251229-001" \
  -d '{
    "customer_id": "cust-001",
    "items": [
      {
        "product_id": "prod-123",
        "product_name": "iPhone 15",
        "quantity": 1,
        "unit_price": 999.99
      }
    ]
  }'

# 支付订单
curl -X POST http://localhost:8000/api/v1/orders/{order_id}/pay \
  -H "x-idempotency-key: payment-{order_id}-001" \
  -d '{}'

# 发货订单
curl -X POST http://localhost:8000/api/v1/orders/{order_id}/ship \
  -H "x-idempotency-key: shipment-{order_id}-001" \
  -d '{
    "tracking_number": "SF123456"
  }'
```

### 服务端配置

```python
# runtime/bootstrap_v2.py

# 获取 session_factory
session_factory = runtime.container.get("db.session_factory")

# 注册 IdempotencyMiddleware（注入 session_factory）
app.add_middleware(
    IdempotencyMiddleware,
    header_name="x-idempotency-key",
    ttl_seconds=86400,  # 24 hours
    tenant_id="default",
    session_factory=session_factory,  # ✅ 注入依赖
)
```

## 🎨 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      HTTP Request                        │
│  POST /api/v1/orders/                                   │
│  Header: x-idempotency-key: order-20251229-001         │
│  Body: {"customer_id": "cust-001", "items": [...]}     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              IdempotencyMiddleware                       │
│  1. 读取 x-idempotency-key header                       │
│  2. 计算 request body hash                              │
│  3. 检查数据库中是否有相同 key 的请求                    │
│  4. 如果存在且已完成，返回缓存的响应                      │
│  5. 如果不存在，继续处理请求                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   API Layer                              │
│  - 解析 Request → Command                               │
│  - 不需要处理 idempotency_key                           │
│  - 专注于业务逻辑                                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                Application Layer                         │
│  - 执行 Command Handler                                 │
│  - 不需要处理 idempotency_key                           │
│  - 专注于业务规则                                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Domain Layer                            │
│  - 执行领域逻辑                                          │
│  - 发布领域事件                                          │
└─────────────────────────────────────────────────────────┘
```

## ✅ 优势

### 1. 符合标准
- HTTP Header 是幂等性的标准位置
- 与 Stripe、AWS、GitHub 等主流 API 一致
- 易于理解和使用

### 2. 关注点分离
- Middleware 处理基础设施关注点
- 应用层专注于业务逻辑
- 清晰的职责边界

### 3. 简单性
- Request/Command 模型更简洁
- 不需要在多个层级传递 idempotency_key
- 减少代码重复

### 4. 可靠性
- 依赖注入 session_factory，避免获取失败
- 幂等性检查不会被跳过
- 更容易测试和调试

### 5. 性能
- 在 HTTP 层处理，避免不必要的应用层处理
- 缓存整个响应，包括状态码和 body
- 减少数据库查询

## 📊 对比

| 方面 | 旧设计（Body） | 新设计（Header） |
|------|---------------|-----------------|
| **符合标准** | ❌ 不符合 HTTP 标准 | ✅ 符合 HTTP 标准 |
| **关注点分离** | ❌ 混合基础设施和业务 | ✅ 清晰分离 |
| **代码简洁性** | ❌ 需要在多层传递 | ✅ 只在 HTTP 层处理 |
| **可靠性** | ❌ 容易被跳过 | ✅ 依赖注入保证执行 |
| **测试难度** | ❌ 需要测试多层 | ✅ 只测试 Middleware |
| **文档清晰度** | ❌ 容易混淆 | ✅ 清晰明确 |

## 🔍 实施检查清单

### API 层
- [x] 从所有 Request 模型中移除 `idempotency_key` 字段
- [x] 在 docstring 中说明使用 HTTP Header
- [x] 更新 API 文档示例

### 应用层
- [x] 从所有 Command 模型中移除 `idempotency_key` 字段
- [x] 在 docstring 中说明幂等性由 Middleware 处理
- [x] 移除 Command Handler 中的幂等性逻辑

### 基础设施层
- [x] 修改 IdempotencyMiddleware 支持依赖注入
- [x] 在 bootstrap 中注入 session_factory
- [x] 移除 IdempotencyBridgeMiddleware（不再需要）

### 测试
- [ ] 更新测试脚本使用 Header 方式
- [ ] 验证幂等性正常工作
- [ ] 验证相同 key 返回缓存响应
- [ ] 验证不同 key 创建新记录

### 文档
- [x] 创建最佳实践文档
- [ ] 更新 API 文档
- [ ] 更新使用指南

## 🚀 下一步

1. **更新测试脚本**：将所有测试改为使用 Header 方式
2. **验证功能**：运行测试确保幂等性正常工作
3. **更新文档**：确保所有文档反映新的设计
4. **清理代码**：删除不再需要的文件和代码

## 📝 示例代码

### JavaScript/TypeScript 客户端

```typescript
async function createOrder(orderData: OrderData, idempotencyKey: string) {
  const response = await fetch('http://localhost:8000/api/v1/orders/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-idempotency-key': idempotencyKey,  // ✅ 在 Header 中
    },
    body: JSON.stringify(orderData),  // ✅ Body 中不包含 idempotency_key
  });

  return await response.json();
}

// 使用
const key = `order-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
const order = await createOrder({
  customer_id: 'cust-001',
  items: [...]
}, key);
```

### Python 客户端

```python
import requests
import time
import random
import string

def create_order(order_data: dict, idempotency_key: str):
    response = requests.post(
        'http://localhost:8000/api/v1/orders/',
        headers={
            'Content-Type': 'application/json',
            'x-idempotency-key': idempotency_key,  # ✅ 在 Header 中
        },
        json=order_data,  # ✅ Body 中不包含 idempotency_key
    )
    return response.json()

# 使用
key = f"order-{int(time.time())}-{''.join(random.choices(string.ascii_lowercase, k=6))}"
order = create_order({
    'customer_id': 'cust-001',
    'items': [...]
}, key)
```

## 🎓 总结

**最佳实践 = 纯 HTTP Header 方式**

- ✅ 符合 HTTP 标准
- ✅ 关注点分离
- ✅ 代码简洁
- ✅ 可靠性高
- ✅ 易于测试
- ✅ 性能优秀

这是一个全新的 framework，我们选择了最佳的设计方案，为未来的扩展和维护打下坚实的基础。
