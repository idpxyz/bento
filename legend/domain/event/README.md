# 领域事件 (Domain Events)

领域事件是领域驱动设计 (DDD) 中的核心概念，代表在领域中发生的事实。它们是不可变的，并且包含事件发生时的完整上下文。

## 设计原则

1. **领域事件属于领域层**：领域事件应该定义在领域层，而不是基础设施层。
2. **不可变性**：一旦创建，领域事件不应该被修改。
3. **自包含**：领域事件应该包含理解事件所需的所有信息。
4. **命名约定**：领域事件应该使用过去时态命名，如 `UserCreated`、`OrderPlaced` 等。
5. **与聚合关联**：领域事件通常与聚合根关联，表示聚合状态的变化。

## 端口与适配器架构

本项目采用端口与适配器架构(六边形架构)来处理领域事件的发布和订阅：

1. **端口(Ports)**：在领域层定义接口
   - `EventPublisherPort`: 发布领域事件的接口
   - `EventSubscriberPort`: 订阅领域事件的接口
   - `EventBusPort`: 结合发布和订阅功能的完整接口

2. **适配器(Adapters)**：在基础设施层实现接口
   - `MessageBusAdapter`: 使用消息总线实现领域事件端口

这种架构确保了：
- 领域层不依赖基础设施层
- 依赖方向从外向内(基础设施层依赖领域层)
- 领域模型的纯粹性和独立性

## 基本用法

### 定义领域事件

```python
from idp.domain.event.base import DomainEvent

class UserCreatedEvent(DomainEvent):
    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        # ... 其他领域特定属性
        **kwargs  # 传递给基类的参数
    ):
        # 如果未提供聚合根ID，则使用user_id
        if "aggregate_id" not in kwargs:
            kwargs["aggregate_id"] = user_id
            
        super().__init__(**kwargs)
        
        self._user_id = user_id
        self._username = username
        self._email = email
        
    # 属性访问器
    @property
    def user_id(self) -> str:
        return self._user_id
    
    @property
    def username(self) -> str:
        return self._username
    
    @property
    def email(self) -> str:
        return self._email
    
    # 实现抽象方法
    def get_payload(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email
        }
    
    # 从负载创建事件的工厂方法
    @classmethod
    def from_payload(cls, payload: Dict[str, Any], **kwargs) -> 'UserCreatedEvent':
        return cls(
            user_id=payload["user_id"],
            username=payload["username"],
            email=payload["email"],
            **kwargs
        )
```

### 使用事件总线

#### 方式1: 使用上下文管理器

```python
from idp.domain.event.context import event_bus_context
from idp.infrastructure.messaging.adapters.factory import EventBusAdapterFactory

async def example():
    # 创建事件总线适配器
    event_bus = await EventBusAdapterFactory.create_adapter()
    
    # 使用上下文管理器
    async with event_bus_context(event_bus) as bus:
        # 注册事件类型
        bus.register_event_type(UserCreatedEvent)
        
        # 订阅事件
        await bus.subscribe(UserCreatedEvent, handle_user_created)
        
        # 创建事件
        event = UserCreatedEvent(
            user_id="user-123",
            username="john_doe",
            email="john@example.com"
        )
        
        # 发布事件
        await bus.publish(event)
```

#### 方式2: 手动管理生命周期

```python
from idp.infrastructure.messaging.adapters.factory import EventBusAdapterFactory

async def example():
    # 获取事件总线适配器单例
    event_bus = await EventBusAdapterFactory.get_instance()
    
    try:
        # 初始化事件总线
        await event_bus.initialize()
        
        # 注册事件类型
        event_bus.register_event_type(UserCreatedEvent)
        
        # 订阅事件
        await event_bus.subscribe(UserCreatedEvent, handle_user_created)
        
        # 创建事件
        event = UserCreatedEvent(
            user_id="user-123",
            username="john_doe",
            email="john@example.com"
        )
        
        # 发布事件
        await event_bus.publish(event)
    finally:
        # 关闭事件总线
        await event_bus.shutdown()
```

#### 方式3: 依赖注入

```python
from idp.domain.event.ports import EventBusPort

class UserService:
    def __init__(self, event_bus: EventBusPort):
        self.event_bus = event_bus
    
    async def create_user(self, user_id: str, username: str, email: str) -> None:
        # 业务逻辑...
        
        # 创建事件
        event = UserCreatedEvent(
            user_id=user_id,
            username=username,
            email=email
        )
        
        # 发布事件
        await self.event_bus.publish(event)
```

## 事件处理

### 定义事件处理函数

```python
async def handle_user_created(event: DomainEvent) -> bool:
    if isinstance(event, UserCreatedEvent):
        print(f"处理用户创建事件: {event.username} ({event.email})")
        # 处理逻辑...
        return True
    return False
```

### 订阅事件

```python
# 订阅特定类型的事件
subscription_id = await event_bus.subscribe(UserCreatedEvent, handle_user_created)

# 取消订阅
await event_bus.unsubscribe(subscription_id)
```

## 最佳实践

1. **保持事件简单**：领域事件应该只包含必要的信息，避免过度复杂。
2. **版本控制**：使用版本字段支持事件架构的演变。
3. **使用工厂方法**：提供工厂方法简化事件创建。
4. **文档化**：清晰记录每个事件的目的和内容。
5. **测试**：为领域事件编写单元测试，确保正确性。
6. **使用端口与适配器**：通过端口与适配器架构保持领域层的纯粹性。

## 与事件溯源的关系

领域事件是实现事件溯源的基础。在事件溯源中，聚合的状态通过重放其历史事件来重建。

```python
async def rebuild_user_aggregate(user_id: str, event_store: EventStore):
    # 获取用户的所有事件
    events = await event_store.get_by_aggregate_id(user_id)
    
    # 按时间戳排序
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    
    # 创建空用户
    user = User.create_empty()
    
    # 应用每个事件
    for event in sorted_events:
        user.apply(event)
    
    return user
```

## 结论

领域事件是DDD中连接领域模型和外部系统的关键机制。通过端口与适配器架构，我们确保了领域模型的完整性和独立性，同时实现了与基础设施层的集成。这种设计符合DDD的核心原则，使系统更加可维护、可测试和可扩展。 