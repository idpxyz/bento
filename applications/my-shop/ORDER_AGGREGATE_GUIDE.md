# Order 聚合完整实现指南

## 📦 聚合结构

```
Order (聚合根)
  ├── OrderItem (实体)
  ├── OrderItem (实体)
  └── OrderItem (实体)
```

## 🎯 核心概念

### Order - 订单聚合根
Order 是订单上下文的聚合根，负责管理订单的整个生命周期。

**字段：**
- `id` - 订单ID
- `customer_id` - 客户ID
- `items` - 订单项列表 (list[OrderItem])
- `total` - 订单总额（自动计算）
- `status` - 订单状态 (OrderStatus 枚举)
- `created_at` - 创建时间
- `paid_at` - 支付时间
- `shipped_at` - 发货时间

**状态流转：**
```
PENDING → PAID → SHIPPED → DELIVERED
    ↓        ↓
CANCELLED  CANCELLED
```

### OrderItem - 订单项实体
OrderItem 是 Order 聚合内的实体，代表订单中的一个商品项。

**字段：**
- `id` - 订单项ID
- `order_id` - 所属订单ID
- `product_id` - 产品ID
- `product_name` - 产品名称
- `quantity` - 数量
- `unit_price` - 单价
- `subtotal` - 小计（计算属性）

## 📝 业务规则

### 1. 订单创建规则
- 订单必须至少有一个订单项
- 订单总额由所有订单项小计之和计算
- 新订单默认状态为 PENDING（待支付）

### 2. 订单项管理规则
- 只有待支付订单可以添加/删除订单项
- 删除订单项后，订单必须至少保留一个订单项
- 数量必须大于 0
- 单价不能为负数

### 3. 支付规则
- 只有待支付订单可以确认支付
- 支付成功后状态变为 PAID
- 触发 OrderPaidEvent 事件

### 4. 发货规则
- 只有已支付订单可以发货
- 发货后状态变为 SHIPPED
- 触发 OrderShippedEvent 事件

### 5. 送达规则
- 只有已发货订单可以确认送达
- 送达后状态变为 DELIVERED
- 触发 OrderDeliveredEvent 事件

### 6. 取消规则
- 只有待支付或已支付的订单可以取消
- 已发货的订单无法取消
- 触发 OrderCancelledEvent 事件

## 💻 使用示例

### 创建订单并添加商品

```python
from contexts.ordering.domain.order import Order, OrderStatus
from contexts.ordering.domain.orderitem import OrderItem

# 1. 创建空订单
order = Order(
    id="order-12345",
    customer_id="customer-001"
)

# 2. 添加订单项
order.add_item(
    product_id="product-001",
    product_name="MacBook Pro 16",
    quantity=1,
    unit_price=18999.00
)

order.add_item(
    product_id="product-002",
    product_name="Magic Mouse",
    quantity=2,
    unit_price=699.00
)

# 3. 查看订单信息
print(f"订单总额: ¥{order.total}")  # 20397.00
print(f"订单项数: {len(order.items)}")  # 2
print(f"订单状态: {order.status.value}")  # pending
```

### 处理订单支付

```python
# 确认支付
order.confirm_payment()

# 状态变为 PAID
assert order.status == OrderStatus.PAID
assert order.paid_at is not None

# 触发领域事件
events = order.collect_events()
assert any(isinstance(e, OrderPaidEvent) for e in events)
```

### 订单发货

```python
# 发货
order.ship(tracking_number="SF1234567890")

# 状态变为 SHIPPED
assert order.status == OrderStatus.SHIPPED
assert order.shipped_at is not None
```

### 确认送达

```python
# 确认送达
order.deliver()

# 状态变为 DELIVERED
assert order.status == OrderStatus.DELIVERED
```

### 取消订单

```python
# 取消待支付订单
order_pending = Order(id="order-001", customer_id="cust-001")
order_pending.add_item("prod-001", "Product A", 1, 100.0)
order_pending.cancel(reason="客户要求取消")

assert order_pending.status == OrderStatus.CANCELLED
```

### 错误处理

