# 事件设计规范

本文档提供事件驱动架构中的事件设计、版本管理和 Outbox 模式的详细指导。

## 📋 目录

- [事件基础](#事件基础)
- [事件命名规范](#事件命名规范)
- [事件结构设计](#事件结构设计)
- [事件版本管理](#事件版本管理)
- [Outbox 模式](#outbox-模式)
- [事件处理器](#事件处理器)
- [事件溯源](#事件溯源)
- [最佳实践](#最佳实践)

---

## 事件基础

### 什么是领域事件？

**定义**: 领域中已经发生的、领域专家关心的事情的记录。

**特征**:
- ✅ **不可变**: 事件一旦发生，不能修改
- ✅ **过去式**: 表示已经发生的事实
- ✅ **自包含**: 包含所有必要的上下文信息
- ✅ **有序**: 有明确的时间戳

### 事件类型

#### 1. 领域事件（Domain Event）
```python
@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """订单已创建 - 领域事件"""
    order_id: str
    customer_id: str
    occurred_at: datetime = field(default_factory=now_utc)
```

**用途**: 
- 聚合内状态变化的记录
- 同一限界上下文内的通信
- 触发业务流程

#### 2. 集成事件（Integration Event）
```python
@dataclass(frozen=True)
class OrderConfirmedIntegrationEvent:
    """订单已确认 - 集成事件"""
    event_id: str
    event_type: str = "ecommerce.order.confirmed.v1"
    timestamp: datetime
    
    # 业务数据
    order_id: str
    customer_id: str
    total_amount: Decimal
    items: List[dict]
    
    # 元数据
    source_system: str = "order-service"
    correlation_id: Optional[str] = None
```

**用途**:
- 跨限界上下文通信
- 跨服务通信
- 外部系统集成

### 事件 vs 命令

| 维度 | 事件 (Event) | 命令 (Command) |
|-----|-------------|---------------|
| **时态** | 过去式 | 祈使句 |
| **示例** | `OrderCreated` | `CreateOrder` |
| **意图** | "发生了什么" | "做什么" |
| **接收者** | 0到多个 | 通常一个 |
| **失败** | 不能拒绝 | 可以拒绝 |

```python
# 命令 - 请求做某事
@dataclass
class CreateOrderCommand:
    customer_id: str
    items: List[dict]

# 事件 - 已经发生的事实
@dataclass(frozen=True)
class OrderCreatedEvent:
    order_id: str
    customer_id: str
    occurred_at: datetime
```

---

## 事件命名规范

### 命名模式

```
<聚合名><动作过去式>Event
```

#### ✅ 好的命名

```python
# 领域事件
OrderCreatedEvent           # 订单已创建
OrderConfirmedEvent         # 订单已确认
OrderCancelledEvent         # 订单已取消
OrderShippedEvent           # 订单已发货
PaymentProcessedEvent       # 支付已处理
InventoryReservedEvent      # 库存已预留
CustomerRegisteredEvent     # 客户已注册

# 集成事件（带版本）
order.created.v1            # 订单已创建 v1
payment.processed.v2        # 支付已处理 v2
inventory.depleted.v1       # 库存已耗尽 v1
```

#### ❌ 不好的命名

```python
CreateOrderEvent      # ❌ 不是过去式
OrderEvent            # ❌ 太模糊
OrderUpdate           # ❌ 不明确变化
OrderChanged          # ❌ 不具体
Order_Created         # ❌ 使用下划线
orderCreated          # ❌ 首字母小写
```

### 命名约定

#### 1. 使用过去式

```python
# ✅ 正确
OrderConfirmedEvent
PaymentCompletedEvent
ItemAddedToCartEvent

# ❌ 错误
OrderConfirmEvent
PaymentCompleteEvent
AddItemToCartEvent
```

#### 2. 明确具体

```python
# ✅ 具体的事件
OrderConfirmedEvent
OrderCancelledEvent
OrderShippedEvent

# ❌ 模糊的事件
OrderStatusChangedEvent  # 什么状态？需要查看payload
OrderUpdatedEvent        # 更新了什么？
```

#### 3. 业务语言

```python
# ✅ 业务术语
CustomerRegisteredEvent
OrderPlacedEvent
PaymentRefundedEvent

# ❌ 技术术语
CustomerInsertedEvent
OrderSavedEvent
PaymentTransactionReversedEvent
```

---

## 事件结构设计

### 基础事件模板

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from bento.core.clock import now_utc

@dataclass(frozen=True)
class DomainEvent:
    """领域事件基类"""
    
    # === 事件元数据 ===
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # 事件类型（如 "order.created"）
    occurred_at: datetime = field(default_factory=now_utc)
    
    # === 聚合信息 ===
    aggregate_id: str  # 聚合ID
    aggregate_type: str  # 聚合类型（如 "Order"）
    aggregate_version: int = 1  # 聚合版本（用于事件溯源）
    
    # === 关联信息 ===
    correlation_id: Optional[str] = None  # 关联ID（追踪整个流程）
    causation_id: Optional[str] = None    # 因果ID（触发此事件的事件ID）
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return asdict(self)
```

### 具体事件示例

```python
@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """订单已创建事件"""
    
    # 元数据（继承自 DomainEvent）
    event_type: str = "order.created.v1"
    aggregate_type: str = "Order"
    
    # 业务数据（事件特有）
    order_id: str
    customer_id: str
    order_number: str
    total_amount: Decimal
    currency: str = "USD"
    
    # 可选：快照数据
    items: Optional[List[dict]] = None
    
    def __post_init__(self):
        """验证不变量"""
        object.__setattr__(self, "aggregate_id", self.order_id)
```

### 事件数据原则

#### 1. 自包含原则

事件应包含足够的信息，让消费者无需查询其他数据：

```python
# ✅ 好的 - 自包含
@dataclass(frozen=True)
class OrderConfirmedEvent:
    order_id: str
    customer_id: str
    total_amount: Decimal
    items: List[dict]  # 包含订单项详情
    shipping_address: dict  # 包含地址

# ❌ 不好的 - 需要额外查询
@dataclass(frozen=True)
class OrderConfirmedEvent:
    order_id: str  # 消费者需要查询订单详情
```

**权衡**: 自包含 vs 事件大小

```python
# 策略1: 完整快照（适合小聚合）
@dataclass(frozen=True)
class OrderCreatedEvent:
    order: dict  # 完整订单快照

# 策略2: 关键信息 + ID引用（适合大聚合）
@dataclass(frozen=True)
class OrderCreatedEvent:
    order_id: str
    customer_id: str
    total_amount: Decimal
    item_ids: List[str]  # 只有ID，消费者按需查询
```

#### 2. 不可变原则

```python
@dataclass(frozen=True)  # ✅ 强制不可变
class OrderCreatedEvent:
    order_id: str
    occurred_at: datetime

# 尝试修改会报错
event = OrderCreatedEvent(order_id="123", occurred_at=now_utc())
event.order_id = "456"  # ❌ FrozenInstanceError
```

#### 3. 最小必要信息

```python
# ✅ 好的 - 只包含必要信息
@dataclass(frozen=True)
class OrderCancelledEvent:
    order_id: str
    reason: str
    cancelled_by: str  # 谁取消的
    refund_amount: Decimal

# ❌ 不好的 - 包含太多不必要信息
@dataclass(frozen=True)
class OrderCancelledEvent:
    order_id: str
    reason: str
    entire_order_snapshot: dict  # ❌ 通常不需要
    customer_full_profile: dict  # ❌ 不相关
    system_logs: List[str]       # ❌ 技术细节
```

---

## 事件版本管理

### 为什么需要版本？

**场景**: 业务需求变化，事件结构需要演进

```python
# v1: 初始版本
@dataclass(frozen=True)
class OrderCreatedEvent:
    event_type: str = "order.created.v1"
    order_id: str
    customer_id: str
    total_amount: Decimal

# v2: 添加新字段
@dataclass(frozen=True)
class OrderCreatedEventV2:
    event_type: str = "order.created.v2"
    order_id: str
    customer_id: str
    total_amount: Decimal
    currency: str = "USD"  # 新增
    source: str = "web"    # 新增
```

### 版本策略

#### 策略1: 向后兼容（推荐）

```python
@dataclass(frozen=True)
class OrderCreatedEvent:
    """向后兼容的事件演进"""
    event_type: str = "order.created.v2"
    
    # v1 字段
    order_id: str
    customer_id: str
    total_amount: Decimal
    
    # v2 新增字段（带默认值）
    currency: str = "USD"
    source: str = "unknown"
    
    @classmethod
    def from_v1(cls, v1_event: dict) -> "OrderCreatedEvent":
        """从 v1 升级到 v2"""
        return cls(
            order_id=v1_event["order_id"],
            customer_id=v1_event["customer_id"],
            total_amount=v1_event["total_amount"],
            currency="USD",  # 默认值
            source="unknown",  # 默认值
        )
```

#### 策略2: 独立版本类

```python
# v1 事件
@dataclass(frozen=True)
class OrderCreatedEventV1:
    event_type: str = "order.created.v1"
    order_id: str
    customer_id: str

# v2 事件（完全独立）
@dataclass(frozen=True)
class OrderCreatedEventV2:
    event_type: str = "order.created.v2"
    order_id: str
    customer_id: str
    source: str

# 事件升级器
class EventUpgrader:
    def upgrade(self, event: dict) -> dict:
        if event["event_type"] == "order.created.v1":
            return self._upgrade_v1_to_v2(event)
        return event
    
    def _upgrade_v1_to_v2(self, v1: dict) -> dict:
        return {
            "event_type": "order.created.v2",
            "order_id": v1["order_id"],
            "customer_id": v1["customer_id"],
            "source": "legacy",  # 默认值
        }
```

### 版本演进规则

#### ✅ 安全的变更

```python
# 1. 添加新字段（带默认值）
@dataclass(frozen=True)
class OrderCreatedEventV2:
    order_id: str
    customer_id: str
    source: str = "web"  # ✅ 新字段有默认值

# 2. 废弃字段（保留但不使用）
@dataclass(frozen=True)
class OrderCreatedEventV3:
    order_id: str
    customer_id: str
    # old_field: str  # ✅ 注释掉但保留文档说明

# 3. 扩展枚举值
class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"  # ✅ 新增状态
```

#### ❌ 破坏性变更

```python
# 1. 删除字段
# v1
order_id: str
customer_id: str  # ❌ v2 删除了这个字段

# 2. 重命名字段
# v1: customer_id
# v2: customerId  # ❌ 破坏性变更

# 3. 改变字段类型
# v1: total_amount: int
# v2: total_amount: Decimal  # ❌ 类型变化

# 4. 改变语义
# v1: amount = 订单总额
# v2: amount = 订单净额（不含税）  # ❌ 语义变化
```

**处理破坏性变更**：
- 发布新的事件类型（v3）
- 同时支持 v2 和 v3
- 逐步迁移消费者
- 最终废弃 v2

---

## Outbox 模式

### 问题：双写问题

```python
# ❌ 问题场景：可能不一致
async def create_order(inp: CreateOrderInput):
    # 1. 写数据库
    await db.execute("INSERT INTO orders ...")  # ✅ 成功
    
    # 2. 发送事件
    await event_bus.publish(OrderCreatedEvent(...))  # ❌ 失败！
    
    # 结果：数据库有订单，但事件未发送 → 不一致！
```

### 解决方案：Outbox 模式

```
┌─────────────────────────────────────┐
│  1. 业务事务                        │
│  ┌──────────────────────────────┐  │
│  │ BEGIN TRANSACTION            │  │
│  │   INSERT INTO orders ...     │  │
│  │   INSERT INTO outbox ...     │  │ ← 同一事务
│  │ COMMIT                       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  2. 异步发布（独立进程）             │
│  ┌──────────────────────────────┐  │
│  │ SELECT * FROM outbox         │  │
│  │   WHERE published = false    │  │
│  │ Publish to Pulsar            │  │
│  │ UPDATE outbox                │  │
│  │   SET published = true       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Outbox 表结构

```sql
CREATE TABLE outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 事件元数据
    event_type VARCHAR(255) NOT NULL,
    event_id UUID NOT NULL UNIQUE,
    
    -- 聚合信息
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    
    -- 事件数据
    payload JSONB NOT NULL,
    
    -- 发布状态
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    
    -- 追踪
    created_at TIMESTAMP DEFAULT NOW(),
    attempts INT DEFAULT 0,
    
    -- 索引
    INDEX idx_outbox_published (published, created_at),
    INDEX idx_outbox_aggregate (aggregate_type, aggregate_id)
);
```

### Outbox 实现

#### 1. 写入 Outbox

```python
class SQLAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession, outbox_repo: OutboxRepository):
        self.session = session
        self.outbox_repo = outbox_repo
        self._tracked_aggregates: List[AggregateRoot] = []
    
    def track(self, aggregate: AggregateRoot) -> None:
        """追踪聚合（用于收集事件）"""
        self._tracked_aggregates.append(aggregate)
    
    async def commit(self) -> None:
        """提交事务 + 写入 Outbox"""
        # 1. 收集所有领域事件
        events = []
        for aggregate in self._tracked_aggregates:
            events.extend(aggregate.collect_events())
        
        # 2. 写入 Outbox（同一事务）
        for event in events:
            outbox_message = OutboxMessage(
                event_id=event.event_id,
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                aggregate_type=event.aggregate_type,
                payload=event.to_dict(),
                created_at=now_utc(),
            )
            await self.outbox_repo.add(outbox_message)
        
        # 3. 提交事务（原子性保证）
        await self.session.commit()
        
        self._tracked_aggregates.clear()
```

#### 2. Outbox 轮询发布器

```python
class OutboxPublisher:
    """Outbox 发布器（独立进程）"""
    
    def __init__(
        self,
        outbox_repo: OutboxRepository,
        event_bus: EventBus,
        batch_size: int = 100,
        poll_interval: int = 5,
    ):
        self.outbox_repo = outbox_repo
        self.event_bus = event_bus
        self.batch_size = batch_size
        self.poll_interval = poll_interval
    
    async def run(self) -> None:
        """持续轮询并发布事件"""
        while True:
            try:
                await self._publish_batch()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Outbox publisher error: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _publish_batch(self) -> None:
        """发布一批事件"""
        # 1. 获取未发布的事件
        messages = await self.outbox_repo.pull_unpublished(
            limit=self.batch_size
        )
        
        for message in messages:
            try:
                # 2. 发布到事件总线
                await self.event_bus.publish(
                    topic=message.event_type,
                    payload=message.payload,
                )
                
                # 3. 标记为已发布
                await self.outbox_repo.mark_published(message.id)
                
                logger.info(
                    f"Published event {message.event_type} "
                    f"for aggregate {message.aggregate_id}"
                )
                
            except Exception as e:
                # 4. 记录失败，稍后重试
                await self.outbox_repo.increment_attempts(message.id)
                logger.error(f"Failed to publish {message.id}: {e}")
```

#### 3. Repository 集成

```python
class SQLAlchemyOrderRepository:
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
    
    async def save(self, order: Order) -> None:
        """保存订单 + 追踪事件"""
        # 1. 保存实体
        order_model = self._to_model(order)
        self.session.add(order_model)
        
        # 2. 追踪聚合（UoW 会收集事件）
        self.uow.track(order)
```

### Outbox 最佳实践

#### 1. 幂等性处理

```python
@dataclass(frozen=True)
class OrderCreatedEvent:
    event_id: str  # ✅ 唯一ID，用于去重
    order_id: str
    customer_id: str

# 消费者端去重
class OrderEventHandler:
    def __init__(self, processed_events_cache: Cache):
        self.cache = processed_events_cache
    
    async def handle_order_created(self, event: OrderCreatedEvent):
        # 检查是否已处理
        if await self.cache.exists(event.event_id):
            logger.info(f"Event {event.event_id} already processed")
            return
        
        # 处理事件
        await self._process_event(event)
        
        # 标记为已处理
        await self.cache.set(event.event_id, "processed", ttl=86400)
```

#### 2. 事件顺序保证

```python
# 使用分区键保证同一聚合的事件有序
class OutboxPublisher:
    async def _publish_batch(self) -> None:
        messages = await self.outbox_repo.pull_unpublished(
            limit=self.batch_size,
            order_by="created_at",  # ✅ 按时间排序
        )
        
        for message in messages:
            # 使用 aggregate_id 作为分区键
            await self.event_bus.publish(
                topic=message.event_type,
                payload=message.payload,
                partition_key=message.aggregate_id,  # ✅ 同一聚合到同一分区
            )
```

#### 3. 重试策略

```python
class OutboxPublisher:
    MAX_ATTEMPTS = 3
    
    async def _publish_batch(self) -> None:
        messages = await self.outbox_repo.pull_unpublished(
            limit=self.batch_size,
            max_attempts=self.MAX_ATTEMPTS,  # 只获取未超过重试次数的
        )
        
        for message in messages:
            try:
                await self.event_bus.publish(...)
                await self.outbox_repo.mark_published(message.id)
            except Exception as e:
                # 增加重试次数
                await self.outbox_repo.increment_attempts(message.id)
                
                # 超过最大重试 → 移到死信队列
                if message.attempts >= self.MAX_ATTEMPTS:
                    await self.dead_letter_queue.add(message)
                    await self.outbox_repo.mark_failed(message.id)
```

---

## 事件处理器

### 事件处理器注册

```python
from typing import Callable, Awaitable, Dict, List

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[dict], Awaitable[None]],
    ) -> None:
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def publish(self, event_type: str, payload: dict) -> None:
        """发布事件"""
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(payload)
            except Exception as e:
                logger.error(f"Handler error for {event_type}: {e}")

# 使用装饰器注册
event_bus = EventBus()

def event_handler(event_type: str):
    def decorator(func):
        event_bus.subscribe(event_type, func)
        return func
    return decorator

@event_handler("order.created.v1")
async def handle_order_created(event: dict):
    order_id = event["order_id"]
    logger.info(f"Order created: {order_id}")
    # 处理逻辑...
```

### 事件处理最佳实践

#### 1. 处理器幂等性

```python
@event_handler("order.confirmed.v1")
async def reserve_inventory(event: dict):
    """幂等的库存预留"""
    event_id = event["event_id"]
    order_id = event["order_id"]
    
    # 检查是否已处理
    if await idempotency_store.exists(f"reserve:{event_id}"):
        logger.info(f"Event {event_id} already processed")
        return
    
    # 处理业务逻辑
    for item in event["items"]:
        inventory = await inventory_repo.get_by_product(item["product_id"])
        await inventory.reserve(item["quantity"])
    
    # 标记为已处理
    await idempotency_store.set(f"reserve:{event_id}", "done", ttl=86400)
```

#### 2. 错误处理与重试

```python
@event_handler("payment.processed.v1")
async def handle_payment_processed(event: dict):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 业务逻辑
            await process_payment(event)
            return  # 成功，退出
            
        except RetryableError as e:
            retry_count += 1
            logger.warning(f"Retry {retry_count}/{max_retries}: {e}")
            await asyncio.sleep(2 ** retry_count)  # 指数退避
            
        except FatalError as e:
            logger.error(f"Fatal error, sending to DLQ: {e}")
            await dead_letter_queue.add(event)
            return
    
    # 超过重试次数
    await dead_letter_queue.add(event)
```

#### 3. 事件转换

```python
@event_handler("order.confirmed.v1")
async def handle_order_confirmed(event: dict):
    """将领域事件转换为集成事件"""
    
    # 1. 处理领域逻辑
    order = await order_repo.get(event["order_id"])
    # ...
    
    # 2. 发布集成事件（给外部系统）
    integration_event = {
        "event_type": "ecommerce.order.confirmed.v1",
        "event_id": str(uuid.uuid4()),
        "timestamp": now_utc().isoformat(),
        "data": {
            "order_id": event["order_id"],
            "customer_email": order.customer_email,
            "total_amount": float(order.total.amount),
        },
        "metadata": {
            "source": "order-service",
            "version": "1.0.0",
        }
    }
    
    await external_event_bus.publish("order-events", integration_event)
```

---

## 事件溯源

### 基本概念

**定义**: 将聚合的所有状态变化存储为事件序列，通过重放事件重建状态。

```python
# 传统方式：存储当前状态
Order(id="123", status="confirmed", total=1000)

# 事件溯源：存储事件序列
[
    OrderCreatedEvent(order_id="123", ...),
    ItemAddedEvent(order_id="123", product_id="p1", quantity=2),
    OrderConfirmedEvent(order_id="123"),
]
```

### 事件溯源聚合

```python
from typing import List

class EventSourcedOrder:
    """事件溯源的订单聚合"""
    
    def __init__(self):
        self.id: Optional[EntityId] = None
        self.customer_id: Optional[str] = None
        self.items: List[OrderItem] = []
        self.status = OrderStatus.PENDING
        self.version = 0
        self._uncommitted_events: List[DomainEvent] = []
    
    @staticmethod
    def create(customer_id: str) -> "EventSourcedOrder":
        """创建新订单"""
        order = EventSourcedOrder()
        event = OrderCreatedEvent(
            order_id=str(uuid.uuid4()),
            customer_id=customer_id,
        )
        order._apply_event(event)
        order._uncommitted_events.append(event)
        return order
    
    def add_item(self, product_id: str, quantity: int) -> Result[None, str]:
        """添加订单项"""
        if self.status != OrderStatus.PENDING:
            return Err("Cannot modify confirmed order")
        
        event = ItemAddedEvent(
            order_id=self.id.value,
            product_id=product_id,
            quantity=quantity,
        )
        self._apply_event(event)
        self._uncommitted_events.append(event)
        return Ok(None)
    
    def _apply_event(self, event: DomainEvent) -> None:
        """应用事件改变状态"""
        if isinstance(event, OrderCreatedEvent):
            self.id = EntityId(event.order_id)
            self.customer_id = event.customer_id
            self.status = OrderStatus.PENDING
        
        elif isinstance(event, ItemAddedEvent):
            self.items.append(OrderItem(
                product_id=event.product_id,
                quantity=event.quantity,
            ))
        
        elif isinstance(event, OrderConfirmedEvent):
            self.status = OrderStatus.CONFIRMED
        
        self.version += 1
    
    @classmethod
    def from_events(cls, events: List[DomainEvent]) -> "EventSourcedOrder":
        """从事件序列重建聚合"""
        order = cls()
        for event in events:
            order._apply_event(event)
        return order
    
    def uncommitted_events(self) -> List[DomainEvent]:
        """获取未提交的事件"""
        events = self._uncommitted_events.copy()
        self._uncommitted_events.clear()
        return events
```

### 事件存储

```python
class EventStore:
    """事件存储"""
    
    async def save_events(
        self,
        aggregate_id: str,
        events: List[DomainEvent],
        expected_version: int,
    ) -> None:
        """保存事件（乐观锁）"""
        async with self.session.begin():
            # 检查版本（防止并发冲突）
            current_version = await self._get_version(aggregate_id)
            if current_version != expected_version:
                raise ConcurrencyError(
                    f"Version conflict: expected {expected_version}, "
                    f"got {current_version}"
                )
            
            # 保存事件
            for i, event in enumerate(events):
                event_model = EventModel(
                    event_id=event.event_id,
                    aggregate_id=aggregate_id,
                    event_type=event.event_type,
                    version=expected_version + i + 1,
                    payload=event.to_dict(),
                    created_at=event.occurred_at,
                )
                self.session.add(event_model)
    
    async def load_events(
        self,
        aggregate_id: str,
        from_version: int = 0,
    ) -> List[DomainEvent]:
        """加载事件序列"""
        result = await self.session.execute(
            select(EventModel)
            .where(EventModel.aggregate_id == aggregate_id)
            .where(EventModel.version > from_version)
            .order_by(EventModel.version)
        )
        
        event_models = result.scalars().all()
        return [self._deserialize(model) for model in event_models]
```

---

## 最佳实践

### 1. 事件设计原则

```python
# ✅ 不可变
@dataclass(frozen=True)
class OrderCreatedEvent: ...

# ✅ 自包含
@dataclass(frozen=True)
class OrderConfirmedEvent:
    order_id: str
    customer_id: str
    total_amount: Decimal
    items: List[dict]  # 包含足够信息

# ✅ 过去式命名
OrderCreatedEvent      # 而非 CreateOrderEvent
PaymentProcessedEvent  # 而非 ProcessPaymentEvent

# ✅ 明确具体
OrderConfirmedEvent    # 而非 OrderStatusChangedEvent
InventoryDepletedEvent # 而非 InventoryChangedEvent
```

### 2. 性能优化

```python
# 批量发布事件
class OutboxPublisher:
    async def _publish_batch(self) -> None:
        messages = await self.outbox_repo.pull_unpublished(
            limit=100  # ✅ 批量处理
        )
        
        # 批量发布
        await self.event_bus.publish_batch(messages)

# 事件快照（事件溯源优化）
class EventStore:
    async def save_snapshot(
        self,
        aggregate_id: str,
        snapshot: dict,
        version: int,
    ) -> None:
        """保存快照"""
        # 每100个事件保存一次快照
        if version % 100 == 0:
            await self._save_snapshot(aggregate_id, snapshot, version)
    
    async def load_aggregate(self, aggregate_id: str) -> Order:
        # 1. 加载最新快照
        snapshot, version = await self._load_latest_snapshot(aggregate_id)
        
        # 2. 只重放快照之后的事件
        events = await self.load_events(aggregate_id, from_version=version)
        
        # 3. 重建聚合
        order = Order.from_snapshot(snapshot)
        for event in events:
            order._apply_event(event)
        
        return order
```

### 3. 监控与追踪

```python
@dataclass(frozen=True)
class OrderCreatedEvent:
    event_id: str
    order_id: str
    
    # ✅ 关联ID（追踪整个流程）
    correlation_id: str  # 用户请求ID
    causation_id: Optional[str]  # 触发此事件的事件ID
    
    # ✅ 元数据
    source: str = "order-service"
    user_id: Optional[str] = None

# 日志追踪
logger.info(
    "Event published",
    extra={
        "event_type": event.event_type,
        "event_id": event.event_id,
        "correlation_id": event.correlation_id,
        "aggregate_id": event.aggregate_id,
    }
)
```

### 4. 测试

```python
# 测试事件发布
async def test_order_creation_publishes_event():
    # Arrange
    event_store = InMemoryEventStore()
    order = Order.create("customer-1")
    
    # Act
    order.add_item("product-1", 2)
    events = order.uncommitted_events()
    
    # Assert
    assert len(events) == 2
    assert isinstance(events[0], OrderCreatedEvent)
    assert isinstance(events[1], ItemAddedEvent)

# 测试事件处理
async def test_inventory_reservation_on_order_confirmed():
    # Arrange
    event = OrderConfirmedEvent(
        order_id="123",
        items=[{"product_id": "p1", "quantity": 2}],
    )
    
    # Act
    await handle_order_confirmed(event)
    
    # Assert
    inventory = await inventory_repo.get_by_product("p1")
    assert inventory.reserved == 2
```

---

## 快速检查清单

### 事件设计
- [ ] 使用过去式命名
- [ ] 事件不可变（frozen=True）
- [ ] 包含事件ID和时间戳
- [ ] 自包含（足够的上下文信息）
- [ ] 明确具体（不模糊）

### Outbox 模式
- [ ] 事件写入与业务操作在同一事务
- [ ] 有独立的发布进程
- [ ] 处理幂等性
- [ ] 保证事件顺序
- [ ] 实现重试策略

### 事件处理
- [ ] 处理器幂等
- [ ] 错误处理与重试
- [ ] 死信队列
- [ ] 监控与日志

### 版本管理
- [ ] 事件有版本号
- [ ] 向后兼容
- [ ] 有升级策略
- [ ] 文档化变更

---

## 参考资料

- [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html) - Martin Fowler
- [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- [Domain Events](https://www.domainlanguage.com/ddd/patterns/DDD_Domain_Events_Pattern.pdf) - Eric Evans
- [Versioning in an Event Sourced System](https://leanpub.com/esversioning) - Greg Young

