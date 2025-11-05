# Outbox Pattern 使用指南

## 🎯 什么是 Transactional Outbox？

**Transactional Outbox 模式** 解决分布式系统中的关键问题：**如何确保数据库事务和消息发布的原子性**。

### 问题场景

```python
# ❌ 常见错误：不保证原子性
async def create_order(order: Order):
    # 1. 保存订单到数据库
    await db.save(order)
    await db.commit()
    
    # 2. 发布事件到消息队列
    # ⚠️ 如果这里失败，数据库已提交但事件丢失！
    await message_bus.publish(OrderCreated(order.id))
```

### Outbox 解决方案

```python
# ✅ 使用 Outbox：保证原子性
async def create_order(order: Order, uow: UnitOfWork):
    # 1. 在同一事务中保存订单和事件
    await uow.orders.save(order)
    await uow.outbox.add("orders.created", {
        "order_id": order.id,
        "customer_id": order.customer_id,
    })
    
    # 2. 一次性提交（全成功或全失败）
    await uow.commit()
    
    # 3. 后台任务会异步发布事件
```

## 📦 Bento 框架中的 Outbox

### 架构

```
┌─────────────────────────────────────────────────────┐
│  Use Case (Application Layer)                       │
│  ┌──────────┐                                       │
│  │ Command  │                                       │
│  │ Handler  │                                       │
│  └────┬─────┘                                       │
│       │                                             │
│       ▼                                             │
│  ┌──────────┐    ┌─────────────┐                  │
│  │   UoW    │───▶│   Outbox    │                  │
│  └────┬─────┘    └──────┬──────┘                  │
│       │                 │                           │
└───────┼─────────────────┼───────────────────────────┘
        │                 │
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│   Database   │  │ outbox_table │
│  (orders)    │  │   (pending)  │
└──────────────┘  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Background  │
                  │   Worker     │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Message Bus  │
                  │ (Kafka/Pulsar)│
                  └──────────────┘
```

## 🔧 当前实现

### 1. Outbox Repository

框架提供 `SqlAlchemyOutbox`：

```python
from bento.persistence.sqlalchemy.outbox_sql import SqlAlchemyOutbox

# 自动在 composition.py 中注入
uow.outbox = SqlAlchemyOutbox(session)
```

### 2. Outbox 表结构

```sql
CREATE TABLE outboxrecord (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic VARCHAR(255) NOT NULL,
    payload TEXT NOT NULL,       -- JSON 格式
    status VARCHAR(16) DEFAULT 'pending',
    INDEX idx_topic (topic),
    INDEX idx_status (status)
);
```

### 3. 在 Use Case 中使用

```python
from bento.application.ports import IUnitOfWork
from applications.ecommerce.modules.order.domain.order import Order

class CreateOrderUseCase:
    async def execute(
        self, 
        command: CreateOrderCommand, 
        uow: IUnitOfWork
    ) -> Order:
        # 创建订单
        order = Order(
            order_id=ID.generate(),
            customer_id=ID(command.customer_id),
        )
        
        # 添加商品
        for item in command.items:
            order.add_item(
                product_id=ID(item.product_id),
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
        
        # 保存订单
        repo = OrderRepository(uow.session)
        await repo.save(order)
        
        # 📤 将领域事件写入 Outbox
        for event in order.events:
            await uow.outbox.add(
                topic=f"orders.{event.name.lower()}",
                payload={
                    "event_id": str(event.event_id),
                    "event_type": event.name,
                    "occurred_at": event.occurred_at.isoformat(),
                    "order_id": str(order.id),
                    # ... 更多事件数据
                }
            )
        
        # 清除已处理的事件
        order.clear_events()
        
        # 提交事务（订单 + Outbox 一起提交）
        await uow.commit()
        
        return order
```

## 🚀 完整示例

### 步骤 1: 创建订单（写入 Outbox）

