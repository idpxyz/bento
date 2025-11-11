# Bento Framework - Pulsar 优先策略

## 📋 决策说明

**决策时间**: 2025-01-04  
**决策者**: 项目团队  
**状态**: ✅ 已确认

---

## 🎯 核心决策

Bento Framework 将 **Apache Pulsar** 作为**首选消息系统**，而非 Apache Kafka。

---

## 💡 选择 Pulsar 的原因

### 1. **架构优势**

| 特性 | Pulsar | Kafka |
|------|--------|-------|
| **存储与计算分离** | ✅ 天然支持 | ❌ 紧耦合 |
| **多租户** | ✅ 原生支持 | ⚠️ 需额外配置 |
| **地理复制** | ✅ 内置 | ⚠️ 需 MirrorMaker |
| **消息模型** | ✅ 队列 + 流 | ⚠️ 仅流 |
| **消息去重** | ✅ 内置 | ❌ 需自实现 |
| **分层存储** | ✅ 内置（Tiered Storage）| ⚠️ 需额外配置 |

### 2. **功能丰富**

- ✅ **原生支持 RPC**：Request/Reply 模式
- ✅ **Schema Registry**：内置 Schema 管理
- ✅ **死信队列（DLQ）**：开箱即用
- ✅ **延迟消息**：原生支持
- ✅ **消息追踪**：完整的消息追踪链路

### 3. **性能优势**

- ✅ **低延迟**：P99 延迟更低
- ✅ **高吞吐**：存储计算分离，扩展性更好
- ✅ **无限存储**：支持对接 S3/HDFS 等

### 4. **运维友好**

- ✅ **水平扩展**：存储和计算独立扩展
- ✅ **零拷贝**：减少内存使用
- ✅ **BookKeeper**：成熟的分布式日志存储

### 5. **Old 实现基础**

- ✅ `old/messaging_pulsar/` 目录包含**成熟的 Pulsar 实现**
- ✅ 已有完整的编解码器（JSON, Avro, Protobuf）
- ✅ 已有 Admin、DLQ、观测性等完整功能

---

## 📦 依赖配置

### pyproject.toml

```toml
[project]
dependencies = [
  # Phase 5: Messaging dependencies
  "pulsar-client>=3.4",                   # Apache Pulsar client
]
```

**说明**:
- 使用 `pulsar-client` 官方 Python 客户端
- 版本 >= 3.4（支持最新特性）

---

## 🗂️ 迁移策略

### Phase 5: Messaging 系统

#### 优先级排序

1. **⭐⭐⭐⭐⭐ Pulsar 适配器**（优先）
   - 源文件：`old/messaging_pulsar/`
   - 目标：`src/adapters/messaging/pulsar/`
   - 时间：1-2 周

2. **⭐⭐⭐⭐ Codec 系统**
   - 源文件：`old/messaging_pulsar/codec/`
   - 目标：`src/adapters/messaging/codec/`
   - 时间：1 周

3. **⭐⭐⭐ Kafka 适配器**（可选）
   - 源文件：`old/messaging-kafka/`
   - 目标：`src/adapters/messaging/kafka/`
   - 时间：1-2 周（如果需要）

---

## 🔌 端口与适配器

### MessageBus Port

```python
# src/application/ports/message_bus.py
from typing import Protocol
from bento.domain.domain_event import DomainEvent

class MessageBus(Protocol):
    """Message Bus 端口 - 消息总线契约"""
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish an event."""
        ...
    
    async def subscribe(self, event_type: type, handler: Callable) -> None:
        """Subscribe to an event type."""
        ...
```

### Pulsar 适配器（优先）

```python
# src/adapters/messaging/pulsar/bus.py
from bento.application.ports.message_bus import MessageBus
from pulsar import Client

class PulsarMessageBus:
    """Pulsar MessageBus 适配器 - 实现 MessageBus Port"""
    
    def __init__(self, client: Client, topic: str):
        self.client = client
        self.topic = topic
        self.producer = None
        self.consumer = None
    
    async def publish(self, event: DomainEvent) -> None:
        # 发布到 Pulsar
        ...
    
    async def subscribe(self, event_type: type, handler: Callable) -> None:
        # 订阅 Pulsar Topic
        ...
```

### Kafka 适配器（可选）

```python
# src/adapters/messaging/kafka/bus.py
from bento.application.ports.message_bus import MessageBus
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

class KafkaMessageBus:
    """Kafka MessageBus 适配器 - 实现 MessageBus Port（可选）"""
    
    def __init__(self, bootstrap_servers: str, topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        self.consumer = None
    
    async def publish(self, event: DomainEvent) -> None:
        # 发布到 Kafka
        ...
```

---

## 📚 Old 实现参考

### Pulsar 实现文件结构

```
old/messaging_pulsar/
├── core/                   # 核心抽象
│   ├── bus.py
│   ├── dispatcher.py
│   └── consumer.py
├── pulsar/                 # Pulsar 客户端
│   ├── producer.py
│   ├── consumer.py
│   └── admin.py
├── codec/                  # 编解码器
│   ├── json.py
│   ├── avro.py
│   └── protobuf.py
├── dlq/                    # 死信队列
│   └── handler.py
├── dispatcher/             # 事件分发
│   └── event_dispatcher.py
├── observability/          # 观测性
│   ├── metrics.py
│   └── tracing.py
└── admin/                  # 管理功能
    ├── topic.py
    └── subscription.py
```

