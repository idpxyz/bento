# 库存预留服务 (Inventory Reservation Service)

## 📋 概述

`InventoryReservationService` 是一个典型的**领域服务**（Domain Service），用于协调订单（Order）和库存（Inventory）两个聚合根之间的业务逻辑。

### 核心职责

- ✅ 为订单预留库存
- ✅ 检查库存可用性
- ✅ 管理预留生命周期（预留 → 确认 → 释放/完成）
- ✅ 处理过期预留
- ✅ 库存补货建议
- ✅ 预留指标分析

## 🎯 为什么需要领域服务？

在 DDD 中，当业务逻辑需要协调多个聚合根时，不应该将这些逻辑放在任何一个聚合根内部。这时就需要领域服务：

```
❌ 不好的设计：
Order.reserve_inventory(inventory)  # Order 聚合负担过重
Inventory.create_reservation(order)  # Inventory 聚合负担过重

✅ 好的设计：
InventoryReservationService.reserve(order, inventory)  # 独立的领域服务
```

## 🏗️ 架构特点

### 1. 无状态设计
服务本身不保存状态，所有数据通过参数传入：

```python
service = InventoryReservationService()
result = service.reserve_inventory(request, inventory_item)
```

### 2. 跨聚合协调
协调订单和库存两个聚合的业务规则：

```
Order (订单聚合)  ←→  Reservation Service  ←→  Inventory (库存聚合)
```

### 3. 纯业务逻辑
不依赖任何基础设施（数据库、API等），便于测试和复用。

## 🔑 核心概念

### ReservationStatus（预留状态）

```python
class ReservationStatus(str, Enum):
    PENDING = "pending"        # 待处理
    CONFIRMED = "confirmed"    # 已确认
    EXPIRED = "expired"        # 已过期
    RELEASED = "released"      # 已释放
    FULFILLED = "fulfilled"    # 已完成
```

### StockStatus（库存状态）

```python
class StockStatus(str, Enum):
    IN_STOCK = "in_stock"           # 有货
    LOW_STOCK = "low_stock"         # 库存不足
    OUT_OF_STOCK = "out_of_stock"   # 缺货
    DISCONTINUED = "discontinued"    # 已停产
```

## 📝 使用示例

### 1. 检查库存可用性

```python
from applications.ecommerce.modules.order.domain.services import (
    InventoryItem,
    InventoryReservationService,
)

service = InventoryReservationService()

# 创建库存项
inventory = InventoryItem(
    product_id="PROD-123",
    available_quantity=100,
    reserved_quantity=20
)

# 检查可用性
result = service.check_availability(inventory, requested_quantity=10)

# 结果
{
    "product_id": "PROD-123",
    "requested_quantity": 10,
    "available_quantity": 100,
    "is_available": True,
    "stock_status": "in_stock",
    "message": "Product is available"
}
```

### 2. 预留库存（成功订单流程）

```python
from datetime import datetime
from applications.ecommerce.modules.order.domain.services import (
    ReservationRequest,
)

# 步骤 1: 创建预留请求
request = ReservationRequest(
    product_id="PROD-123",
    quantity=10,
    order_id="ORD-456",
    customer_id="CUST-789",
    reservation_duration_minutes=15  # 15分钟后过期
)

# 步骤 2: 预留库存
result = service.reserve_inventory(request, inventory, datetime.now())

# 结果
{
    "success": True,
    "reservation_id": "uuid-here",
    "product_id": "PROD-123",
    "quantity": 10,
    "order_id": "ORD-456",
    "status": "confirmed",
    "expires_at": "2025-01-01T12:15:00",
    "new_available_quantity": 90,
    "new_reserved_quantity": 30,
    "message": "Successfully reserved 10 units"
}

# 步骤 3: 客户完成支付 - 完成订单
fulfill_result = service.fulfill_reservation(reservation, datetime.now())
# 库存将从 reserved 转为 fulfilled，真正扣减
```

### 3. 释放预留（取消订单流程）

```python
# 客户取消订单
release_result = service.release_reservation(
    reservation,
    reason="customer_cancelled",
    current_time=datetime.now()
)

# 结果
{
    "success": True,
    "reservation_id": "uuid-here",
    "quantity_released": 10,
    "status": "released",
    "reason": "customer_cancelled",
    "message": "Released 10 units back to inventory"
}
```

### 4. 处理过期预留