```python
# API 调用
POST /api/orders/
{
  "customer_id": "cust-123",
  "items": [...]
}

# 数据库事务：
# 1. INSERT INTO orders ...
# 2. INSERT INTO outboxrecord (topic='orders.created', payload='...', status='pending')
# 3. COMMIT
```

### 步骤 2: 后台 Worker 发布事件

```python
# 伪代码 - 后台任务
async def outbox_publisher():
    while True:
        # 拉取待发布的消息
        messages = await outbox.pull_batch(limit=100)
        
        for msg in messages:
            try:
                # 发布到消息队列
                await message_bus.publish(
                    topic=msg['topic'],
                    payload=msg['payload']
                )
                
                # 标记为已发布
                await outbox.mark_published(msg['id'])
                
            except Exception as e:
                # 记录错误，稍后重试
                logger.error(f"Failed to publish: {e}")
        
        await asyncio.sleep(5)  # 每 5 秒轮询一次
```

### 步骤 3: 消费者处理事件

```python
# 另一个服务订阅 "orders.created"
@message_handler("orders.created")
async def on_order_created(payload: dict):
    order_id = payload['order_id']
    
    # 业务逻辑
    await inventory_service.reserve_items(order_id)
    await notification_service.send_confirmation(order_id)
```

## 🎯 当前状态

### ✅ 已实现

- [x] `SqlAlchemyOutbox` 仓储实现
- [x] `OutboxRecord` 表定义
- [x] UnitOfWork 集成
- [x] 数据库表自动创建
- [x] 所有测试通过（16/16）

### 🚧 待实现

- [ ] 后台 Worker（Outbox Publisher）
- [ ] 消息重试机制
- [ ] 死信队列（DLQ）
- [ ] 监控和告警
- [ ] 消息去重（Idempotency Key）

## 🔍 调试 Outbox

### 查看待发布的消息

```sql
SELECT * FROM outboxrecord 
WHERE status = 'pending' 
ORDER BY id DESC;
```

### 手动发布消息

```python
from bento.persistence.sqlalchemy.outbox_sql import SqlAlchemyOutbox

async with session_scope() as session:
    outbox = SqlAlchemyOutbox(session)
    
    # 拉取消息
    messages = await outbox.pull_batch(limit=10)
    
    for msg in messages:
        print(f"Topic: {msg['topic']}")
        print(f"Payload: {msg['payload']}")
        
        # 发布后标记
        await outbox.mark_published(msg['id'])
    
    await session.commit()
```

### 清理已发布的消息

```sql
-- 删除 7 天前已发布的消息
DELETE FROM outboxrecord 
WHERE status = 'published' 
AND created_at < datetime('now', '-7 days');
```

## 📚 最佳实践

### 1. 事件负载最小化

```python
# ✅ 好：只存储必要信息
await uow.outbox.add("orders.created", {
    "order_id": "123",
    "customer_id": "456",
    "total_amount": 999.99,
})

# ❌ 避免：存储整个订单对象
await uow.outbox.add("orders.created", {
    "order": order.to_dict(),  # 太大了！
})
```

### 2. 使用语义化的 Topic

```python
# ✅ 清晰的命名
"orders.created"
"orders.paid"
"orders.cancelled"
"inventory.reserved"

# ❌ 模糊的命名
"event1"
"order_event"
```

### 3. 包含追踪信息

```python
await uow.outbox.add("orders.created", {
    "trace_id": request_id,      # 用于分布式追踪
    "correlation_id": correlation_id,
    "timestamp": datetime.now().isoformat(),
    "order_id": order.id,
    # ...
})
```

## 🎊 总结

✅ **Outbox 已正确集成到 E-commerce 应用**  
✅ **在同一事务中保存数据和事件**  
✅ **避免了分布式事务的复杂性**  
✅ **保证了最终一致性**  

下一步可以实现后台 Worker 来自动发布 Outbox 中的消息！

