# 🎭 Mock Adapters 使用指南

## 📋 概述

Mock Adapters 是用于**开发和测试环境**的模拟实现，提供与真实 Adapters 相同的接口，但不依赖外部服务。

---

## ✅ 已实现的 Mock Adapters

| Adapter | Port 接口 | 用途 | 状态 |
|---------|----------|------|------|
| `MockPaymentAdapter` | `IPaymentService` | 模拟支付处理 | ✅ 完成 |
| `MockNotificationAdapter` | `INotificationService` | 模拟通知发送 | ✅ 完成 |
| `MockInventoryAdapter` | `IInventoryService` | 模拟库存管理 | ✅ 完成 |

---

## 🎯 特性

### 1. MockPaymentAdapter 💳

**特点：**
- ✅ 所有支付自动成功
- ✅ 生成模拟交易ID（`MOCK_xxx`）
- ✅ 内存记录支付历史
- ✅ 支持查询、取消、退款

**使用示例：**

```python
from contexts.ordering.infrastructure.adapters import MockPaymentAdapter
from contexts.ordering.domain.ports.services import (
    PaymentRequest,
    PaymentMethod,
)

# 创建适配器
payment = MockPaymentAdapter()

# 处理支付
request = PaymentRequest(
    order_id="ORDER_001",
    amount=999.99,
    payment_method=PaymentMethod.ALIPAY,
)

result = await payment.process_payment(request)
# result.status == PaymentStatus.SUCCESS
# result.transaction_id == "MOCK_xxxx"

# 查询支付
query_result = await payment.query_payment(result.transaction_id)

# 退款
refund_result = await payment.refund_payment(result.transaction_id, 500.0)
```

**输出示例：**
```
💳 [MockPayment] Payment processed: MOCK_9246BDB40DF84275 - $999.99
🔍 [MockPayment] Query payment: MOCK_9246BDB40DF84275 - Status: SUCCESS
💰 [MockPayment] Refund processed: MOCK_9246BDB40DF84275 - $500.00
```

---

### 2. MockNotificationAdapter 📧

**特点：**
- ✅ 所有通知自动成功
- ✅ 生成模拟通知ID（`NOTIF_xxx`）
- ✅ 控制台输出通知内容（便于调试）
- ✅ 内存记录通知历史

**使用示例：**

```python
from contexts.ordering.infrastructure.adapters import MockNotificationAdapter

# 创建适配器（verbose=True 会打印详细通知内容）
notification = MockNotificationAdapter(verbose=True)

# 发送订单创建通知
result = await notification.send_order_created(
    order_id="ORDER_001",
    customer_email="customer@example.com"
)

# 发送支付成功通知
await notification.send_order_paid("ORDER_001", "customer@example.com")

# 发送发货通知
await notification.send_order_shipped(
    "ORDER_001",
    "customer@example.com",
    "SF1234567890"
)

# 查看通知历史
history = notification.get_notification_history()
count = notification.get_notification_count()
```

**输出示例：**
```
======================================================================
📧 [MockNotification] NOTIF_5DA76C641EB9
======================================================================
收件人: customer@example.com
类型: email
优先级: normal
主题: 订单创建成功
内容:
您的订单 ORDER_001 已创建成功！我们将尽快为您处理。
发送时间: 2025-11-21T15:32:24.522921
======================================================================
```

---

### 3. MockInventoryAdapter 📦

**特点：**
- ✅ 内存管理库存
- ✅ 默认所有产品库存 9999
- ✅ 支持预留、扣减、恢复
- ✅ 生成模拟预留ID（`RSV_xxx`）

**使用示例：**

```python
from contexts.ordering.infrastructure.adapters import MockInventoryAdapter
from contexts.ordering.infrastructure.adapters.services.mock_inventory_adapter import (
    ReservationRequest,
)

# 创建适配器（默认库存 9999）
inventory = MockInventoryAdapter(default_quantity=100)

# 检查库存
is_available = await inventory.check_availability("PROD_001", 10)

# 批量检查
availability = await inventory.check_availability_batch([
    ("PROD_001", 10),
    ("PROD_002", 5),
])

# 获取库存信息
inventory_item = await inventory.get_inventory("PROD_001")
# inventory_item.available_quantity == 100

# 预留库存
request = ReservationRequest(
    order_id="ORDER_001",
    items=[("PROD_001", 10), ("PROD_002", 5)]
)
result = await inventory.reserve_inventory(request)
# result.success == True
# result.reservation_id == "RSV_xxxx"

# 扣减库存
await inventory.deduct_inventory("PROD_001", 10)

# 恢复库存
await inventory.restore_inventory("PROD_001", 5)

# 释放预留
await inventory.release_reservation(result.reservation_id)
```

