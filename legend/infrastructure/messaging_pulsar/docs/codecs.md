# 消息编解码器系统

## 概述

消息编解码器系统负责消息的序列化和反序列化，支持多种编码格式，包括:

- **JSON**: 默认编码格式，适合调试和开发阶段
- **Protocol Buffers**: 高性能二进制格式，适合生产环境
- **Apache Avro**: 支持复杂数据类型和Schema演化的序列化系统

编解码器子系统具有如下特性:

1. **可插拔架构**: 基于注册表模式，方便扩展新的编解码格式
2. **运行时选择**: 可在运行时根据需要选择不同的编解码器
3. **透明使用**: 对业务代码隐藏底层实现细节
4. **性能优化**: 高性能编解码器可显著提升消息处理速度

## 架构设计

编解码器系统由以下组件构成:

- **MessageCodec 接口**: 定义编解码器的统一接口
- **具体编解码器实现**: 如 JsonMessageCodec, ProtobufMessageCodec, AvroMessageCodec
- **编解码器注册表**: 管理所有可用的编解码器
- **Schema定义**: Protocol Buffers (.proto) 和 Avro (.avsc) 的消息格式定义

### 类图关系

```
                      ┌─────────────┐
                      │ MessageCodec│
                      │   (接口)    │
                      └──────┬──────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
┌──────────▼─────────┐ ┌─────▼───────────┐ ┌───▼───────────────┐
│  JsonMessageCodec  │ │ProtobufCodec    │ │ AvroMessageCodec  │
└────────────────────┘ └─────────────────┘ └───────────────────┘
```

## 如何扩展

添加新的编解码器只需实现 `MessageCodec` 接口并注册:

```python
from idp.framework.infrastructure.messaging.core.codec import MessageCodec, register_codec

class MyCustomCodec(MessageCodec):
    def encode(self, envelope: MessageEnvelope) -> bytes:
        # 自定义编码逻辑
        ...
        
    def decode(self, raw: bytes) -> MessageEnvelope:
        # 自定义解码逻辑
        ...

# 注册到全局注册表        
register_codec("my-format", MyCustomCodec())
```

## Protocol Buffers

Google开发的高效二进制序列化格式。主要优势:

- 比JSON更紧凑，序列化/反序列化性能高
- 强类型，提供静态类型检查
- 支持向前/向后兼容
- 支持多语言代码生成

我们的Protocol Buffers实现位于 `messaging/codec/proto/` 目录。

### 定义消息结构

```protobuf
// message.proto
syntax = "proto3";

package idp.messaging;

message MessageEnvelope {
  string event_type = 1;
  map<string, string> payload = 2;
  string occurred_at = 3;
  string source = 4;
  string correlation_id = 5;
}
```

### 生成代码

首次使用或更新Schema后需生成代码:

```bash
cd src/idp/framework/infrastructure/messaging/codec/proto
python generate_protos.py
```

## Apache Avro

Apache开发的数据序列化系统，提供:

- 丰富的数据类型支持
- Schema与数据一起存储，便于解析
- 支持Schema演化，实现向前/向后兼容
- 更紧凑的编码

我们的Avro实现位于 `messaging/codec/avro/` 目录。

### 定义消息结构

```json
// message.avsc
{
  "namespace": "idp.messaging",
  "type": "record",
  "name": "MessageEnvelope",
  "fields": [
    {"name": "event_type", "type": "string"},
    {"name": "payload", "type": {"type": "map", "values": "string"}},
    {"name": "occurred_at", "type": "string"},
    {"name": "source", "type": "string"},
    {"name": "correlation_id", "type": "string"}
  ]
}
```

## 使用示例

### 基本使用

```python
from idp.framework.infrastructure.messaging.core.codec import get_codec

# 获取默认编解码器(JSON)
default_codec = get_codec()

# 获取特定编解码器
protobuf_codec = get_codec("protobuf")
avro_codec = get_codec("avro")

# 编码/解码消息
encoded = codec.encode(message_envelope)
decoded = codec.decode(encoded)
```

### 在事件总线中使用

```python
from idp.framework.infrastructure.messaging.pulsar.event_bus import PulsarEventBus

# 创建使用Protobuf编解码器的事件总线
event_bus = PulsarEventBus(codec_name="protobuf")

# 发布事件
await event_bus.publish_event(event_type, payload, source, correlation_id)
```

## 性能对比

我们提供了性能测试工具，可以运行:

```bash
python -m idp.framework.infrastructure.messaging.demo.codec_comparison
```

典型测试结果:

| 编解码器 | 编码时间 | 解码时间 | 数据大小 |
|---------|---------|---------|---------|
| JSON    | 基准值   | 基准值   | 基准值   |
| Protobuf | 1.5x-3x 更快 | 2x-4x 更快 | 减少40-60% |
| Avro    | 1.5x-2.5x 更快 | 2x-3.5x 更快 | 减少35-55% |

## 结论与建议

- **开发/调试环境**: 使用JSON编解码器，便于查看消息内容
- **生产/高性能环境**: 使用Protocol Buffers或Avro
- **需要严格Schema管理**: 优先考虑Avro
- **跨语言服务**: 优先考虑Protocol Buffers 