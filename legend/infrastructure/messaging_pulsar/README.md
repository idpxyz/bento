# 消息系统 (Messaging System)

IDP框架的异步消息基础设施，支持事件驱动架构和微服务间的异步通信。

## 主要功能

- 发布-订阅模式的消息传递
- 事件总线抽象（支持Apache Pulsar）
- 领域事件的发布与处理
- 多种序列化格式支持（JSON、Protocol Buffers、Avro）
- 集成可观测性和错误处理
- 死信队列(DLQ)处理失败消息

## 快速入门

### 安装

```bash
# 安装基本依赖
pip install -r requirements.txt

# 安装编解码器依赖并生成代码
python install_codecs.py
```

### 发布事件

```python
from idp.framework.infrastructure.messaging.pulsar.event_bus import PulsarEventBus

event_bus = PulsarEventBus()

await event_bus.publish_event(
    event_type="user.registered",
    payload={"user_id": "123", "email": "user@example.com"},
    source="user-service",
    correlation_id="req-abc-123"
)
```

### 处理事件

```python
from idp.framework.infrastructure.messaging.dispatcher.decorator import event_handler
from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope

@event_handler("user.registered")
async def handle_user_registered(message: MessageEnvelope):
    print(f"用户注册成功: {message.payload['email']}")
    # 处理用户注册事件...
```

### 使用高性能编解码器

```python
# 使用Protocol Buffers
event_bus = PulsarEventBus(codec_name="protobuf")

# 使用Avro
event_bus = PulsarEventBus(codec_name="avro")
```

## 架构概览

消息系统由以下模块组成:

- **core**: 核心接口和基础结构，包括`MessageBus`和`EventBus`抽象
- **pulsar**: 基于Apache Pulsar的实现
- **codec**: 消息编解码器（序列化/反序列化）
  - **JSON**: 默认编解码器，用于调试
  - **Protocol Buffers**: 高性能二进制格式
  - **Avro**: 支持复杂数据类型和Schema演化
- **dispatcher**: 事件分发和处理
- **event**: 领域事件定义
- **dlq**: 死信队列处理
- **observability**: 可观测性和监控
- **demo**: 示例和演示

## 多编解码格式支持

消息系统支持以下编解码格式:

| 格式 | 特点 | 推荐场景 |
|-----|-----|---------|
| JSON | 人类可读，便于调试 | 开发/测试环境 |
| Protocol Buffers | 高性能，紧凑 | 生产环境，跨语言服务 |
| Avro | 支持Schema演化 | 需要严格Schema管理的场景 |

可以使用演示脚本比较性能:

```bash
python -m idp.framework.infrastructure.messaging.demo.codec_comparison
```

## 示例

完整示例请参考 `demo/` 目录下的示例程序:

- `event_bus_demo.py`: 演示如何使用事件总线发布和订阅事件
- `codec_comparison.py`: 比较不同编解码器的性能

## 开发

扩展消息系统:

1. 实现新的消息总线:
   ```python
   from idp.framework.infrastructure.messaging.core.message_bus import AbstractMessageBus
   
   class MyCustomMessageBus(AbstractMessageBus):
       # 实现所需的方法...
   ```

2. 实现新的编解码器:
   ```python
   from idp.framework.infrastructure.messaging.core.codec import MessageCodec, register_codec
   
   class MyCustomCodec(MessageCodec):
       # 实现编码解码方法...
       
   # 注册到全局注册表
   register_codec("my-format", MyCustomCodec())
   ```

## 文档

详细文档请参考 `docs/` 目录:

- [编解码器系统](docs/codecs.md)
- [事件处理](docs/event_handling.md)
- [错误处理策略](docs/error_handling.md)
- [可观测性](docs/observability.md) 