### 关键特性

1. **编解码器支持**
   - JSON（默认）
   - Avro（Schema Registry）
   - Protobuf

2. **死信队列（DLQ）**
   - 自动处理失败消息
   - 可配置重试策略

3. **事件分发器**
   - 基于类型的路由
   - 并发处理

4. **观测性**
   - Prometheus 指标
   - OpenTelemetry 追踪

---

## 🚀 使用示例

### 生产环境配置

```python
# runtime/config.py
from pulsar import Client

# Pulsar 客户端配置
pulsar_client = Client(
    service_url='pulsar://localhost:6650',
    operation_timeout_seconds=30,
    authentication=None,  # 或配置认证
)

# MessageBus 注入
from bento.adapters.messaging.pulsar.bus import PulsarMessageBus

message_bus = PulsarMessageBus(
    client=pulsar_client,
    topic='persistent://public/default/events',
)

# 依赖注入
container.register(MessageBus, lambda: message_bus)
```

### 发布事件

```python
from bento.domain.domain_event import DomainEvent

class UserCreatedEvent(DomainEvent):
    user_id: str
    email: str

# 在 UseCase 中
async def create_user(self, command: CreateUserCommand) -> Result:
    user = User.create(...)
    event = UserCreatedEvent(user_id=user.id, email=user.email)
    
    async with self.uow:
        await self.uow.collect_events()  # 收集事件
        await self.uow.commit()          # 提交后发布到 Pulsar
```

### 订阅事件

```python
# 事件处理器
async def handle_user_created(event: UserCreatedEvent) -> None:
    # 发送欢迎邮件
    await send_welcome_email(event.email)

# 注册订阅
await message_bus.subscribe(UserCreatedEvent, handle_user_created)
```

---

## 🔧 开发环境

### Docker Compose 配置

```yaml
# deploy/docker/compose.dev.yaml
services:
  pulsar:
    image: apachepulsar/pulsar:3.1.0
    container_name: pulsar
    ports:
      - "6650:6650"   # Pulsar broker
      - "8080:8080"   # Admin API
    command: bin/pulsar standalone
    volumes:
      - pulsar-data:/pulsar/data
    environment:
      - PULSAR_MEM="-Xms512m -Xmx512m"
```

### 启动开发环境

```bash
# 启动 Pulsar
docker-compose -f deploy/docker/compose.dev.yaml up -d pulsar

# 验证 Pulsar 运行
curl http://localhost:8080/admin/v2/clusters
```

---

## 📊 对比总结

| 维度 | Pulsar | Kafka |
|------|--------|-------|
| **架构** | 存储计算分离 ⭐⭐⭐⭐⭐ | 紧耦合 ⭐⭐⭐ |
| **多租户** | 原生支持 ⭐⭐⭐⭐⭐ | 需配置 ⭐⭐⭐ |
| **消息模型** | 队列 + 流 ⭐⭐⭐⭐⭐ | 仅流 ⭐⭐⭐⭐ |
| **功能丰富度** | 非常丰富 ⭐⭐⭐⭐⭐ | 基础功能 ⭐⭐⭐⭐ |
| **运维复杂度** | 中等 ⭐⭐⭐⭐ | 较高 ⭐⭐⭐ |
| **社区生态** | 活跃 ⭐⭐⭐⭐ | 非常活跃 ⭐⭐⭐⭐⭐ |
| **学习曲线** | 中等 ⭐⭐⭐⭐ | 较平缓 ⭐⭐⭐⭐⭐ |

---

## ✅ 决策确认

- [x] pyproject.toml 已更新（pulsar-client >= 3.4）
- [x] 迁移计划已更新（Pulsar 优先）
- [x] 文档已更新（明确 Pulsar 优先）
- [x] 目录映射已更新（Pulsar ⭐⭐⭐⭐⭐）

---

## 📝 未来考虑

### 如果需要支持 Kafka

如果未来有项目需要 Kafka，可以：

1. **保持 Port 不变**：MessageBus Protocol 保持通用
2. **添加 Kafka 适配器**：`src/adapters/messaging/kafka/`
3. **配置切换**：运行时配置选择使用哪个实现

```python
# runtime/config.py
if config.messaging.backend == "pulsar":
    message_bus = PulsarMessageBus(...)
elif config.messaging.backend == "kafka":
    message_bus = KafkaMessageBus(...)
```

**优势**：端口与适配器分离，易于切换

---

## 🔗 相关文档

- [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) - Phase 5: Messaging 系统
- [TARGET_STRUCTURE.md](./architecture/TARGET_STRUCTURE.md) - 端口与适配器映射
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Messaging 迁移映射

---

**最后更新**: 2025-01-04  
**维护者**: Bento Framework Team  
**状态**: ✅ 已确认并实施

