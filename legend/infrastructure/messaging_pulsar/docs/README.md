# 📡 IDP消息系统 (Messaging Framework)

## 🧭 简介

IDP消息系统是一个基于 Apache Pulsar 构建的**异步消息与事件驱动框架**，面向企业级系统，支持多种序列化格式(JSON/Protobuf/Avro)，具备以下特性：

- ✅ 可插拔中间件（默认 Pulsar）
- ✅ 领域无关的 `MessageBus` 与 `EventBus` 抽象
- ✅ 支持装饰器注册的事件处理机制
- ✅ 内建可观测性（Trace / Metrics / Error Hooks）
- ✅ 自动 DLQ 支持与失败补偿工具
- ✅ 多格式编解码支持 (JSON/Protobuf/Avro)

## 📁 目录结构说明

```bash
messaging/
├── README.md                        # 主README文件
├── init.py                          # 初始化模块
├── install_codecs.py                # 安装编解码器依赖和生成代码脚本
├── requirements-codec.txt           # 编解码器依赖
│
├── core/                            # 📌 抽象接口层
│   ├── base_message.py              # 标准消息结构 MessageEnvelope
│   ├── codec.py                     # 编解码器抽象接口和注册表
│   ├── message_bus.py               # 抽象消息总线接口 AbstractMessageBus
│   └── event_bus.py                 # 抽象事件总线接口 AbstractEventBus
│
├── codec/                           # 🔄 消息编解码实现
│   ├── __init__.py                  # 自动导入所有编解码器
│   ├── json.py                      # JSON编解码器实现
│   ├── protobuf.py                  # Protocol Buffers编解码器实现
│   ├── avro.py                      # Avro编解码器实现
│   ├── proto/                       # Protocol Buffers定义和生成文件
│   │   ├── message.proto            # Protobuf消息定义
│   │   └── generate_protos.py       # 代码生成脚本
│   └── avro/                        # Avro定义文件
│       └── message.avsc             # Avro消息定义
│
├── pulsar/                          # 🔌 Pulsar 实现模块
│   ├── client.py                    # Pulsar 客户端封装
│   ├── config.py                    # Pulsar 配置
│   └── event_bus.py                 # PulsarEventBus 实现
│
├── dispatcher/                      # ⚙️ 事件注册 & 分发
│   ├── registry.py                  # 事件处理器注册中心
│   ├── decorator.py                 # 装饰器 @event_handler
│   └── subscriber_runner.py         # 启动订阅任务
│
├── event/                           # 📣 事件定义
│   ├── registry.py                  # 事件注册
│   └── user_event.py                # 用户相关事件示例
│
├── observability/                   # 🔍 可观测性模块
│   └── hook.py                      # 可观测性钩子
│
├── dlq/                             # ❌ Dead Letter Queue 支持
│   └── handler.py                   # DLQ处理
│
└── demo/                            # 🎮 示例代码
    ├── codec_comparison.py          # 编解码器性能对比
    └── event_bus_demo.py            # 事件总线示例
```

## ✨ 功能总览

| 模块 | 功能点 |
|------|--------|
| `core/` | 定义标准消息结构和接口，便于扩展中间件 |
| `codec/` | 提供多种序列化支持（JSON/Protocol Buffers/Avro） |
| `pulsar/` | 封装 Pulsar client，连接配置，事件总线实现 |
| `dispatcher/` | 提供自动注册与调度事件处理函数的能力 |
| `event/` | 定义和管理领域事件 |
| `observability/` | 提供埋点、异常上报、耗时记录 |
| `dlq/` | 消费失败自动进入死信队列 + 错误处理 |
| `demo/` | 示例代码和性能基准测试 |

## 🚀 安装

安装基本依赖和编解码器支持:

```bash
# 安装基本依赖
pip install -r requirements.txt

# 安装编解码器依赖并生成代码
python install_codecs.py
```

## ✅ 使用方式

### 1. 发布事件

