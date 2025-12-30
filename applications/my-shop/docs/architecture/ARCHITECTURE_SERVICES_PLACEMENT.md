# Services 正确放置指南（修正版）

## 🎯 三层决策树

### 第一优先：聚合根内部方法
**位置**: `domain/order.py`（聚合根文件内）

**何时使用**：
- ✅ 只涉及单个聚合根的操作
- ✅ 维护聚合根的不变性约束
- ✅ 操作自己的数据

### 第二优先：Domain Service
**位置**: `domain/services/`

**何时使用**：
- ✅ 跨多个聚合根的业务逻辑
- ✅ 不依赖 Repository
- ✅ 纯业务规则

### 第三优先：Application Service
**位置**: `application/services/`

**何时使用**：
- ✅ 需要访问数据库（Repository）
- ✅ 需要调用外部服务
- ✅ 编排多个操作

## 📋 正确示例

### ✅ 第一层：聚合根方法（最常用）

```python
# domain/order.py
class Order(AggregateRoot):
    """订单聚合根"""

    def __init__(self, id: ID, customer_id: str):
        super().__init__(id=str(id))
        self.customer_id = customer_id
        self.items: list[OrderItem] = []
        self.total: float = 0.0

    # ✅ 添加订单项 - 聚合根内部方法
    def add_item(self, product_id: str, quantity: int, unit_price: float) -> None:
        """添加订单项"""
        if quantity <= 0:
            raise ValueError("数量必须大于0")

        item = OrderItem(
            id=ID.generate(),
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price
        )
        self.items.append(item)
        self._recalculate_total()  # 维护不变性

    # ✅ 计算总额 - 私有方法
    def _recalculate_total(self) -> None:
        """重新计算总额"""
        self.total = sum(item.subtotal for item in self.items)

    # ✅ 取消订单 - 聚合根方法
    def cancel(self) -> None:
        """取消订单"""
        if self.status not in [OrderStatus.PENDING, OrderStatus.PAID]:
            raise CannotCancelOrderError("只有待支付或已支付的订单可以取消")

        self.status = OrderStatus.CANCELLED
        self.add_event(OrderCancelled(order_id=self.id))

    # ✅ 判断是否需要审批 - 业务规则
    def requires_approval(self) -> bool:
        """判断订单是否需要审批"""
        return self.total >= 10000 or len(self.items) >= 100

    # ✅ 验证订单 - 业务规则
    def validate(self) -> None:
        """验证订单"""
        if not self.items:
            raise EmptyOrderError()
        if self.total <= 0:
            raise InvalidTotalError()
```

**何时不需要 Domain Service**：
- ❌ 不要为 `calculate_total()` 创建单独的 Service
- ❌ 不要为 `validate()` 创建单独的 Service
- ❌ 不要为单个聚合根的逻辑创建 Service

### ✅ 第二层：Domain Service（跨聚合根时）

```python
# domain/services/pricing_service.py
class PricingService:
    """定价服务 - 真正需要 Domain Service 的场景"""

    def calculate_discounted_price(
        self,
        product: Product,      # 聚合根1
        customer: Customer,    # 聚合根2
        quantity: int,
        promotions: list[Promotion]  # 聚合根3
    ) -> Money:
        """计算折扣价格

        为什么需要 Domain Service：
        - 涉及 3 个不同的聚合根
        - 复杂的业务规则
        - 不依赖 Repository（所有对象已加载）
        """
        base_price = product.price * quantity

        # 客户等级折扣
        if customer.is_vip():
            base_price *= 0.95

        # 批量折扣
        if quantity >= 10:
            base_price *= 0.9

        # 促销活动折扣
        for promo in promotions:
            if promo.applies_to(product, customer):
                base_price = promo.calculate_discount(base_price)

        return Money(base_price)

    def can_combine_orders(
        self,
        order1: Order,  # 聚合根1
        order2: Order   # 聚合根2
    ) -> bool:
        """判断两个订单是否可以合并

        为什么需要 Domain Service：
        - 跨两个 Order 聚合根
        - 纯业务逻辑判断
        """
        return (
            order1.customer_id == order2.customer_id and
            order1.status == OrderStatus.PENDING and
            order2.status == OrderStatus.PENDING
        )


# domain/services/transfer_service.py
class MoneyTransferService:
    """转账服务 - 经典的 Domain Service 场景"""

    def transfer(
        self,
        from_account: Account,  # 聚合根1
        to_account: Account,    # 聚合根2
        amount: Money
    ) -> None:
        """执行转账

        为什么需要 Domain Service：
        - 必须同时操作两个聚合根
        - 保证原子性的业务逻辑
        """
        from_account.debit(amount)  # 扣款
        to_account.credit(amount)   # 入账
```

### ✅ 第三层：Application Service（最常见）

