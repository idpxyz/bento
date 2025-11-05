# 领域建模指南

本文档提供 Bento DDD 框架中领域建模的详细指导，帮助你识别聚合边界、设计领域对象和建立统一语言。

## 📋 目录

- [DDD 核心概念](#ddd-核心概念)
- [识别聚合](#识别聚合)
- [设计聚合根](#设计聚合根)
- [实体 vs 值对象](#实体-vs-值对象)
- [领域事件设计](#领域事件设计)
- [领域服务](#领域服务)
- [统一语言](#统一语言)
- [实战案例](#实战案例)

---

## DDD 核心概念

### 战术设计构建块

```
┌─────────────────────────────────────────────┐
│           Bounded Context (限界上下文)       │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐  ┌──────────────┐        │
│  │  Aggregate   │  │  Aggregate   │        │
│  │  ┌────────┐  │  │  ┌────────┐  │        │
│  │  │  Root  │  │  │  │  Root  │  │        │
│  │  └───┬────┘  │  │  └───┬────┘  │        │
│  │      │       │  │      │       │        │
│  │  ┌───▼───┐   │  │  ┌───▼───┐   │        │
│  │  │Entity │   │  │  │Entity │   │        │
│  │  └───────┘   │  │  └───────┘   │        │
│  │  ┌─────────┐ │  │  ┌─────────┐ │        │
│  │  │ValueObj │ │  │  │ValueObj │ │        │
│  │  └─────────┘ │  │  └─────────┘ │        │
│  └──────────────┘  └──────────────┘        │
│         │                  │               │
│         ▼                  ▼               │
│  ┌─────────────────────────────┐          │
│  │    Domain Events            │          │
│  └─────────────────────────────┘          │
│                                             │
└─────────────────────────────────────────────┘
```

### 核心原则

1. **聚合（Aggregate）**
   - 事务一致性边界
   - 通过聚合根（Root）访问
   - 保护业务不变量

2. **实体（Entity）**
   - 有唯一标识
   - 可变的生命周期
   - 由身份而非属性区分

3. **值对象（Value Object）**
   - 无标识，由属性定义
   - 不可变
   - 可替换

4. **领域事件（Domain Event）**
   - 记录已发生的业务事实
   - 不可变
   - 驱动进程间通信

---

## 识别聚合

### 什么是聚合？

**定义**: 一组领域对象，作为数据修改的单元，保护业务不变量。

**特征**:
- ✅ 有明确的边界
- ✅ 有一个聚合根（Root Entity）
- ✅ 内部强一致性
- ✅ 外部最终一致性

### 识别方法

#### 1. 事务边界法

**问题**: 哪些对象必须在同一个事务中修改？

**示例**：订单聚合
```python
# ✅ Order 和 OrderItem 必须在同一事务中修改
class Order(AggregateRoot):
    id: EntityId
    items: List[OrderItem]  # 聚合内实体
    total: Money
    
    def add_item(self, product_id: str, quantity: int) -> None:
        """添加订单项"""
        item = OrderItem(product_id=product_id, quantity=quantity)
        self.items.append(item)
        self._recalculate_total()  # 必须同步更新
    
    def _recalculate_total(self) -> None:
        """保护不变量：total = sum(items)"""
        self.total = sum(item.price * item.quantity for item in self.items)
```

#### 2. 不变量法

**问题**: 哪些业务规则必须始终保持一致？

**示例**：库存聚合
```python
@dataclass
class Inventory(AggregateRoot):
    id: EntityId
    product_id: str
    quantity: int
    reserved: int
    
    def reserve(self, amount: int) -> Result[None, str]:
        """预留库存 - 保护不变量：available >= 0"""
        available = self.quantity - self.reserved
        
        if available < amount:
            return Err(f"Insufficient inventory: {available} < {amount}")
        
        self.reserved += amount
        self.record_event(InventoryReservedEvent(
            inventory_id=self.id.value,
            amount=amount,
        ))
        return Ok(None)
    
    def available_quantity(self) -> int:
        """可用数量 - 不变量"""
        return self.quantity - self.reserved
```

#### 3. 生命周期法

**问题**: 哪些对象一起创建、一起删除？

**示例**：
```python
# ✅ 订单和订单项一起创建
order = Order.create(customer_id="c1")
order.add_item(product_id="p1", quantity=2)  # 同一生命周期

# ❌ 订单和产品是独立的聚合
# Product 有自己的生命周期
product = Product.create(name="iPhone")
```

### 聚合大小建议

#### 小聚合原则

**推荐**: 聚合尽量小，只包含必须一起修改的对象

```python
# ✅ 好的 - 小聚合
class Order(AggregateRoot):
    id: EntityId
    customer_id: str  # 只保存引用，不是聚合的一部分
    items: List[OrderItem]  # 聚合内实体
    total: Money

# ❌ 不好的 - 大聚合
class Order(AggregateRoot):
    id: EntityId
    customer: Customer  # ❌ Customer 应该是独立聚合
    items: List[OrderItem]
    shipment: Shipment  # ❌ Shipment 应该是独立聚合
    payment: Payment    # ❌ Payment 应该是独立聚合
```

**原因**：
- 🚀 性能更好（锁定范围小）
- 🔄 并发性更高
- 🧩 更易于理解和维护

#### 何时可以大一点？

```python
# ✅ 可接受的中等聚合 - 强不变量需求
@dataclass
class Reservation(AggregateRoot):
    id: EntityId
    room_id: str
    guest: Guest  # 值对象，聚合内
    check_in: date
    check_out: date
    nights: int
    total_price: Money
    
    def __post_init__(self):
        """强不变量：nights 必须与日期一致"""
        calculated_nights = (self.check_out - self.check_in).days
        require(
            self.nights == calculated_nights,
            f"Nights mismatch: {self.nights} != {calculated_nights}"
        )
```

---

## 设计聚合根

### 聚合根的职责

1. **守门人**: 唯一的外部访问入口
2. **协调者**: 协调聚合内对象
3. **保护者**: 强制执行不变量
4. **事件发布者**: 记录和发布领域事件

### 设计模板

```python
from dataclasses import dataclass, field
from typing import List
from bento.core.ids import EntityId
from bento.core.result import Result, Ok, Err
from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_event import DomainEvent

@dataclass
class Order(AggregateRoot):
    # === 状态 ===
    id: EntityId
    customer_id: str
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    total: Money = Money.zero()
    
    # 领域事件集合（私有）
    _events: List[DomainEvent] = field(
        default_factory=list,
        init=False,
        repr=False
    )
    
    # === 工厂方法 ===
    @staticmethod
    def create(customer_id: str) -> "Order":
        """创建新订单"""
        order = Order(
            id=EntityId.new(),
            customer_id=customer_id,
        )
        order.record_event(OrderCreatedEvent(
            order_id=order.id.value,
            customer_id=customer_id,
        ))
        return order
    
    # === 业务方法 ===
    def add_item(
        self,
        product_id: str,
        quantity: int,
        unit_price: Money,
    ) -> Result[None, str]:
        """添加订单项 - 保护不变量"""
        # 1. 验证前置条件
        if self.status != OrderStatus.PENDING:
            return Err("Cannot modify non-pending order")
        
        if quantity <= 0:
            return Err("Quantity must be positive")
        
        # 2. 修改状态
        item = OrderItem(
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )
        self.items.append(item)
        self._recalculate_total()
        
        # 3. 记录事件
        self.record_event(ItemAddedToOrderEvent(
            order_id=self.id.value,
            product_id=product_id,
            quantity=quantity,
        ))
        
        return Ok(None)
    
    def confirm(self) -> Result[None, str]:
        """确认订单"""
        if self.status != OrderStatus.PENDING:
            return Err(f"Cannot confirm order in status: {self.status}")
        
        if not self.items:
            return Err("Cannot confirm empty order")
        
        self.status = OrderStatus.CONFIRMED
        self.record_event(OrderConfirmedEvent(
            order_id=self.id.value,
            total=self.total.amount,
        ))
        
        return Ok(None)
    
    # === 不变量保护 ===
    def _recalculate_total(self) -> None:
        """私有方法：维护不变量"""
        self.total = sum(
            (item.unit_price * item.quantity for item in self.items),
            Money.zero()
        )
    
    # === 查询方法 ===
    def can_be_cancelled(self) -> bool:
        """业务规则查询"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]
    
    def item_count(self) -> int:
        """总商品数"""
        return sum(item.quantity for item in self.items)
```

### 关键设计原则

#### 1. 通过聚合根修改
```python
# ✅ 正确 - 通过聚合根
order = await order_repo.get(order_id)
result = order.add_item(product_id="p1", quantity=2)
await order_repo.save(order)

# ❌ 错误 - 直接修改内部实体
order = await order_repo.get(order_id)
order.items[0].quantity = 5  # 绕过了聚合根的控制
```

#### 2. 引用其他聚合用 ID
```python
# ✅ 正确 - 通过 ID 引用
@dataclass
class Order(AggregateRoot):
    customer_id: str  # 引用 Customer 聚合
    items: List[OrderItem]

# ❌ 错误 - 直接持有其他聚合
@dataclass
class Order(AggregateRoot):
    customer: Customer  # ❌ 跨聚合边界
    items: List[OrderItem]
```

#### 3. 一个事务修改一个聚合
```python
# ✅ 正确 - 单聚合事务
async with uow:
    order = await order_repo.get(order_id)
    order.add_item(...)
    await order_repo.save(order)
    await uow.commit()

# ❌ 错误 - 跨聚合事务（应该用 Saga）
async with uow:
    order = await order_repo.get(order_id)
    order.confirm()
    
    inventory = await inventory_repo.get(product_id)
    inventory.reserve(quantity)  # ❌ 跨聚合
    
    await uow.commit()
```

---

## 实体 vs 值对象

### 决策树

```
对象有唯一标识吗？
    ├─ 是 → 是否需要追踪其变化？
    │       ├─ 是 → Entity（实体）
    │       └─ 否 → 可能是 Value Object
    │
    └─ 否 → 由属性定义吗？
            ├─ 是 → Value Object（值对象）
            └─ 否 → 重新思考模型
```

### 实体（Entity）

**特征**：
- ✅ 有唯一标识（ID）
- ✅ 可变（状态会改变）
- ✅ 由身份区分，而非属性

**示例**：
```python
from dataclasses import dataclass
from bento.core.ids import EntityId

@dataclass
class Customer(Entity):
    id: EntityId  # 唯一标识
    email: str
    name: str
    
    def change_email(self, new_email: str) -> Result[None, str]:
        """可以修改属性"""
        if not self._is_valid_email(new_email):
            return Err("Invalid email")
        self.email = new_email
        return Ok(None)

# 身份相等性
customer1 = Customer(id=EntityId("123"), email="a@example.com", name="Alice")
customer2 = Customer(id=EntityId("123"), email="b@example.com", name="Bob")

assert customer1.id == customer2.id  # ✅ 相同的实体（即使属性不同）
```

### 值对象（Value Object）

**特征**：
- ✅ 无标识
- ✅ 不可变（frozen）
- ✅ 由属性值定义
- ✅ 可替换

**示例**：
```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)  # 不可变
class Money(ValueObject):
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        """验证不变量"""
        require(self.amount >= 0, "Amount cannot be negative")
        require(len(self.currency) == 3, "Invalid currency code")
    
    def add(self, other: "Money") -> "Money":
        """操作返回新实例"""
        require(self.currency == other.currency, "Currency mismatch")
        return Money(self.amount + other.amount, self.currency)
    
    @staticmethod
    def zero(currency: str = "USD") -> "Money":
        return Money(Decimal(0), currency)

# 值相等性
money1 = Money(Decimal("100.00"), "USD")
money2 = Money(Decimal("100.00"), "USD")

assert money1 == money2  # ✅ 属性相同即相等
```

### 常见值对象

```python
# 1. 地址
@dataclass(frozen=True)
class Address(ValueObject):
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "CN"

# 2. 邮箱地址
@dataclass(frozen=True)
class EmailAddress(ValueObject):
    value: str
    
    def __post_init__(self):
        require("@" in self.value, "Invalid email format")

# 3. 日期范围
@dataclass(frozen=True)
class DateRange(ValueObject):
    start: date
    end: date
    
    def __post_init__(self):
        require(self.start <= self.end, "Start must be before end")
    
    def days(self) -> int:
        return (self.end - self.start).days
    
    def contains(self, date: date) -> bool:
        return self.start <= date <= self.end

# 4. 订单状态（枚举也是值对象）
class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
```

### 何时使用值对象？

#### ✅ 应该使用值对象

```python
# 1. 度量/数量
Money(Decimal("100"), "USD")
Weight(5.5, "kg")
Temperature(36.5, "celsius")

# 2. 复合属性
Address(street="...", city="...", ...)
FullName(first="John", last="Doe")

# 3. 业务概念
DateRange(start=..., end=...)
EmailAddress("user@example.com")

# 4. 有行为的属性
PhoneNumber("13800138000").format()  # "+86 138-0013-8000"
```

#### ❌ 不应该使用值对象

```python
# 需要追踪状态变化
class User:  # ✅ 应该是 Entity
    id: EntityId
    email: str  # 会变化
    
# 有独立生命周期
class Order:  # ✅ 应该是 Entity
    id: EntityId
    status: OrderStatus  # 状态会变化
```

---

## 领域事件设计

### 什么是领域事件？

**定义**: 在领域中已经发生的、领域专家关心的事情。

**特征**:
- ✅ 过去式命名（`OrderCreated`, `PaymentProcessed`）
- ✅ 不可变
- ✅ 包含事件发生时的所有必要信息
- ✅ 包含时间戳

### 事件设计模板

```python
from dataclasses import dataclass, field
from datetime import datetime
from bento.core.clock import now_utc

@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """订单已创建事件"""
    
    # 事件元数据
    name: str = "order.created"  # 事件名称
    occurred_at: datetime = field(default_factory=now_utc)  # 发生时间
    
    # 事件数据（业务关心的信息）
    order_id: str
    customer_id: str
    
    # 可选：聚合版本（用于事件溯源）
    aggregate_version: int = 1
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "aggregate_version": self.aggregate_version,
        }
```

### 事件命名约定

```python
# 模式：<实体><动作过去式>Event
OrderCreatedEvent         # 订单已创建
OrderConfirmedEvent       # 订单已确认
OrderCancelledEvent       # 订单已取消
PaymentProcessedEvent     # 支付已处理
InventoryReservedEvent    # 库存已预留
ShipmentDispatchedEvent   # 货物已发货

# 避免
CreateOrderEvent  # ❌ 不是过去式
OrderEvent        # ❌ 太模糊
OrderChange       # ❌ 不明确
```

### 何时发布事件？

#### 1. 状态重要变化
```python
class Order(AggregateRoot):
    def confirm(self) -> Result[None, str]:
        if self.status != OrderStatus.PENDING:
            return Err("Cannot confirm")
        
        self.status = OrderStatus.CONFIRMED
        
        # ✅ 状态变化 → 发布事件
        self.record_event(OrderConfirmedEvent(
            order_id=self.id.value,
            confirmed_at=now_utc(),
        ))
        
        return Ok(None)
```

#### 2. 领域专家关心的事情
```python
class Inventory(AggregateRoot):
    def reserve(self, amount: int) -> Result[None, str]:
        # ...库存预留逻辑...
        
        # ✅ 业务关心 → 发布事件
        self.record_event(InventoryReservedEvent(
            inventory_id=self.id.value,
            product_id=self.product_id,
            amount=amount,
        ))
```

#### 3. 跨聚合协作
```python
# 订单确认后，需要预留库存（不同聚合）
class Order(AggregateRoot):
    def confirm(self) -> Result[None, str]:
        self.status = OrderStatus.CONFIRMED
        
        # ✅ 触发其他聚合的操作
        self.record_event(OrderConfirmedEvent(
            order_id=self.id.value,
            items=[
                {"product_id": item.product_id, "quantity": item.quantity}
                for item in self.items
            ],
        ))

# 库存聚合监听事件
async def handle_order_confirmed(event: OrderConfirmedEvent):
    for item in event.items:
        inventory = await inventory_repo.get_by_product(item["product_id"])
        inventory.reserve(item["quantity"])
        await inventory_repo.save(inventory)
```

### 事件粒度

```python
# ✅ 好的 - 细粒度事件
OrderCreatedEvent
ItemAddedToOrderEvent
OrderConfirmedEvent
OrderCancelledEvent

# ❌ 不好的 - 粗粒度事件
OrderChangedEvent  # 太模糊，无法知道具体变化
```

### 事件版本管理

```python
# v1: 初始版本
@dataclass(frozen=True)
class OrderCreatedEvent:
    name: str = "order.created.v1"
    order_id: str
    customer_id: str

# v2: 添加新字段
@dataclass(frozen=True)
class OrderCreatedEventV2:
    name: str = "order.created.v2"
    order_id: str
    customer_id: str
    source: str = "web"  # 新增字段

# 事件升级器
class EventUpgrader:
    def upgrade_order_created(self, event: dict) -> dict:
        if event["name"] == "order.created.v1":
            event["name"] = "order.created.v2"
            event["source"] = "unknown"  # 默认值
        return event
```

---

## 领域服务

### 何时需要领域服务？

**场景**：
1. ❌ 业务逻辑不属于任何单一实体/值对象
2. ❌ 操作涉及多个聚合（但不是事务）
3. ❌ 需要外部信息（如当前汇率）

### 领域服务示例

```python
# 场景：订单定价逻辑涉及多个因素
class PricingService(DomainService):
    """定价领域服务"""
    
    def calculate_order_price(
        self,
        items: List[OrderItem],
        customer: Customer,
        promotion: Optional[Promotion],
    ) -> Money:
        """计算订单价格"""
        # 1. 基础价格
        subtotal = sum(item.unit_price * item.quantity for item in items)
        
        # 2. 会员折扣
        if customer.is_vip:
            subtotal = subtotal * Decimal("0.95")
        
        # 3. 促销折扣
        if promotion and promotion.is_active():
            subtotal = promotion.apply_discount(subtotal)
        
        # 4. 运费计算
        shipping = self._calculate_shipping(items, customer.address)
        
        return subtotal + shipping
    
    def _calculate_shipping(
        self,
        items: List[OrderItem],
        address: Address,
    ) -> Money:
        """运费计算逻辑"""
        # 复杂的运费计算...
        pass

# 使用
pricing_service = PricingService()
price = pricing_service.calculate_order_price(
    items=order.items,
    customer=customer,
    promotion=promotion,
)
```

### 领域服务 vs 应用服务

```python
# ✅ 领域服务 - 业务逻辑
class PricingService(DomainService):
    def calculate_price(self, items: List[OrderItem]) -> Money:
        """业务规则：定价算法"""
        return sum(item.price * item.quantity for item in items)

# ✅ 应用服务 - 编排
class CreateOrderUseCase:
    def __init__(
        self,
        order_repo: OrderRepository,
        pricing_service: PricingService,
        uow: UnitOfWork,
    ):
        self.order_repo = order_repo
        self.pricing_service = pricing_service
        self.uow = uow
    
    async def __call__(self, inp: CreateOrderInput) -> Result[Order, str]:
        """编排：调用领域服务 + 持久化"""
        # 1. 创建订单
        order = Order.create(inp.customer_id)
        
        # 2. 调用领域服务
        price = self.pricing_service.calculate_price(inp.items)
        order.set_price(price)
        
        # 3. 持久化
        async with self.uow:
            await self.order_repo.save(order)
            await self.uow.commit()
        
        return Ok(order)
```

---

## 统一语言

### 什么是统一语言（Ubiquitous Language）？

**定义**: 团队（开发者 + 领域专家）共享的、在代码和对话中都使用的语言。

### 建立统一语言

#### 1. 从领域专家的术语开始

```python
# ❌ 程序员术语
class OrderData:
    def update_status(self, new_status: int): ...

# ✅ 业务术语
class Order:
    def confirm(self) -> Result[None, str]: ...
    def cancel(self, reason: str) -> Result[None, str]: ...
    def ship(self) -> Result[None, str]: ...
```

#### 2. 避免技术术语污染

```python
# ❌ 技术术语
order.save_to_database()
order.serialize_to_json()

# ✅ 业务术语
order_repo.save(order)
order_dto = OrderDTO.from_entity(order)
```

#### 3. 建立术语表

创建 `docs/glossary.md`:

```markdown
# 业务术语表

## 订单域

- **订单 (Order)**: 客户购买商品的请求
- **订单项 (Order Item)**: 订单中的单个商品及数量
- **确认订单 (Confirm Order)**: 客户提交订单，等待处理
- **取消订单 (Cancel Order)**: 客户或系统撤销订单
- **发货 (Ship)**: 将商品发送给客户

## 库存域

- **库存 (Inventory)**: 可销售商品的数量
- **预留 (Reserve)**: 为订单暂时锁定库存
- **释放 (Release)**: 取消订单后归还库存
```

#### 4. 代码中使用业务术语

```python
# ✅ 方法名使用业务语言
class Order:
    def confirm(self): ...      # 而非 set_status_confirmed()
    def cancel(self): ...        # 而非 set_status_cancelled()
    def add_item(self): ...      # 而非 append_to_items_list()

# ✅ 变量名使用业务术语
available_inventory = inventory.quantity - inventory.reserved
# 而非 val1 = val2 - val3

# ✅ 事件名使用业务语言
OrderConfirmedEvent    # 而非 OrderStatusChangedEvent
InventoryDepletedEvent # 而非 InventoryLowEvent
```

---

## 实战案例

### 案例：电商订单系统

#### 1. 识别聚合

```python
# 聚合 1: Order（订单）
# 边界：订单 + 订单项
# 不变量：total = sum(items)
class Order(AggregateRoot):
    items: List[OrderItem]  # 聚合内实体
    total: Money

# 聚合 2: Inventory（库存）
# 边界：单个产品的库存
# 不变量：available = quantity - reserved >= 0
class Inventory(AggregateRoot):
    product_id: str
    quantity: int
    reserved: int

# 聚合 3: Payment（支付）
# 边界：支付记录
# 不变量：amount > 0, status 状态机
class Payment(AggregateRoot):
    order_id: str  # 引用 Order 聚合
    amount: Money
    status: PaymentStatus
```

#### 2. 设计交互流程

```python
# 步骤 1: 创建订单
async def create_order(inp: CreateOrderInput) -> Result[Order, str]:
    async with uow:
        order = Order.create(inp.customer_id)
        for item in inp.items:
            order.add_item(item.product_id, item.quantity)
        
        await order_repo.save(order)
        await uow.commit()
        # 发布：OrderCreatedEvent
    
    return Ok(order)

# 步骤 2: 确认订单（触发库存预留）
async def confirm_order(order_id: str) -> Result[None, str]:
    async with uow:
        order = await order_repo.get(order_id)
        result = order.confirm()
        if result.is_err:
            return result
        
        await order_repo.save(order)
        await uow.commit()
        # 发布：OrderConfirmedEvent
    
    return Ok(None)

# 步骤 3: 处理订单确认事件（预留库存）
@event_handler("order.confirmed")
async def handle_order_confirmed(event: OrderConfirmedEvent):
    """监听订单确认，预留库存"""
    for item in event.items:
        async with uow:
            inventory = await inventory_repo.get_by_product(item.product_id)
            result = inventory.reserve(item.quantity)
            
            if result.is_err:
                # 发布：InventoryReservationFailedEvent
                # 触发补偿（取消订单）
                pass
            
            await inventory_repo.save(inventory)
            await uow.commit()
```

#### 3. 完整聚合实现

```python
@dataclass
class Order(AggregateRoot):
    id: EntityId
    customer_id: str
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    total: Money = Money.zero()
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)
    
    @staticmethod
    def create(customer_id: str) -> "Order":
        order = Order(id=EntityId.new(), customer_id=customer_id)
        order.record_event(OrderCreatedEvent(
            order_id=order.id.value,
            customer_id=customer_id,
        ))
        return order
    
    def add_item(
        self,
        product_id: str,
        quantity: int,
        unit_price: Money,
    ) -> Result[None, str]:
        if self.status != OrderStatus.PENDING:
            return Err("Cannot modify confirmed order")
        
        item = OrderItem(
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )
        self.items.append(item)
        self._recalculate_total()
        
        self.record_event(ItemAddedToOrderEvent(
            order_id=self.id.value,
            product_id=product_id,
            quantity=quantity,
        ))
        
        return Ok(None)
    
    def confirm(self) -> Result[None, str]:
        if self.status != OrderStatus.PENDING:
            return Err(f"Cannot confirm order in {self.status} status")
        
        if not self.items:
            return Err("Cannot confirm empty order")
        
        self.status = OrderStatus.CONFIRMED
        self.record_event(OrderConfirmedEvent(
            order_id=self.id.value,
            items=[
                {"product_id": i.product_id, "quantity": i.quantity}
                for i in self.items
            ],
            total=self.total.amount,
        ))
        
        return Ok(None)
    
    def _recalculate_total(self) -> None:
        self.total = sum(
            (item.unit_price * item.quantity for item in self.items),
            Money.zero()
        )
```

---

## 快速检查清单

### 聚合设计
- [ ] 聚合边界清晰（事务边界）
- [ ] 聚合尽量小
- [ ] 通过 ID 引用其他聚合
- [ ] 一个事务修改一个聚合
- [ ] 有明确的聚合根
- [ ] 保护业务不变量

### 实体/值对象
- [ ] 实体有唯一标识
- [ ] 值对象不可变（frozen=True）
- [ ] 值对象验证不变量
- [ ] 正确选择实体 vs 值对象

### 领域事件
- [ ] 使用过去式命名
- [ ] 事件不可变
- [ ] 包含时间戳
- [ ] 包含必要的业务信息
- [ ] 在状态变化时发布

### 统一语言
- [ ] 使用业务术语
- [ ] 避免技术术语
- [ ] 代码反映领域模型
- [ ] 维护术语表

---

## 参考资料

- [Domain-Driven Design](https://www.domainlanguage.com/ddd/) - Eric Evans
- [Implementing Domain-Driven Design](https://vaughnvernon.com/) - Vaughn Vernon
- [Effective Aggregate Design](https://vaughnvernon.com/effective-aggregate-design-part-i/) - Vaughn Vernon
- [Domain Events](https://martinfowler.com/eaaDev/DomainEvent.html) - Martin Fowler