**输出示例：**
```
📦 [MockInventory] Check availability: PROD_001 - Need: 10, Available: 100, Result: ✅ OK
✅ [MockInventory] Reservation successful: RSV_F0C6D362C4E5 - Order: ORDER_001
➖ [MockInventory] Inventory deducted: PROD_001 - Quantity: 10, Remaining: 90
➕ [MockInventory] Inventory restored: PROD_001 - Quantity: 5, Total: 95
♻️ [MockInventory] Reservation released: RSV_F0C6D362C4E5
```

---

## 🔧 在 Use Case 中使用

### 示例：CreateOrderUseCase

```python
# application/commands/create_order.py
from contexts.ordering.domain.ports import (
    IProductCatalogService,
    IInventoryService,
    INotificationService,
)

class CreateOrderUseCase:
    def __init__(
        self,
        uow: IUnitOfWork,
        product_catalog: IProductCatalogService,
        inventory: IInventoryService,
        notification: INotificationService,
    ):
        self._uow = uow
        self._product_catalog = product_catalog
        self._inventory = inventory
        self._notification = notification

    async def execute(self, command: CreateOrderCommand) -> Order:
        # 1. 验证产品
        products = await self._product_catalog.get_products_info(
            command.product_ids
        )

        # 2. 检查库存
        availability = await self._inventory.check_availability_batch(
            command.items
        )

        if not all(availability.values()):
            raise ApplicationException("库存不足")

        # 3. 预留库存
        reservation_request = ReservationRequest(
            order_id=order_id,
            items=command.items
        )
        reservation = await self._inventory.reserve_inventory(reservation_request)

        if not reservation.success:
            raise ApplicationException("库存预留失败")

        # 4. 创建订单
        order = Order.create(...)
        order_repo = self._uow.repository(Order)
        await order_repo.save(order)

        # 5. 发送通知
        await self._notification.send_order_created(
            order.id,
            command.customer_email
        )

        return order
```

### 依赖注入配置

```python
# interfaces/order_api.py
from contexts.ordering.infrastructure.adapters import (
    ProductCatalogAdapter,
    MockPaymentAdapter,
    MockNotificationAdapter,
    MockInventoryAdapter,
)

def get_create_order_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
):
    """获取 CreateOrderUseCase（使用 Mock Adapters）"""

    # 真实的产品目录服务
    product_catalog = ProductCatalogAdapter(uow.session)

    # Mock 服务（开发/测试环境）
    inventory = MockInventoryAdapter()
    notification = MockNotificationAdapter()

    return CreateOrderUseCase(
        uow,
        product_catalog,
        inventory,
        notification
    )
```

---

## 🧪 运行测试

### 运行 Mock Adapters 测试

```bash
# 在项目根目录执行
uv run python tests/ordering/test_mock_adapters.py
```

### 测试内容

测试文件 `tests/ordering/test_mock_adapters.py` 包含：

1. **单独测试** - 每个 Adapter 的功能测试
2. **协同测试** - 模拟完整订单流程

测试输出示例：

```
🚀 Mock Adapters 测试套件
🚀 ==================================================================

🧪 测试 MockPaymentAdapter
💳 [MockPayment] Payment processed: MOCK_xxx - $999.99
✅ 支付成功！

🧪 测试 MockNotificationAdapter
📧 [MockNotification] NOTIF_xxx
收件人: customer@example.com
主题: 订单创建成功
✅ 通知发送成功

🧪 测试 MockInventoryAdapter
📦 [MockInventory] Check availability: PROD_001 - Need: 10, Available: 100, Result: ✅ OK
✅ 库存检查: 充足

🧪 测试所有 Adapters 协同工作（模拟完整订单流程）
📦 步骤 1: 检查库存... ✅
🔒 步骤 2: 预留库存... ✅
📧 步骤 3: 发送订单创建通知... ✅
💳 步骤 4: 处理支付... ✅
➖ 步骤 5: 扣减库存... ✅
📧 步骤 6: 发送支付成功通知... ✅
📦 步骤 7: 发送发货通知... ✅
🎉 完整订单流程测试完成！

✅ 所有测试完成！
```