```python
# application/services/order_analytics_service.py
class OrderAnalyticsService:
    """订单分析服务 - 正确的 Application Service"""

    def __init__(self, order_repo: OrderRepository):
        self._repo = order_repo  # ✅ 依赖 Repository

    async def get_revenue_stats(self) -> dict:
        """获取收入统计

        为什么是 Application Service：
        - 需要访问数据库（Repository）
        - 查询和统计功能
        - 不是纯业务逻辑
        """
        return {
            "total": await self._repo.sum_field("total"),
            "avg": await self._repo.avg_field("total"),
            "count": await self._repo.count_field("id")
        }

    async def get_customer_lifetime_value(self, customer_id: str) -> float:
        """计算客户终身价值

        为什么是 Application Service：
        - 需要查询数据库
        """
        orders = await self._repo.find_all_by_field("customer_id", customer_id)
        return sum(order.total for order in orders)


# application/commands/create_order.py
class CreateOrderUseCase:
    """创建订单用例 - 编排多个操作"""

    def __init__(
        self,
        order_repo: IOrderRepository,
        product_repo: IProductRepository,
        inventory_service: IInventoryService,
        notification_service: INotificationService,
        pricing_service: PricingService,  # 可以注入 Domain Service
        uow: IUnitOfWork
    ):
        self._order_repo = order_repo
        self._product_repo = product_repo
        self._inventory_service = inventory_service
        self._notification_service = notification_service
        self._pricing_service = pricing_service
        self._uow = uow

    async def handle(self, command: CreateOrderCommand) -> OrderId:
        """创建订单

        为什么是 Application Service：
        - 需要访问多个 Repository
        - 调用外部服务
        - 编排多个操作
        - 事务管理
        """
        # 1. 加载数据（基础设施操作）
        products = await self._product_repo.get_by_ids(command.product_ids)
        customer = await self._customer_repo.get(command.customer_id)

        # 2. 创建聚合根
        order = Order(id=ID.generate(), customer_id=command.customer_id)

        # 3. 调用聚合根方法（领域逻辑）
        for item in command.items:
            # 可选：调用 Domain Service 计算价格
            price = self._pricing_service.calculate_discounted_price(
                products[item.product_id],
                customer,
                item.quantity,
                []
            )
            order.add_item(item.product_id, item.quantity, price.amount)

        # 4. 调用聚合根方法（领域逻辑）
        order.validate()

        # 5. 持久化（基础设施操作）
        await self._order_repo.save(order)

        # 6. 调用外部服务（基础设施操作）
        for item in command.items:
            await self._inventory_service.deduct(item.product_id, item.quantity)

        # 7. 发送通知（基础设施操作）
        await self._notification_service.send_order_confirmation(order.id)

        # 8. 提交事务
        await self._uow.commit()

        return order.id


# application/commands/cancel_order.py
class CancelOrderUseCase:
    """取消订单用例 - 编排多个操作"""

    async def handle(self, command: CancelOrderCommand):
        """取消订单

        Application Service 的典型职责：
        - 加载聚合根
        - 调用聚合根方法
        - 调用外部服务
        - 事务管理
        """
        # 1. 加载聚合根（基础设施）
        order = await self._order_repo.get(command.order_id)

        # 2. 调用领域逻辑
        order.cancel()  # 聚合根方法

        # 3. 保存（基础设施）
        await self._order_repo.save(order)

        # 4. 退款（外部服务）
        await self._payment_service.refund(order.id)

        # 5. 恢复库存（外部服务）
        for item in order.items:
            await self._inventory_service.restore(item.product_id, item.quantity)

        # 6. 通知（外部服务）
        await self._notification_service.send_cancellation(order.customer_id)
```

## 📊 快速决策表

| 场景 | 放在哪里 | 示例 |
|------|---------|------|
| 计算订单总额 | ✅ 聚合根 | `order.calculate_total()` |
| 验证订单 | ✅ 聚合根 | `order.validate()` |
| 取消订单 | ✅ 聚合根 | `order.cancel()` |
| 跨聚合根定价 | ✅ Domain Service | `pricing_service.calculate()` |
| 转账（两个账户） | ✅ Domain Service | `transfer_service.transfer()` |
| 查询统计 | ✅ Application Service | `analytics.get_stats()` |
| 创建订单（含外部调用） | ✅ Application Service | `create_order_use_case.handle()` |

## 🎯 你的项目评估

### OrderAnalyticsService - ✅ 完全正确

```python
# application/services/order_analytics_service.py
class OrderAnalyticsService:
    def __init__(self, order_repo: OrderRepository):
        self._repo = order_repo  # 依赖 Repository

    async def get_total_revenue(self):
        return await self._repo.sum_field("total")  # 查询数据库
```

**位置正确的原因**：
1. ✅ 依赖 Repository（基础设施）
2. ✅ 执行查询统计
3. ✅ 不是单个聚合根的逻辑
4. ✅ 不是跨聚合根的纯业务逻辑

## 💡 关键原则

1. **首选聚合根内部方法** - 80% 的业务逻辑应该在这里
2. **谨慎使用 Domain Service** - 只在真正跨聚合根且不依赖基础设施时
3. **Application Service 负责编排** - 协调、Repository、外部服务

## ❌ 常见错误

```python
# ❌ 错误：不需要的 Domain Service
class OrderDomainService:
    def calculate_total(self, order: Order):
        return sum(item.subtotal for item in order.items)

# ✅ 正确：直接在聚合根内
class Order:
    def calculate_total(self):
        return sum(item.subtotal for item in self.items)
```

---

**总结**：你的 OrderAnalyticsService 放置完全正确！继续保持这种架构意识！
