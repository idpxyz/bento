让我帮您分析当前的事件处理架构。根据您的代码库，我发现了以下关键实现：

### 1. 事件存储实现 ([ch_events_store.py](cci:7://file:///workspace/bento/src/bento/adapters/event_store/ch_events_store.py:0:0-0:0))

```python
class ClickHouseEventStore(EventStore):
    async def append_events(self, events: list[DomainEvent]) -> None:
        # 直接保存到 ClickHouse
        await self._save_events(events)
        # 发布到 Pulsar
        await self._publish_to_pulsar(events)
```

### 2. 消息总线实现 ([message_bus.py](cci:7://file:///workspace/bento/src/bento/adapters/messaging/inprocess/message_bus.py:0:0-0:0))

```python
class PulsarMessageBus(MessageBus):
    async def publish(self, topic: str, message: Any) -> None:
        # 直接发布到 Pulsar
        producer = self._client.create_producer(topic)
        await producer.send(message)
```

### 3. 当前架构的问题

1. **缺少事务性保证**
   - 事件存储和消息发布不是原子操作
   - 如果发布到 Pulsar 失败，事件会丢失

2. **紧耦合**
   - [ClickHouseEventStore](cci:2://file:///workspace/bento/src/bento/adapters/event_store/ch_events_store.py:6:0-88:9) 直接依赖 Pulsar
   - 违反单一职责原则

3. **缺少 In-Process 总线**
   - 领域事件直接发布到外部系统
   - 难以添加本地消费者

### 4. 建议的改进方案

#### 4.1 引入 Outbox 模式

```python
class SqlAlchemyOutbox:
    async def save_events(self, events: list[DomainEvent]) -> None:
        # 在事务中保存事件到 outbox 表
        async with self.uow:
            for event in events:
                outbox_record = OutboxRecord(
                    event_id=event.id,
                    topic=event.topic,
                    payload=event.json(),
                    status='pending'
                )
                self.uow.session.add(outbox_record)
            await self.uow.commit()
```

#### 4.2 添加 Outbox 处理器

```python
class OutboxProcessor:
    def __init__(self, outbox_repo: OutboxRepository, event_bus: EventBus):
        self.outbox_repo = outbox_repo
        self.event_bus = event_bus

    async def process_pending_events(self):
        events = await self.outbox_repo.get_pending_events()
        for event in events:
            try:
                await self.event_bus.publish(event.topic, event.payload)
                await self.outbox_repo.mark_as_processed(event.id)
            except Exception:
                await self.outbox_repo.mark_as_failed(event.id)
```

#### 4.3 更新事件存储

```python
class ClickHouseEventStore(EventStore):
    async def append_events(self, events: list[DomainEvent]) -> None:
        # 1. 保存到 ClickHouse
        await self._save_events(events)
        # 2. 保存到 Outbox 表
        await self.outbox_processor.save_events(events)
```

#### 4.4 添加 In-Process 事件总线

```python
class InProcessEventBus(EventBus):
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_type: Type[DomainEvent], handler: Callable):
        self.subscribers[event_type].append(handler)

    async def publish(self, event: DomainEvent):
        for handler in self.subscribers[type(event)]:
            await handler(event)
```

### 5. 迁移步骤

1. **第一步：实现基础组件**
   - 实现 `SqlAlchemyOutbox` 和 `OutboxProcessor`
   - 添加 `InProcessEventBus`

2. **第二步：重构事件存储**
   - 从 [ClickHouseEventStore](cci:2://file:///workspace/bento/src/bento/adapters/event_store/ch_events_store.py:6:0-88:9) 移除 Pulsar 依赖
   - 添加 Outbox 集成

3. **第三步：更新消息总线**
   - 实现 `PulsarEventBus` 适配器
   - 订阅 In-Process 总线并转发到 Pulsar

4. **第四步：配置依赖注入**
   - 注册新的服务
   - 更新现有的事件发布代码

需要我帮您实现其中某个具体组件吗？或者您想了解更详细的迁移计划？