---

## 💡 最佳实践

### 1. 根据环境选择 Adapter

```python
import os
from contexts.ordering.infrastructure.adapters import (
    MockPaymentAdapter,
    AlipayAdapter,  # 假设已实现
)

def get_payment_adapter():
    """根据环境变量选择支付适配器"""
    env = os.getenv("ENV", "development")

    if env == "production":
        return AlipayAdapter(
            app_id=os.getenv("ALIPAY_APP_ID"),
            private_key=os.getenv("ALIPAY_PRIVATE_KEY"),
        )
    else:
        # 开发和测试环境使用 Mock
        return MockPaymentAdapter()
```

### 2. 测试中使用 Mock

```python
import pytest
from contexts.ordering.infrastructure.adapters import (
    MockPaymentAdapter,
    MockNotificationAdapter,
)

@pytest.fixture
def payment_adapter():
    """提供 Mock 支付适配器"""
    return MockPaymentAdapter()

@pytest.fixture
def notification_adapter():
    """提供 Mock 通知适配器"""
    return MockNotificationAdapter(verbose=False)  # 测试时关闭详细输出

async def test_create_order(payment_adapter, notification_adapter):
    """测试创建订单"""
    use_case = CreateOrderUseCase(
        uow=mock_uow,
        product_catalog=mock_catalog,
        payment=payment_adapter,
        notification=notification_adapter,
    )

    order = await use_case.execute(command)

    # 验证通知已发送
    assert notification_adapter.get_notification_count() == 1
```

### 3. 自定义库存数量（测试特定场景）

```python
# 测试库存不足场景
inventory = MockInventoryAdapter()
inventory.set_inventory("PROD_001", 5)  # 设置库存为 5

# 尝试购买 10 个会失败
is_available = await inventory.check_availability("PROD_001", 10)
assert is_available == False
```

---

## 🔄 未来：替换为真实 Adapter

当需要切换到生产环境时，只需实现真实的 Adapter：

### 实现真实 Adapter

```python
# infrastructure/adapters/services/alipay_adapter.py
from contexts.ordering.domain.ports.services import IPaymentService

class AlipayAdapter(IPaymentService):
    """支付宝支付适配器"""

    def __init__(self, app_id: str, private_key: str):
        # 初始化支付宝 SDK
        pass

    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        # 调用真实的支付宝 API
        pass
```

### 更新依赖注入

```python
# 只需修改依赖注入配置，Use Case 代码不变
def get_payment_adapter():
    if env == "production":
        return AlipayAdapter(...)  # ✅ 切换到真实实现
    else:
        return MockPaymentAdapter()  # 开发/测试继续用 Mock
```

---

## 📁 文件位置

```
contexts/ordering/infrastructure/adapters/services/
├── product_catalog_adapter.py           # ✅ 真实实现
├── mock_payment_adapter.py              # ✅ Mock 实现
├── mock_notification_adapter.py          # ✅ Mock 实现
└── mock_inventory_adapter.py            # ✅ Mock 实现
```

---

## 🎯 总结

### Mock Adapters 的优势

✅ **快速开发** - 无需依赖外部服务即可开发和测试
✅ **确定性** - 所有操作结果可预测
✅ **零成本** - 不产生真实的支付、短信等费用
✅ **离线工作** - 不需要网络连接
✅ **易于调试** - 控制台输出详细信息
✅ **符合接口** - 与真实 Adapter 完全兼容

### 使用场景

| 场景 | 推荐 Adapter |
|-----|-------------|
| **本地开发** | Mock Adapters |
| **单元测试** | Mock Adapters |
| **集成测试** | Mock Adapters 或 真实 Adapters |
| **预发布环境** | 真实 Adapters |
| **生产环境** | 真实 Adapters |

---

**Mock Adapters 让你可以立即开始开发和测试，无需等待真实服务集成！** 🚀

当需要时，只需实现真实 Adapter 并更新依赖注入配置即可，Use Case 代码完全不需要修改！这就是六边形架构的强大之处！
