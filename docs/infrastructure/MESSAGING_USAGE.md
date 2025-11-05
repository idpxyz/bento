## Messaging 系统使用指南

**版本**: 1.0  
**最后更新**: 2025-11-04

---

## 📖 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [配置](#配置)
4. [发布事件](#发布事件)
5. [订阅事件](#订阅事件)
6. [Outbox Pattern](#outbox-pattern)
7. [最佳实践](#最佳实践)
8. [故障排查](#故障排查)

---

## 快速开始

### 前置条件

1. **Pulsar 运行中**:
```bash
docker run -d \
  -p 6650:6650 \
  -p 8080:8080 \
  apachepulsar/pulsar:latest \
  bin/pulsar standalone
```

2. **安装依赖**:
```bash
pip install pulsar-client
```

### 5 分钟示例

```python
from adapters.messaging.pulsar import PulsarMessageBus, PulsarConfig
from bento.domain.domain_event import DomainEvent

# 1. 创建 MessageBus
config = PulsarConfig(service_url="pulsar://localhost:6650")
bus = PulsarMessageBus(config, source="my-service")

# 2. 启动
await bus.start()

# 3. 定义事件
class UserRegisteredEvent(DomainEvent):
    def __init__(self, user_id: str, email: str):
        super().__init__(name="user.UserRegistered")
        self.user_id = user_id
        self.email = email

# 4. 发布事件
event = UserRegisteredEvent(user_id="123", email="user@example.com")
await bus.publish(event)

# 5. 订阅事件
async def handle_user_registered(event: UserRegisteredEvent):
    print(f"New user: {event.user_id}")

await bus.subscribe(UserRegisteredEvent, handle_user_registered)

# 6. 关闭
await bus.stop()
```

---

## 核心概念

### 1. MessageEnvelope (消息封装)

所有消息都被封装在 `MessageEnvelope` 中：

```python
from messaging.envelope import MessageEnvelope

envelope = MessageEnvelope(
    event_type="order.OrderCreated",        # 事件类型
    payload={"order_id": "123"},             # 事件数据
    event_id="evt-001",                      # 事件ID (自动生成)
    occurred_at=datetime.utcnow(),           # 发生时间
    source="order-service",                  # 来源服务
    correlation_id="req-789",                # 请求追踪ID
    causation_id="evt-000",                  # 因果关系ID
    version="1.0"                            # Schema 版本
)
```

**关键字段**:
- `event_type`: 事件类型（用于路由）
- `payload`: 实际事件数据
- `event_id`: 全局唯一 ID
- `correlation_id`: 分布式追踪
- `causation_id`: 事件链追踪

### 2. MessageCodec (编解码器)

负责消息的序列化和反序列化：

```python
from messaging.codec import JsonCodec

codec = JsonCodec(indent=2)

# 编码
data = codec.encode(envelope)  # MessageEnvelope → bytes

# 解码
envelope = codec.decode(data)  # bytes → MessageEnvelope
```

**可用 Codec**:
- `JsonCodec`: JSON 格式（默认）
- `AvroCodec`: Avro 格式 (TODO)
- `ProtobufCodec`: Protobuf 格式 (TODO)

### 3. MessageBus (消息总线)

定义在 `application.ports.MessageBus`：

```python
class MessageBus(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
    async def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None: ...
    async def unsubscribe(self, event_type: type[DomainEvent], handler: Callable) -> None: ...
    async def start() -> None: ...
    async def stop() -> None: ...
```

**实现**:
- `PulsarMessageBus`: Apache Pulsar 实现 ✅
- `KafkaMessageBus`: Apache Kafka 实现 (TODO)
- `RedisMessageBus`: Redis Pub/Sub 实现 (TODO)

---

## 配置

### 环境变量配置

```bash
# Pulsar 连接
export PULSAR_URL="pulsar://192.168.1.100:6650"

# 认证 (可选)
export PULSAR_AUTH_TOKEN="your-token-here"

# TLS (可选)
export PULSAR_TLS_ENABLED="true"
export PULSAR_TLS_CERT_PATH="/path/to/cert.pem"
export PULSAR_TLS_VALIDATE_HOSTNAME="true"

# Namespace
export PULSAR_TENANT="my-company"
export PULSAR_NAMESPACE="production"
```

### 代码配置

```python
from adapters.messaging.pulsar import PulsarConfig

# 从环境变量加载
config = PulsarConfig.from_env()

# 手动配置
config = PulsarConfig(
    service_url="pulsar://localhost:6650",
    tenant="my-company",
    namespace="production",
    auth_token="your-token"
)
```

### Topic 命名

Topic 格式: `{prefix}://{tenant}/{namespace}/{event_type}`

示例:
- 输入: `order.OrderCreated`
- 输出: `persistent://public/default/order.OrderCreated`

自定义:
```python
config = PulsarConfig(
    tenant="acme",
    namespace="prod",
    topic_prefix="persistent"
)

topic = config.get_topic_fqn("order.OrderCreated")
# Returns: "persistent://acme/prod/order.OrderCreated"
```

---

## 发布事件

### 1. 定义 Domain Event

```python
from bento.domain.domain_event import DomainEvent
from bento.core.clock import now_utc

class OrderCreatedEvent(DomainEvent):
    def __init__(self, order_id: str, customer_id: str, total: float):
        super().__init__(
            name="order.OrderCreated",
            occurred_at=now_utc()
        )
        self.order_id = order_id
        self.customer_id = customer_id
        self.total = total

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "total": self.total,
        }
```

### 2. 发布事件

```python
# 创建事件
event = OrderCreatedEvent(
    order_id="order-001",
    customer_id="cust-123",
    total=99.99
)

# 发布到 MessageBus
await message_bus.publish(event)
```

### 3. 在 Use Case 中发布

```python
from application.usecase import UseCase

class CreateOrderUseCase(UseCase):
    def __init__(self, uow: UnitOfWork, message_bus: MessageBus):
        self.uow = uow
        self.message_bus = message_bus

    async def execute(self, request: CreateOrderRequest) -> CreateOrderResponse:
        async with self.uow:
            # 创建订单
            order = Order.create(...)
            await self.uow.orders.save(order)

            # 提交事务
            await self.uow.commit()

        # 发布事件 (事务外)
        event = OrderCreatedEvent(...)
        await self.message_bus.publish(event)

        return CreateOrderResponse(order_id=order.id)
```

---

## 订阅事件

### 1. 定义 Event Handler

```python
async def handle_order_created(event: OrderCreatedEvent) -> None:
    """处理订单创建事件"""
    print(f"📦 Order created: {event.order_id}")

    # 业务逻辑
    await send_confirmation_email(event.customer_id)
    await update_inventory(event.order_id)
```

### 2. 注册 Handler

```python
# 订阅单个事件
await message_bus.subscribe(OrderCreatedEvent, handle_order_created)

# 订阅多个事件
await message_bus.subscribe(OrderCreatedEvent, handler1)
await message_bus.subscribe(OrderCreatedEvent, handler2)  # 同一事件多个处理器
await message_bus.subscribe(PaymentProcessedEvent, handle_payment)
```

### 3. 取消订阅

```python
await message_bus.unsubscribe(OrderCreatedEvent, handle_order_created)
```

### 4. 在应用启动时注册

```python
# runtime/composition.py

async def setup_event_handlers(message_bus: MessageBus) -> None:
    """注册所有事件处理器"""

    # Order events
    await message_bus.subscribe(OrderCreatedEvent, handle_order_created)
    await message_bus.subscribe(OrderShippedEvent, handle_order_shipped)

    # Payment events
    await message_bus.subscribe(PaymentProcessedEvent, handle_payment_processed)

    # User events
    await message_bus.subscribe(UserRegisteredEvent, handle_user_registered)

# 在应用启动时调用
async def startup():
    message_bus = create_message_bus()
    await message_bus.start()
    await setup_event_handlers(message_bus)
```

---

## Outbox Pattern

### 为什么使用 Outbox Pattern？

**问题**: 数据库事务 + 消息发布的原子性

```python
# ❌ 不可靠的实现
async with uow:
    order = Order.create(...)
    await uow.orders.save(order)
    await uow.commit()  # ← 可能成功

await message_bus.publish(event)  # ← 可能失败！
# 结果：订单保存了，但事件没发布 = 数据不一致
```

**解决方案**: Transactional Outbox Pattern

```python
# ✅ 可靠的实现
async with uow:
    order = Order.create(...)
    await uow.orders.save(order)

    # 事件保存到 Outbox 表（同一事务）
    outbox = OutboxRecord(
        topic="order.OrderCreated",
        payload=json.dumps(event.to_dict()),
        status="pending"
    )
    uow.session.add(outbox)

    await uow.commit()  # ← 原子操作：Order + Outbox

# OutboxProjector 异步发布
# - 轮询 Outbox 表
# - 发布到 MessageBus
# - 更新状态为 'published'
```

### 使用 OutboxProjector

#### 1. 创建 OutboxProjector

```python
from infrastructure.projection import OutboxProjector

projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus,
    batch_size=200  # 每批处理 200 条
)
```

#### 2. 后台运行

```python
# 方式 1: asyncio.create_task
task = asyncio.create_task(projector.run_forever())

# 方式 2: 在 FastAPI lifespan 中
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task = asyncio.create_task(projector.run_forever())
    yield
    # Shutdown
    await projector.stop()
    task.cancel()
```

#### 3. 手动触发 (测试)

```python
# 处理所有待发布事件
count = await projector.publish_all()
print(f"Published {count} events")
```

### 完整流程

```python
# 1. 创建基础设施
session_factory = create_session_factory()
message_bus = PulsarMessageBus(config)
await message_bus.start()

# 2. 创建 OutboxProjector
projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus
)

# 3. 启动 Projector
projector_task = asyncio.create_task(projector.run_forever())

# 4. 业务逻辑 (保存事件到 Outbox)
async with uow:
    order = Order.create(...)
    await uow.orders.save(order)
    # Outbox 记录在 UoW.commit() 时自动创建
    await uow.commit()

# 5. OutboxProjector 自动发布
# (无需手动干预)

# 6. 关闭
await projector.stop()
await message_bus.stop()
```

---

## 最佳实践

### 1. Event Naming

**推荐**:
- 使用过去式: `OrderCreated`, `PaymentProcessed`
- 使用命名空间: `order.OrderCreated`, `payment.PaymentProcessed`
- 保持一致性: `{domain}.{EventName}`

**示例**:
```python
class OrderCreatedEvent(DomainEvent):
    def __init__(self, ...):
        super().__init__(name="order.OrderCreated")
```

### 2. Idempotency (幂等性)

Event handlers **必须是幂等的**（多次执行结果一致）:

```python
# ✅ 幂等的 Handler
async def handle_order_created(event: OrderCreatedEvent) -> None:
    # 使用唯一键检查是否已处理
    if await is_already_processed(event.event_id):
        return  # 跳过重复事件

    # 处理事件
    await send_email(event.customer_id)

    # 标记为已处理
    await mark_as_processed(event.event_id)
```

### 3. Error Handling

```python
async def handle_order_created(event: OrderCreatedEvent) -> None:
    try:
        await send_email(event.customer_id)
    except EmailServiceError as e:
        logger.error(f"Failed to send email: {e}")
        # 不要抛出异常（会导致消息重试）
        # 可以保存到 DLQ (Dead Letter Queue)
        await save_to_dlq(event, error=str(e))
```

### 4. Correlation ID

使用 `correlation_id` 追踪请求链：

```python
# API 层：生成 correlation_id
correlation_id = str(uuid4())

# Use Case 层：传递 correlation_id
event = OrderCreatedEvent(...)
envelope = MessageEnvelope(
    event_type=...,
    payload=...,
    correlation_id=correlation_id  # ← 传递
)

# Handler 层：记录 correlation_id
async def handle_order_created(event):
    logger.info(f"Processing order", extra={
        "correlation_id": event.correlation_id
    })
```

### 5. Graceful Shutdown

```python
# 信号处理
import signal

shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 主循环
await shutdown_event.wait()

# 优雅关闭
await projector.stop()
await message_bus.stop()
```

---

## 故障排查

### 1. 无法连接到 Pulsar

**症状**: `ConnectionError: Failed to connect to Pulsar`

**解决**:
```bash
# 检查 Pulsar 是否运行
docker ps | grep pulsar

# 检查端口
telnet localhost 6650

# 检查配置
echo $PULSAR_URL
```

### 2. 事件没有被发布

**症状**: Outbox 表中有 `pending` 记录，但一直不变

**检查**:
```python
# 检查 OutboxProjector 是否运行
logger.info("OutboxProjector started")  # 应该看到这个日志

# 检查 Outbox 表
SELECT * FROM outbox WHERE status = 'pending';

# 手动触发
await projector.publish_all()
```

### 3. 事件重复处理

**症状**: Handler 被调用多次

**原因**: Pulsar 使用 **at-least-once** 语义

**解决**: 实现 idempotency
```python
# 使用唯一键去重
processed_events = set()

async def handle_event(event):
    if event.event_id in processed_events:
        return
    processed_events.add(event.event_id)
    # ... 处理事件
```

### 4. 查看 Pulsar Topics

```bash
# 进入 Pulsar 容器
docker exec -it <pulsar-container> bash

# 列出 topics
bin/pulsar-admin topics list public/default

# 查看 topic 统计
bin/pulsar-admin topics stats persistent://public/default/order.OrderCreated
```

---

## 总结

✅ **核心概念**: MessageEnvelope, Codec, MessageBus  
✅ **发布事件**: `await bus.publish(event)`  
✅ **订阅事件**: `await bus.subscribe(EventType, handler)`  
✅ **Outbox Pattern**: 保证事务一致性  
✅ **最佳实践**: 幂等性、错误处理、优雅关闭

**下一步**: 查看 `examples/messaging/pulsar_outbox_example.py` 获取完整示例！


