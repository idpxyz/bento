# IDP Schema Center

Schema Center 是 IDP 框架的一部分，提供对事件模式（Schema）的管理、生成和验证功能。它支持多种格式的 Schema 定义，包括 Protocol Buffers、Avro 和 JSON Schema，并提供统一的编译、注册和使用接口。

## 主要功能

- **Schema 注册表**：维护事件定义及其元数据
- **Schema 编译**：自动编译 Schema 为不同语言代码
- **Pydantic 模型生成**：从 Schema 自动生成 Pydantic 数据模型
- **文档生成**：自动为 Schema 生成文档
- **版本控制**：管理 Schema 版本演进
- **兼容性检查**：验证 Schema 版本之间的兼容性
- **与 Event Bus 集成**：提供与事件总线的无缝集成

## 目录结构

```
schema/
├── avro/                  # Avro Schema 定义文件
│   └── product_updated.avsc
├── proto/                 # Protocol Buffers 定义文件
│   └── order_created.proto
├── json/                  # JSON Schema 定义文件
│   └── user_activity.json
├── docs/                  # 文档
│   ├── guides/            # 使用指南
│   │   └── event_bus_integration.md
├── cli/                   # CLI 工具
│   ├── generators/        # 代码生成器
│   │   ├── __init__.py
│   │   ├── proto_generator.py
│   │   ├── avro_generator.py
│   │   └── json_generator.py
│   └── schemactl.py       # 命令行工具
├── tests/                 # 测试
│   ├── test_compatibility.py
│   └── test_version_control.py
├── registry.yml           # Schema 注册表配置
├── README.md              # 项目说明
└── __init__.py            # 模块入口
```

## 使用说明

### 1. 创建新的 Schema

使用 `schemactl` 命令行工具创建新的 Schema：

```bash
python -m idp.framework.infrastructure.schema.cli.schemactl create --name OrderCreated --format proto --desc "订单创建事件"
```

或使用 Makefile：

```bash
make create NAME=OrderCreated FORMAT=proto DESC="订单创建事件"
```

### 2. 编译 Schema

编译所有已注册的 Schema：

```bash
make build
```

### 3. 生成 Pydantic 模型

从 Schema 生成 Pydantic 模型：

```bash
make generate
```

### 4. 注册到 Schema Registry

将 Schema 注册到 Pulsar Schema Registry：

```bash
export PULSAR_ADMIN_URL="http://localhost:8080"
make register
```

### 5. 生成文档

生成 Schema 文档：

```bash
make docs
```

### 6. 查看文档

启动本地文档服务器：

```bash
make serve-docs
```

## 版本控制与兼容性

### 创建新版本

当需要更新 Schema 定义时，可以创建新版本而不影响现有使用者：

```bash
make version-new NAME=OrderCreated VERSION=2
```

这将复制现有 Schema 并创建新版本，同时在注册表中添加版本信息。

### 列出版本

查看 Schema 的所有版本：

```bash
make version-list NAME=OrderCreated
```

### 验证兼容性

在发布新版本前验证兼容性，以确保不会破坏现有应用：

```bash
make verify-compatibility NAME=OrderCreated VERSION=2 MODE=BACKWARD
```

支持的兼容性模式:
- `BACKWARD` - 新版本可以读取旧版本数据 (默认)
- `FORWARD` - 旧版本可以读取新版本数据
- `FULL` - 完全兼容 (BACKWARD + FORWARD)
- `NONE` - 不要求兼容性

## 在应用程序中使用

### 加载 Schema 注册表

```python
from idp.framework.infrastructure.schema import load_registry

# 加载注册表
registry = load_registry()
```

### 获取特定 Schema

```python
from idp.framework.infrastructure.schema import load_schema

# 加载特定 Schema
order_created_schema = load_schema("OrderCreated")

# 加载特定版本的 Schema
order_created_v2_schema = load_schema("OrderCreatedV2")
```

### 使用生成的 Pydantic 模型

```python
from idp.framework.infrastructure.schema.generated.models import OrderCreated

# 创建事件对象
event = OrderCreated(
    order_id="ORD-12345",
    customer_id="CUST-789",
    items=[
        {
            "product_id": "PROD-001",
            "product_name": "商品1",
            "quantity": 2,
            "unit_price": 29.99,
            "subtotal": 59.98
        }
    ],
    total_amount=59.98,
    currency="CNY",
    status="created",
    created_at="2023-10-15T12:30:45Z"
)
```

### 处理不同版本

```python
from idp.framework.infrastructure.schema.generated.models import OrderCreated, OrderCreatedV2

# 根据消息来源选择适当的版本
def process_order_event(message, version=None):
    if version == "2":
        event = OrderCreatedV2.model_validate_json(message)
    else:
        event = OrderCreated.model_validate_json(message)
    
    # 处理事件...
    process_order(event)
```

### 与 Event Bus 集成

关于与 Event Bus 集成的详细信息，请参见 [Event Bus 集成指南](docs/guides/event_bus_integration.md)。

## 配置 Schema Registry

编辑 `registry.yml` 文件配置 Schema 注册表：

