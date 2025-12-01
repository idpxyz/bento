# Bento Framework DDD实践指南

## 1. 架构分层指南

### Domain Layer (领域层)
**职责**: 纯业务逻辑，无基础设施依赖

```python
# ✅ 正确的Domain设计
class Order(AggregateRoot):
    def place_order(self, items: list[OrderItem]) -> None:
        """纯业务逻辑"""
        if not items:
            raise DomainException("Order must have items")

        self._validate_items(items)
        self.status = OrderStatus.PLACED
        self.add_event(OrderPlacedEvent(self.id, items))

class OrderDomainService(DomainService):
    @staticmethod
    def calculate_total_price(order: Order, pricing_rules: PricingRules) -> Money:
        """跨聚合的业务逻辑"""
        # 纯计算，无副作用
        return pricing_rules.calculate(order.items)
```

### Application Layer (应用层)
**职责**: 协调Domain对象，管理事务和用例

```python
# ✅ 标准的ApplicationService
class OrderApplicationService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def place_order(self, command: PlaceOrderCommand) -> OrderResult:
        """标准的用例实现模式"""
        async with self.uow:
            # 1. 加载聚合
            customer_repo = self.uow.repository(Customer)
            product_repo = self.uow.repository(Product)

            customer = await customer_repo.get(command.customer_id)
            products = await product_repo.find_by_ids(command.product_ids)

            # 2. 执行领域逻辑
            order = Order.create_new(customer, products)
            total = OrderDomainService.calculate_total_price(order, PricingRules())
            order.set_total(total)

            # 3. 保存 (UoW自动处理事件)
            order_repo = self.uow.repository(Order)
            await order_repo.save(order)
            await self.uow.commit()

            return OrderResult.success(order.id)
```

### Infrastructure Layer (基础设施层)
**职责**: 技术实现，数据访问，外部集成

```python
# ✅ Repository适配器
class OrderRepositoryAdapter(RepositoryAdapter[Order, OrderPO, str]):
    """标准的Repository实现"""
    pass

# ✅ 外部服务适配器
class PaymentServiceAdapter:
    def __init__(self, payment_api: PaymentAPI):
        self.payment_api = payment_api

    async def process_payment(self, payment_request: PaymentRequest) -> PaymentResult:
        # 适配外部API到Domain概念
        pass
```

## 2. 常见模式和最佳实践

### 聚合设计模式
```python
# ✅ 聚合根设计最佳实践
class ShoppingCart(AggregateRoot):
    def __init__(self, customer_id: CustomerId):
        super().__init__(ShoppingCartId.generate())
        self.customer_id = customer_id
        self._items: list[CartItem] = []
        self._total = Money.zero()

    def add_item(self, product: Product, quantity: int) -> None:
        """聚合内部一致性保证"""
        if quantity <= 0:
            raise DomainException("Quantity must be positive")

        existing_item = self._find_item(product.id)
        if existing_item:
            existing_item.increase_quantity(quantity)
        else:
            self._items.append(CartItem(product, quantity))

        self._recalculate_total()
        self.add_event(ItemAddedToCartEvent(self.id, product.id, quantity))

    def _recalculate_total(self) -> None:
        """私有方法维护内部一致性"""
        self._total = sum(item.subtotal for item in self._items)
```

### 事件驱动模式
```python
# ✅ 领域事件设计
@dataclass(frozen=True)
class OrderPlacedEvent(DomainEvent):
    order_id: str = ""
    customer_id: str = ""
    total_amount: str = ""
    topic: str = "order.placed"

# ✅ 事件处理器
class OrderEventHandler:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    async def handle_order_placed(self, event: OrderPlacedEvent) -> None:
        """事件处理保持幂等性"""
        await self.email_service.send_order_confirmation(
            event.customer_id, event.order_id
        )
```