```python
from idp.framework.infrastructure.messaging.pulsar.event_bus import PulsarEventBus

# 创建事件总线 (默认使用JSON编解码器)
event_bus = PulsarEventBus()

# 或使用高性能编解码器
# event_bus = PulsarEventBus(codec_name="protobuf")  # 使用Protocol Buffers
# event_bus = PulsarEventBus(codec_name="avro")      # 使用Avro

# 发布事件
await event_bus.publish_event(
    event_type="user.registered",
    payload={"user_id": "123", "email": "user@example.com"},
    source="user-service",
    correlation_id="req-abc-123"
)
```

### 2. 注册事件处理器

```python
from idp.framework.infrastructure.messaging.dispatcher.decorator import event_handler
from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope

@event_handler("user.registered")
async def handle_user_registered(message: MessageEnvelope):
    print(f"用户注册成功: {message.payload['email']}")
    # 处理用户注册事件...
```

### 3. 启动订阅器

```python
from idp.framework.infrastructure.messaging.init import init_messaging

# 在应用启动时初始化消息系统
# 比如在FastAPI应用中:
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化消息系统
    await init_messaging()
    yield
    # 应用关闭时可以添加清理代码

app = FastAPI(lifespan=lifespan)
```

## 🔄 多编解码格式支持

消息系统支持以下编解码格式:

| 格式 | 特点 | 推荐场景 |
|-----|-----|---------|
| JSON | 人类可读，便于调试 | 开发/测试环境 |
| Protocol Buffers | 高性能，紧凑 | 生产环境，跨语言服务 |
| Avro | 支持Schema演化 | 需要严格Schema管理的场景 |

性能对比:

| 编解码器 | 编码时间 | 解码时间 | 数据大小 |
|---------|---------|---------|---------|
| JSON    | 基准值   | 基准值   | 基准值   |
| Protobuf | 1.5x-3x 更快 | 2x-4x 更快 | 减少40-60% |
| Avro    | 1.5x-2.5x 更快 | 2x-3.5x 更快 | 减少35-55% |

您可以运行性能测试脚本:

```bash
python -m idp.framework.infrastructure.messaging.demo.codec_comparison
```

## 🔍 可观测性

系统内置可观测性钩子，记录事件处理情况:

```python
from idp.framework.infrastructure.messaging.observability.hook import set_observer

def custom_observer(event_type, correlation_id, success, duration, error):
    print(f"[Event] {event_type}, trace={correlation_id}, success={success}, time={duration:.2f}s")
    if not success:
        print(f"[Error] {error}")

# 注册自定义观察器
set_observer(custom_observer)
```

## ⚠️ 错误处理和DLQ

事件处理失败会:

1. 记录到可观测性系统
2. 写入死信队列 (DLQ)
3. 可以定制重试策略

## 🧩 扩展开发

### 1. 添加新的编解码器

```python
from idp.framework.infrastructure.messaging.core.codec import MessageCodec, register_codec
from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope

class MyCustomCodec(MessageCodec):
    def encode(self, envelope: MessageEnvelope) -> bytes:
        # 实现编码逻辑
        ...
        
    def decode(self, raw: bytes) -> MessageEnvelope:
        # 实现解码逻辑
        ...

# 注册到全局注册表
register_codec("my-format", MyCustomCodec())
```

### 2. 实现新的消息总线

```python
from idp.framework.infrastructure.messaging.core.message_bus import AbstractMessageBus

class MyCustomMessageBus(AbstractMessageBus):
    # 实现抽象方法
    async def publish(self, topic: str, message: MessageEnvelope) -> None:
        ...

    async def subscribe(self, topic: str, handler: callable) -> None:
        ...
```

## 📝 示例程序

查看 `demo/` 目录下的示例程序:

- `event_bus_demo.py`: 演示如何使用事件总线发布和订阅事件
- `codec_comparison.py`: 比较不同编解码器的性能

## 📚 详细文档

详细文档请参考:

- [编解码器系统](codecs.md)
- [事件处理](event_handling.md)
- [错误处理策略](error_handling.md)
- [可观测性](observability.md)

## 🔮 未来计划

- [ ] 支持Kafka/RabbitMQ实现
- [ ] 添加更多编解码格式支持(MessagePack, BSON等)
- [ ] 添加事件模式验证
- [ ] 添加架构演化支持
- [ ] 添加可视化监控面板