```python
# 示例：尝试修改已支付订单的订单项（会抛出异常）
try:
    order.confirm_payment()
    order.add_item("prod-003", "Product C", 1, 50.0)
except ValueError as e:
    print(f"错误: {e}")  # "只有待支付订单可以修改订单项"

# 示例：尝试发货未支付订单（会抛出异常）
try:
    pending_order = Order(id="order-002", customer_id="cust-002")
    pending_order.add_item("prod-001", "Product A", 1, 100.0)
    pending_order.ship()
except ValueError as e:
    print(f"错误: {e}")  # "只有已支付订单可以发货"
```

## 🔄 领域事件

### 已实现的事件

| 事件 | 触发时机 | 用途 |
|-----|---------|-----|
| `OrderCreatedEvent` | 订单创建 | 通知其他上下文 |
| `OrderPaidEvent` | 支付成功 | 扣减库存、发送通知 |
| `OrderShippedEvent` | 订单发货 | 更新物流、发送通知 |
| `OrderDeliveredEvent` | 确认送达 | 触发评价流程 |
| `OrderCancelledEvent` | 订单取消 | 释放库存、处理退款 |

## 📊 数据模型

### Order 聚合根字段

```python
@dataclass
class Order(AggregateRoot):
    id: str                                    # 订单ID
    customer_id: str                           # 客户ID
    items: list[OrderItem]                     # 订单项列表
    total: float = 0.0                         # 总额
    status: OrderStatus = OrderStatus.PENDING  # 状态
    created_at: datetime | None = None         # 创建时间
    paid_at: datetime | None = None            # 支付时间
    shipped_at: datetime | None = None         # 发货时间
```

### OrderItem 实体字段

```python
@dataclass
class OrderItem(AggregateRoot):
    id: str            # 订单项ID
    order_id: str      # 所属订单ID
    product_id: str    # 产品ID
    product_name: str  # 产品名称
    quantity: int      # 数量
    unit_price: float  # 单价

    @property
    def subtotal(self) -> float:
        """小计 = 数量 × 单价"""
        return self.quantity * self.unit_price
```

## 🧪 测试建议

### 单元测试

```python
# tests/ordering/unit/domain/test_order.py

def test_order_calculate_total():
    """测试订单总额计算"""
    order = Order(id="order-001", customer_id="cust-001")
    order.add_item("prod-1", "Product 1", 2, 100.0)
    order.add_item("prod-2", "Product 2", 1, 50.0)

    assert order.total == 250.0

def test_order_payment_flow():
    """测试支付流程"""
    order = Order(id="order-001", customer_id="cust-001")
    order.add_item("prod-1", "Product 1", 1, 100.0)

    # 确认支付
    order.confirm_payment()
    assert order.status == OrderStatus.PAID
    assert order.paid_at is not None

def test_order_cannot_ship_unpaid():
    """测试未支付订单不能发货"""
    order = Order(id="order-001", customer_id="cust-001")
    order.add_item("prod-1", "Product 1", 1, 100.0)

    with pytest.raises(ValueError, match="只有已支付订单可以发货"):
        order.ship()

def test_orderitem_subtotal():
    """测试订单项小计计算"""
    item = OrderItem(
        id="item-1",
        order_id="order-1",
        product_id="prod-1",
        product_name="Product 1",
        quantity=3,
        unit_price=100.0
    )

    assert item.subtotal == 300.0
```

## 🚀 下一步

### 需要实现的功能

1. **持久化**
   - 实现 OrderRepository
   - 配置数据库映射
   - 处理级联保存（Order → OrderItem）

2. **用例实现**
   - `CreateOrderUseCase` - 创建订单
   - `PayOrderUseCase` - 处理支付
   - `ShipOrderUseCase` - 发货
   - `CancelOrderUseCase` - 取消订单

3. **集成事件**
   - 监听 `ProductPriceChanged` 事件
   - 发布 `OrderPaid` 到库存上下文

4. **API 端点**
   - `POST /orders` - 创建订单
   - `POST /orders/{id}/pay` - 支付
   - `POST /orders/{id}/ship` - 发货
   - `POST /orders/{id}/cancel` - 取消

## ✅ 完成状态

- ✅ Order 聚合根定义
- ✅ OrderItem 实体定义
- ✅ OrderStatus 枚举
- ✅ 业务方法实现
- ✅ 领域事件定义
- ✅ 验证逻辑
- ✅ 状态机管理
- ⏳ 持久化实现
- ⏳ 用例实现
- ⏳ API 实现

---

**总结：** Order 聚合现在已经完整实现，包含 OrderItem 实体和完整的业务逻辑！🎉