### UnitOfWork模式
```python
# ✅ 复杂用例的事务管理
class OrderFulfillmentService:
    async def fulfill_order(self, order_id: str) -> FulfillmentResult:
        async with self.uow:
            # 多个聚合的协调操作
            order_repo = self.uow.repository(Order)
            inventory_repo = self.uow.repository(Inventory)

            order = await order_repo.get(order_id)

            # 检查库存并预留
            for item in order.items:
                inventory = await inventory_repo.get(item.product_id)
                inventory.reserve(item.quantity)  # 可能抛出异常

            # 更新订单状态
            order.mark_as_reserved()

            # 一次性提交所有更改
            await self.uow.commit()

            return FulfillmentResult.success()
```

## 3. 反模式警告

### ❌ 要避免的反模式

#### 反模式1: Domain层直接依赖基础设施
```python
# ❌ 错误示例
class OrderDomainService:
    def __init__(self, repository: OrderRepository):  # 违反依赖方向
        self.repository = repository

    async def process_order(self, order_id: str):
        order = await self.repository.get(order_id)  # Domain层不应直接访问数据
```

#### 反模式2: 跨聚合直接引用
```python
# ❌ 错误示例
class Order(AggregateRoot):
    def __init__(self, customer: Customer):  # 不要直接引用其他聚合
        self.customer = customer  # 应该只保存ID引用
```

#### 反模式3: 贫血模型
```python
# ❌ 错误示例
class Order:
    def __init__(self):
        self.id = None
        self.status = None  # 只有数据，没有行为

class OrderService:
    def place_order(self, order: Order):
        order.status = "PLACED"  # 业务逻辑在外部
```

#### ✅ 正确的富模型
```python
class Order(AggregateRoot):
    def place(self) -> None:
        """业务逻辑封装在聚合内部"""
        if self.status != OrderStatus.DRAFT:
            raise DomainException("Only draft orders can be placed")

        self._validate_order()
        self.status = OrderStatus.PLACED
        self.placed_at = datetime.now()
        self.add_event(OrderPlacedEvent(self.id))
```

## 4. 测试策略

### Domain Layer测试
```python
# ✅ 纯单元测试，无Mock需要
def test_order_placement():
    # Arrange
    order = Order.create_draft(customer_id="cust-1")
    items = [OrderItem(product_id="prod-1", quantity=2)]

    # Act
    order.add_items(items)
    order.place()

    # Assert
    assert order.status == OrderStatus.PLACED
    assert len(order.events) == 1
    assert isinstance(order.events[0], OrderPlacedEvent)
```

### Application Layer测试
```python
# ✅ 集成测试，Mock基础设施
async def test_place_order_use_case():
    # Arrange
    mock_uow = MockUnitOfWork()
    service = OrderApplicationService(mock_uow)
    command = PlaceOrderCommand(customer_id="cust-1", items=[...])

    # Act
    result = await service.place_order(command)

    # Assert
    assert result.success
    assert mock_uow.committed
```

## 5. 性能考虑

### 聚合边界设计
```python
# ✅ 合适的聚合大小
class Order(AggregateRoot):
    # 包含紧密相关的实体
    def __init__(self):
        self._items: list[OrderItem] = []  # 聚合内部实体
        self.shipping_info: ShippingInfo   # 值对象

    # ❌ 不要包含大量子实体
    # self._order_history: list[OrderHistoryEntry] = []  # 应该是单独的聚合
```

### 查询优化
```python
# ✅ 读写分离
class OrderQueryService:
    """专门的查询服务，可以绕过聚合边界"""

    async def get_order_summary(self, order_id: str) -> OrderSummaryDTO:
        # 直接查询优化的视图，不需要加载完整聚合
        pass
```

## 6. 部署和运维

### 事件存储监控
```python
# ✅ 事件发布监控
class EventPublishingMetrics:
    def track_event_published(self, event_type: str, success: bool):
        # 监控事件发布成功率
        pass
```

### 性能监控
```python
# ✅ 用例执行时间监控
@monitor_performance
async def place_order(self, command: PlaceOrderCommand):
    # 自动记录执行时间和成功率
    pass
```

这个指南提供了Bento Framework中正确使用DDD模式的完整参考。
