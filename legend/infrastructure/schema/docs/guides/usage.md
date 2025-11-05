# Schema Center 使用指南

<div align="center">
  <h3>规范化的事件模式管理与代码生成工具</h3>
  <p>简化数据流转，保障各系统间信息交换的一致性与可靠性</p>
</div>

## 📋 目录

- [简介](#简介)
- [快速开始](#快速开始)
- [核心功能](#核心功能)
  - [Schema 定义与管理](#schema-定义与管理)
  - [模型代码生成](#模型代码生成)
  - [Schema 版本控制](#schema-版本控制)
  - [兼容性验证](#兼容性验证)
- [开发工作流](#开发工作流)
- [API 参考](#api-参考)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

## 简介

Schema Center 是一个强大的事件模式管理框架，为事件驱动架构提供核心支持。它允许开发团队集中定义、管理和演进数据模式，确保跨系统通信的一致性和可靠性。

主要特性：

- **多格式支持**：原生支持 Protocol Buffers、Avro 和 JSON Schema
- **代码生成**：自动将 Schema 转换为可直接使用的 Pydantic 模型
- **版本控制**：内置 Schema 版本管理机制
- **兼容性检查**：确保不同版本 Schema 间的兼容性
- **文档生成**：自动生成可视化文档

## 快速开始

### 安装依赖

确保已安装所有必要依赖：

```bash
pip install pydantic avro-python3 protobuf jsonschema
```

### 创建第一个 Schema

```bash
# 创建一个基于 Protocol Buffers 的事件 Schema
make create NAME=OrderCreated FORMAT=proto DESC="订单创建事件"

# 编辑 Schema 定义
vim schemas/ordercreated/order_created.proto
```

示例 Proto 文件内容：

```protobuf
syntax = "proto3";

package ecommerce;

import "google/protobuf/timestamp.proto";

// 订单创建事件
message OrderCreated {
    string order_id = 1;                        // 订单ID
    string customer_id = 2;                     // 客户ID
    repeated OrderItem items = 3;               // 订单项目
    double total_amount = 4;                    // 总金额
    string currency = 5;                        // 货币代码
    string status = 6;                          // 订单状态 选项: "pending", "paid", "cancelled"
    google.protobuf.Timestamp created_at = 7;   // 创建时间
}

// 订单项目
message OrderItem {
    string product_id = 1;                      // 产品ID
    string product_name = 2;                    // 产品名称
    int32 quantity = 3;                         // 数量
    double unit_price = 4;                      // 单价
    double subtotal = 5;                        // 小计
}
```

### 生成 Pydantic 模型

```bash
# 生成特定 Schema 的 Pydantic 模型
make generate NAME=OrderCreated

# 或生成所有 Schema 的模型
make generate
```

### 在应用中使用生成的模型

```python
from datetime import datetime
from src.idp.framework.infrastructure.schema.generated.models.ordercreated import OrderCreated, OrderItem

# 创建订单项目
items = [
    OrderItem(
        product_id="PROD-123",
        product_name="智能手机",
        quantity=1,
        unit_price=999.99,
        subtotal=999.99
    ),
    OrderItem(
        product_id="PROD-456",
        product_name="保护壳",
        quantity=2,
        unit_price=29.99,
        subtotal=59.98
    )
]

# 创建订单事件
order = OrderCreated(
    order_id="ORD-789",
    customer_id="CUST-123",
    items=items,
    total_amount=1059.97,
    currency="CNY",
    status="paid",
    created_at=datetime.now()
)

# 序列化为 JSON
order_json = order.model_dump_json()
print(order_json)

# 反序列化
received_order = OrderCreated.model_validate_json(order_json)
```

## 核心功能

### Schema 定义与管理

Schema Center 支持三种主流数据模式格式：

#### Protocol Buffers

适用于需要高性能序列化和严格类型定义的场景。

```bash
make create NAME=UserRegistered FORMAT=proto DESC="用户注册事件"
```

#### Apache Avro

适用于复杂数据结构和兼容性要求高的场景。

```bash
make create NAME=ProductInventory FORMAT=avro DESC="产品库存事件"
```

#### JSON Schema

适用于与 Web API 集成和验证 JSON 数据的场景。

```bash
make create NAME=UserActivity FORMAT=json DESC="用户活动事件"
```

### 模型代码生成

自动生成对应的 Pydantic 模型，利用 Python 类型系统进行验证和序列化。

```bash
# 生成单个 Schema 的模型
make generate NAME=OrderCreated

# 生成全部模型
make generate

# 使用生成的模型进行验证和序列化
from src.idp.framework.infrastructure.schema.generated.models.ordercreated import OrderCreated

# 从数据创建模型（自动验证）
order = OrderCreated(**data)

# 序列化为 JSON
json_data = order.model_dump_json()

# 或转换为字典
dict_data = order.model_dump()
```

### Schema 版本控制

管理 Schema 的演进，允许多个版本并存。

```bash
# 创建 Schema 的新版本
make version-new NAME=OrderCreated VERSION=2

# 列出特定 Schema 的所有版本
make version-list NAME=OrderCreated
```

### 兼容性验证

确保 Schema 变更不会破坏现有系统。

```bash
# 验证向后兼容性（新版本可读取旧数据）
make verify-compatibility NAME=OrderCreated VERSION=2 MODE=BACKWARD

# 验证向前兼容性（旧版本可读取新数据）
make verify-compatibility NAME=OrderCreated VERSION=2 MODE=FORWARD

# 验证完全兼容性（双向兼容）
make verify-compatibility NAME=OrderCreated VERSION=2 MODE=FULL
```

支持的兼容性模式：

- **BACKWARD**：新版本可以读取旧版本的数据
- **FORWARD**：旧版本可以读取新版本的数据
- **FULL**：完全兼容（同时满足向前和向后兼容）
- **NONE**：不进行兼容性检查

## 开发工作流

使用 Schema Center 的典型开发流程：

1. **定义事件模式**：使用 `make create` 创建新的 Schema 定义
2. **生成模型代码**：使用 `make generate` 生成 Pydantic 模型
3. **在应用中使用**：导入生成的模型用于数据验证和序列化
4. **演进 Schema**：使用 `make version-new` 创建新版本
5. **验证兼容性**：使用 `make verify-compatibility` 确保兼容性
6. **生成新版本模型**：使用 `make generate` 更新模型代码

## API 参考

### 核心 API 函数

```python
from src.idp.framework.infrastructure.schema import load_schema, load_registry, get_schema_topic

# 加载 Schema 注册表
registry = load_registry()

# 加载特定 Schema 定义
order_schema = load_schema("OrderCreated")
# 加载特定版本的 Schema
order_schema_v2 = load_schema("OrderCreated", version=2)

# 获取 Schema 对应的主题
topic = get_schema_topic("OrderCreated")
```

### 在事件总线中集成

发布事件：

```python
from src.idp.framework.infrastructure.schema.generated.models.ordercreated import OrderCreated

def publish_order_created(order_data):
    # 创建并验证模型
    order = OrderCreated(**order_data)
    
    # 发布到事件总线
    event_bus.publish(
        topic="order.created",
        payload=order.model_dump_json(),
        schema_name="OrderCreated"
    )
```

消费事件：

```python
@event_bus.subscribe(topic="order.created", schema="OrderCreated")
async def handle_order_created(event_data):
    # 验证并转换为模型
    order = OrderCreated.model_validate_json(event_data)
    
    # 处理订单
    await process_order(order)
```

## 最佳实践

### Schema 设计原则

1. **具有描述性的命名**：使用清晰、描述性的名称命名 Schema 和字段
2. **添加详细注释**：为每个字段添加注释，说明其用途和约束
3. **保持向后兼容**：添加新字段时设置合理的默认值，避免删除或重命名已有字段
4. **使用明确的类型**：指定最精确的类型，避免过于宽松的类型定义
5. **分版本演进**：通过版本控制机制逐步演进 Schema，而不是直接修改现有版本

### 持续集成建议

将 Schema 验证整合到 CI/CD 流程中：

```yaml
# CI 流程示例
schema-validation:
  stage: validate
  script:
    - make generate
    - python -m unittest discover src/idp/framework/infrastructure/schema/cli/tests
    - make verify-compatibility NAME=OrderCreated VERSION=latest MODE=BACKWARD
```

## 常见问题

### Q: 如何处理 Schema 的循环依赖？

A: 尽量避免在 Schema 设计中创建循环依赖。如果确实需要，可以考虑将相关实体分拆为独立的 Schema，或使用中间层封装复杂关系。

### Q: Schema 应该包含多少字段？

A: 遵循单一责任原则，每个 Schema 应该专注于描述一个清晰的业务事件或实体。通常保持在 10-15 个字段以内为宜，过大的 Schema 应考虑分解。

### Q: 如何处理不同系统使用不同版本的情况？

A: Schema Center 的版本控制机制允许多个版本并存。确保进行兼容性测试，并在系统间协调版本过渡计划。

---

<div align="center">
  <p>
    Schema Center - 为事件驱动架构保驾护航
  </p>
  <p>
    <a href="https://github.com/yourusername/schema-center">GitHub</a> •
    <a href="https://yourdomain.com/docs/schema-center">详细文档</a> •
    <a href="mailto:your-email@example.com">联系支持</a>
  </p>
</div> 