# IDP 事件 Schema 中心

欢迎使用 IDP 事件 Schema 中心！这里是所有事件定义的权威来源，提供了结构化的事件定义、文档和工具。

## 快速链接

* [📚 详细使用指南](guides/usage.md) - 全面的 Schema Center 使用文档
* [📋 Proto 事件文档](schemas/proto.md) - Protocol Buffers 格式的事件定义
* [📋 Avro 事件文档](schemas/avro.md) - Avro 格式的事件定义
* [📋 JSON 事件文档](schemas/json.md) - JSON Schema 格式的事件定义

## 事件 Schema 概览

事件 Schema 中心提供三种类型的事件格式：

| 格式 | 描述 | 优势 | 适用场景 |
| ---- | ---- | ---- | -------- |
| **Protocol Buffers** | 二进制高效序列化协议 | 体积小、速度快、强类型 | 高性能系统间通信 |
| **Avro** | 二进制数据序列化系统 | Schema 演进、动态类型 | 大数据处理、兼容性要求高 |
| **JSON Schema** | 基于 JSON 的模式语言 | 易读性好、灵活、广泛支持 | REST API、简单集成、调试 |

## 使用指南

### 事件消费者

如果您是事件的消费者，请遵循以下步骤：

1. 浏览[事件文档](schemas/)查找您需要处理的事件
2. 通过 Event Bus 框架注册事件处理器：

```python
from idp.framework.event_bus import event_handler

@event_handler(schema="UserRegistered")
async def handle_user_registered(event):
    # 处理 UserRegistered 事件
    user_id = event.user_id
    print(f"用户注册: {user_id}")
```

### 事件发布者

如果您需要发布事件，请遵循以下步骤：

1. 在项目中引用生成的 Pydantic 模型
2. 创建事件并发布：

```python
from idp.framework.event_bus import publish_event
from idp.framework.schema.models.user_registered import UserRegistered

# 创建事件
event = UserRegistered(
    user_id="123",
    username="zhang_san",
    email="zhang_san@example.com"
)

# 发布事件
await publish_event(event)
```

## 工具使用

使用 `schemactl` 命令行工具管理 Schema：

```bash
# 生成所有
make build

# 注册 schema 到 Pulsar
make register

# 生成文档
make docs

# 启动文档服务
make serve-docs
```

## 接口与集成

Schema 中心提供与 Event Bus 的无缝集成，详情请参考 [Event Bus 集成指南](guides/event_bus_integration.md)。 