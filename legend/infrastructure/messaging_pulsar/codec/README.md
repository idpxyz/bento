# 消息编解码器 (Message Codecs)

这个模块提供了多种消息序列化和反序列化格式的实现，用于在消息总线中传输消息。

## 支持的编解码格式

1. **JSON** (默认)
   - 基于 Python 标准库的 json 模块
   - 人类可读，便于调试
   - 序列化/反序列化性能适中

2. **Protocol Buffers**
   - Google 开发的高效二进制序列化格式
   - 比 JSON 更紧凑，序列化/反序列化更快
   - 支持向前兼容和向后兼容
   - 适合跨语言服务间通信

3. **Avro**
   - Apache 开发的数据序列化系统
   - 支持复杂的数据类型和 Schema 演化
   - 提供紧凑的二进制格式
   - 内置 Schema 元数据，适合长期数据存储

## 安装依赖

安装所需的依赖:

```bash
pip install -r requirements-codec.txt
```

## Protocol Buffers 设置

首次使用或更新 .proto 文件后需生成 Python 代码:

```bash
cd src/idp/framework/infrastructure/messaging/codec/proto
python generate_protos.py
```

## 使用方法

### 基本使用

```python
from idp.framework.infrastructure.messaging.core.codec import get_codec
from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope

# 创建消息
envelope = MessageEnvelope(
    event_type="user.registered",
    payload={"user_id": "123", "email": "user@example.com"},
    source="user-service",
    correlation_id="abc-123"
)

# 使用默认编解码器 (JSON)
codec = get_codec()
serialized = codec.encode(envelope)
message = codec.decode(serialized)

# 使用 Protocol Buffer 编解码器
protobuf_codec = get_codec("protobuf")
pb_serialized = protobuf_codec.encode(envelope)
pb_message = protobuf_codec.decode(pb_serialized)

# 使用 Avro 编解码器
avro_codec = get_codec("avro")
avro_serialized = avro_codec.encode(envelope)
avro_message = avro_codec.decode(avro_serialized)
```

### 在事件总线中使用

在 Pulsar 事件总线实现中，可以指定使用哪个编解码器:

```python
from idp.framework.infrastructure.messaging.pulsar.event_bus import PulsarEventBus
from idp.framework.infrastructure.messaging.core.codec import get_codec

# 创建使用 Protocol Buffer 的事件总线
event_bus = PulsarEventBus(codec=get_codec("protobuf"))

# 或创建使用 Avro 的事件总线
event_bus = PulsarEventBus(codec=get_codec("avro"))
```

## 性能对比

| 编解码器 | 序列化速度 | 反序列化速度 | 数据大小 | 兼容性 |
|--------|-----------|------------|--------|-------|
| JSON    | 中等      | 中等        | 较大    | 良好   |
| Protobuf | 快速     | 快速        | 小     | 优秀   |
| Avro    | 快速      | 快速        | 小     | 优秀   |

## 最佳实践

1. 简单场景或调试阶段，使用 JSON 编解码器
2. 高性能要求场景，使用 Protocol Buffer 编解码器
3. 需要严格 Schema 管理的场景，使用 Avro 编解码器