```python
# 检查过期的预留
expired = service.check_expired_reservations(
    reservations_list,
    current_time=datetime.now()
)

# 批量释放过期预留
for expired_reservation in expired:
    service.release_reservation(
        expired_reservation,
        reason="timeout",
        current_time=datetime.now()
    )
```

### 5. 库存补货建议

```python
# 基于销售速度推荐补货
recommendation = service.recommend_stock_replenishment(
    inventory_item,
    sales_velocity=15.0  # 每天销售15件
)

if recommendation:
    # {
    #     "product_id": "PROD-123",
    #     "urgency": "high",
    #     "recommended_quantity": 450,
    #     "days_until_stockout": 3.0,
    #     "reason": "low_stock",
    #     "message": "Stock will run out in 3.0 days"
    # }
    print(f"⚠️ {recommendation['message']}")
    print(f"建议补货: {recommendation['recommended_quantity']} 件")
```

## 🔄 完整业务流程

### 场景1：订单成功完成

```
1. 客户添加商品到购物车
   ↓
2. 检查库存可用性 (check_availability)
   ↓
3. 创建订单 + 预留库存 (reserve_inventory)
   ↓
4. 客户完成支付
   ↓
5. 完成预留，扣减库存 (fulfill_reservation)
   ↓
6. 发货
```

### 场景2：订单被取消

```
1. 客户添加商品到购物车
   ↓
2. 检查库存可用性
   ↓
3. 创建订单 + 预留库存 (reserve_inventory)
   ↓
4. 客户取消订单
   ↓
5. 释放预留，恢复库存 (release_reservation)
```

### 场景3：预留超时

```
1. 客户添加商品到购物车
   ↓
2. 预留库存 (15分钟有效期)
   ↓
3. 客户超过15分钟未支付
   ↓
4. 后台任务检测过期预留 (check_expired_reservations)
   ↓
5. 自动释放预留 (release_reservation with reason="timeout")
```

## 🧪 测试覆盖

服务包含全面的测试套件（30个测试用例）：

```bash
cd /workspace/bento
uv run pytest applications/ecommerce/tests/test_inventory_reservation_service.py -v
```

测试类别：
- ✅ 库存项和预留对象测试
- ✅ 可用性检查测试
- ✅ 预留创建和管理测试
- ✅ 状态转换测试
- ✅ 过期处理测试
- ✅ 指标计算测试
- ✅ 补货建议测试
- ✅ 完整生命周期场景测试

## 📊 实际运行示例

运行完整的使用示例：

```bash
cd /workspace/bento
PYTHONPATH=/workspace/bento uv run python applications/ecommerce/examples/inventory_reservation_example.py
```

这将演示：
1. ✅ 成功订单流程
2. ✅ 取消订单流程
3. ⚠️ 库存不足处理
4. 🔄 过期预留清理
5. 📊 预留指标分析
6. 📦 库存补货建议

## 🎨 设计原则与最佳实践

### 1. 单一职责原则
每个方法专注于一个具体任务：
- `check_availability` - 只检查可用性
- `reserve_inventory` - 只处理预留
- `release_reservation` - 只处理释放

### 2. 显式依赖
所有依赖通过参数传入，没有隐藏依赖：
```python
service.reserve_inventory(request, inventory_item, current_time)
```

### 3. 返回详细信息
方法返回完整的操作结果，便于调试和审计：
```python
{
    "success": True,
    "reservation_id": "...",
    "message": "...",
    "new_available_quantity": 90,
    # ... 更多信息
}
```

### 4. 时间注入（可测试性）
接受 `current_time` 参数，便于时间相关逻辑的测试：
```python
# 生产环境
service.reserve_inventory(request, inventory)

# 测试环境
service.reserve_inventory(request, inventory, fixed_time)
```

### 5. 业务规则集中
所有库存预留相关的业务规则都在服务中：
- 预留时长（15分钟）
- 低库存阈值（20%）
- 补货策略（30天供应量）

## 🔗 相关组件

- **OrderPricingService**: 订单定价服务（另一个领域服务示例）
- **Order Aggregate**: 订单聚合根
- **Inventory Aggregate**: 库存聚合根

## 📚 进一步阅读

- [DDD 领域服务模式](https://martinfowler.com/bliki/DomainService.html)
- [跨聚合协调](https://vaughnvernon.com/domain-driven-design/)
- [电商库存管理最佳实践](https://www.thoughtworks.com/insights/blog/inventory-management)

---

**作者**: Bento Framework Team
**版本**: 1.0.0
**最后更新**: 2025-11-05