```yaml
options:
  default_namespace: "idp/framework"
  models_output_path: "generated/models"
  proto_output_path: "generated/proto"
  docs_output_path: "docs/schemas"

schemas:
  - name: "OrderCreated"
    format: "proto"
    file: "proto/order_created.proto"
    topic: "persistent://idp/framework/order.created"
    description: "订单创建事件"
    package: "events"
    message: "OrderCreated"
```

## 依赖项

- Python 3.8+
- Protocol Buffers 编译器 (`protoc`)
- Pydantic v2
- PyYAML
- Requests (用于 Schema Registry 交互)
- pytest, pytest-asyncio (用于测试)

## 贡献指南

1. 将 Schema 定义添加到相应目录 (`proto/`, `avro/`, `json/`)
2. 更新 `registry.yml` 添加 Schema 元信息
3. 运行命令生成代码和文档
4. 确保兼容性测试通过
5. 提交 PR

### 后续步骤

这个实现已经满足了基本需求，但您仍可以进一步扩展：

1. **缓存机制**：为注册表和 Schema 加载添加缓存，提高性能
2. **版本控制**：增强对 Schema 版本的支持和管理  - ✅
3. **兼容性检查**：添加 Schema 兼容性检查逻辑 - ✅
4. **更多集成**：添加与其他系统的集成，如 Kafka Schema Registry
5. **单元测试**：为各个组件添加全面的单元测试
6. **集成Event Bus**：添加与Event Bus的集成从 schema-center/registry.yaml 加载 schema 注册信息并动态 import 模型

这个 Schema Center 为您的事件驱动架构提供了坚实的基础，使您可以更容易地管理、版本化和使用不同格式的事件 Schema，同时与 Event Bus 无缝集成。通过生成一致的 Pydantic 模型，使得开发者可以在有类型提示的环境中更高效地工作。


**明确 `schema-center` 和 `event-bus` 在目录结构和架构分层中的角色**，构建协同闭环。

---

## 🧱 1. DDD 分层架构视角：定位两个模块的职责

| 层级 | 模块名称 | 职责 | 示例 |
|------|----------|------|------|
| **用户接口层** | API, CLI, 文档前端 | 操作、查看 schema；触发注册、生成文档 | MkDocs UI, CLI 工具 |
| **应用层** | schema-center CLI 工具 | 管理 schema 生命周期、格式校验、生成代码 | `schemactl.py`, `make` |
| **领域层** | schema 实际定义（领域事件） | `.proto`, `.avsc`, `.json` 表示领域事件结构 | `UserRegistered`, `OrderCreated` |
| **基础设施层** | event-bus runtime 框架 | 负责消费消息、分发 handler、异常补偿 | `event_bus.py`, `subscriber.py` |

---
---

## 🔄 2. 构建协同闭环系统（schema-center + event-bus）

| 模块 | 具体功能 | 责任归属 |
|------|----------|----------|
| `registry.yaml` | 统一事件定义元信息 | schema-center |
| `pydantic.BaseModel` 生成器 | 自动生成事件类 | schema-center |
| handler 注册器（按事件名） | 绑定事件处理器 + 类型校验 | event-bus |
| schema auto-subscription | 根据 registry.yaml 订阅 topic | event-bus |
| 事件文档生成 + serve-docs | 文档服务化 | schema-center |
| 消息模拟器 + 预消费测试 | 模拟发送事件 + handler dry-run | 双方协作 |

---

## ✅ 接下来建议步骤：

1. `schema-center`：
   - 📦 添加 `generate_models.py` → 输出 `.py` Pydantic 模型
   - 📚 输出文档链接给订阅者（docs.schema-center.io）

2. `event-bus`：
   - 🧠 支持 `load_registry()` 订阅所有有效 schema
   - ✅ handler 层使用 `@event_handler(schema="UserRegistered")` 自动绑定

3. 提供 CI 工具：
   - ✅ schema 变更检测 + handler 存在性验证

---

是否需要我帮你：

- 先生成 `generate_models.py` 实现（将 `.proto/.avsc/.json` → Pydantic 类）？
- 或者生成一个 handler 与 schema 绑定的桥接代码样板？

我们可以进一步构建**"Schema 驱动型微服务平台"** ✨ 要继续吗？

## 文档查看

Schema Center 为每个事件 Schema 提供了可跳转的 HTML 文档。您可以通过以下方式访问这些文档：

### 生成并查看文档

```bash
# 生成 Schema 文档（包括 Markdown 和 HTML）
make docs

# 启动本地文档服务器
make serve-docs
```

启动文档服务器后，访问 http://localhost:8000 即可浏览所有 Schema 文档。

### 在代码中获取文档链接

```python
from idp.framework.infrastructure.schema import get_schema_doc_url

# 获取特定 Schema 的文档链接
doc_url = get_schema_doc_url("OrderCreated")
print(f"查看文档: {doc_url}")
```

### 将文档部署到自定义位置

如果需要将文档部署到自定义 URL，可以在注册表配置中设置 `docs_base_url` 选项：

```json
{
  "options": {
    "docs_base_url": "https://example.com/schema-docs/",
    "docs_output_path": "docs/schemas"
  },
  "schemas": [
    ...
  ]
}
```

更多文档使用示例，请参考 [事件总线集成指南](docs/guides/event_bus_integration.md)。