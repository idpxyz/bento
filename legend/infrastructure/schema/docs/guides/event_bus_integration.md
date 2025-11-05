# 与 Event Bus 集成指南

本文档介绍如何将 Schema 中心与 Event Bus 框架集成，实现基于 Schema 的事件发布和订阅。

## 概述

Schema 中心与 Event Bus 集成的基本流程如下：

1. Schema 中心定义和管理事件结构
2. Schema 中心将 schema 注册到 Schema Registry
3. Schema 中心生成 Pydantic 模型
4. Event Bus 框架使用这些模型处理事件

## 导入 Registry

在 Event Bus 初始化时，您需要导入 Schema Registry：

```python
from idp.framework.event_bus import EventBus
from idp.framework.infrastructure.schema import load_registry

# 加载注册表
registry = load_registry()

# 初始化事件总线，并传入注册表
event_bus = EventBus(registry=registry)
```

## 注册事件处理器

可以使用两种方式注册事件处理器：

### 1. 基于 Schema 名称注册

```python
from idp.framework.event_bus import event_handler

@event_handler(schema="UserRegistered")
async def handle_user_registered(event):
    # event 是一个 UserRegistered Pydantic 模型的实例
    print(f"新用户注册: {event.username}")
    
    # 所有字段都有类型提示和验证
    user_id = event.user_id
    email = event.email
```

### 2. 基于 Pydantic 模型注册

```python
from idp.framework.event_bus import event_handler
from idp.framework.schema.models.user_registered import UserRegistered

@event_handler(model=UserRegistered)
async def handle_user_registered(event: UserRegistered):
    # 显式类型注解提供更好的 IDE 支持
    print(f"新用户注册: {event.username}")
```

## 发布事件

发布事件时，您可以使用 Schema 中心生成的 Pydantic 模型：

```python
from idp.framework.event_bus import publish_event
from idp.framework.schema.models.order_created import OrderCreated, OrderItem, Address

# 创建事件对象
order_event = OrderCreated(
    order_id="ORD-12345",
    customer_id="CUST-789",
    items=[
        OrderItem(
            product_id="PROD-001",
            quantity=2,
            price=99.99
        )
    ],
    total_amount=199.98,
    status="PENDING",
    created_at=datetime.now(),
    shipping_address=Address(
        street="123 Main St",
        city="Beijing",
        state="Beijing",
        zip="100000",
        country="China"
    )
)

# 发布事件
await publish_event(order_event)
```

## 模式验证与错误处理

Pydantic 自动提供了模式验证，无效的事件数据会引发 `ValidationError`：

```python
try:
    # 创建事件，但缺少必要字段
    invalid_event = UserRegistered(
        # 缺少 user_id 字段
        username="john_doe",
        email="john@example.com"
    )
except ValidationError as e:
    print(f"事件验证失败: {e}")
```

## 完整示例

下面是一个完整的集成示例：

```python
from idp.framework.event_bus import EventBus, event_handler, publish_event
from idp.framework.infrastructure.schema import load_registry
from idp.framework.schema.models.user_registered import UserRegistered

# 初始化
registry = load_registry()
event_bus = EventBus(registry=registry)

# 注册处理器
@event_handler(schema="UserRegistered")
async def log_user_registered(event):
    print(f"用户已注册: {event.username}")

@event_handler(schema="OrderCreated")
async def process_order(event):
    print(f"处理订单: {event.order_id}")

# 启动事件总线
await event_bus.start()

# 发布事件
user_event = UserRegistered(
    user_id="123",
    username="zhang_san",
    email="zhang_san@example.com"
)
await publish_event(user_event)

# 关闭事件总线
await event_bus.shutdown()
```

## 进阶主题

### 配置 Schema Registry 连接

如果需要自定义 Schema Registry 的连接信息：

```python
from idp.framework.infrastructure.schema import load_registry

registry = load_registry(
    registry_url="http://schema-registry:8081",
    auth=("username", "password")
)
```

### 手动加载特定 Schema

```python
from idp.framework.infrastructure.schema import load_schema

# 加载特定的 schema
user_schema = load_schema("UserRegistered")
```

### 处理 Schema 版本变更

当 Schema 版本发生变化时，可以设置兼容模式：

```python
@event_handler(
    schema="UserRegistered", 
    compatibility_mode="BACKWARD"  # 支持向后兼容
)
async def handle_user_registered(event):
    # 处理可能包含不同版本字段的事件
    if hasattr(event, "new_field"):
        print(f"New field value: {event.new_field}")
```

## Schema 文档链接

Schema Center 为每个事件 Schema 提供了可跳转的 HTML 文档链接，开发人员可以通过这些链接快速查看事件结构和使用方法。

### 获取文档链接

```python
from idp.framework.infrastructure.schema import get_schema_doc_url

# 获取指定事件的文档 URL
order_created_doc_url = get_schema_doc_url("OrderCreated")
print(f"OrderCreated 事件文档: {order_created_doc_url}")

# 在处理事件时提供文档链接
@event_bus.subscribe("order.created")
async def handle_order_created(event_data):
    try:
        # 处理事件逻辑
        # ...
    except ValidationError as e:
        # 获取文档链接用于错误消息
        doc_url = get_schema_doc_url("OrderCreated")
        logging.error(f"事件验证失败，请参考文档: {doc_url}，错误: {str(e)}")
```

### 在应用中集成文档链接

在开发环境或管理界面中，可以集成 Schema 文档链接，方便开发人员快速访问：

```python
# 获取所有已订阅主题的 Schema 文档链接
from idp.framework.infrastructure.schema import load_registry

def get_all_schema_doc_urls():
    """获取所有 Schema 的文档链接"""
    registry = load_registry()
    doc_urls = {}
    
    for schema in registry.get('schemas', []):
        name = schema.get('name')
        doc_url = schema.get('doc_url')
        if name and doc_url:
            doc_urls[name] = doc_url
    
    return doc_urls

# 在应用启动时收集所有文档链接
schema_docs = get_all_schema_doc_urls()

# 在 API 中提供文档链接
@app.get("/api/schemas/docs")
async def get_schema_docs():
    return schema_docs
```

通过将 Schema 文档链接集成到应用中，开发人员可以随时查阅事件结构，确保事件的正确使用和处理。 