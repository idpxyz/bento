# Bento Contracts - Contract-as-Code

Contract-as-Code 模块，提供声明式的业务契约管理，包括状态机、错误码、事件路由、Schema 验证和 Breaking Change 检测。

## 核心组件

| 组件 | 说明 |
|------|------|
| `StateMachineEngine` | 基于 YAML 定义的状态机验证引擎 |
| `ReasonCodeCatalog` | 错误/原因码目录（JSON） |
| `RoutingMatrix` | 事件路由矩阵（YAML） |
| `EventSchemaRegistry` | 事件 Schema 验证（JSON Schema） |
| `BreakingChangeDetector` | Breaking Change 检测器（P1） |
| `SchemaComparator` | Schema 版本对比工具（P1） |
| `CompatibilityValidator` | 兼容性验证引擎（P1） |
| `ContractLoader` | 统一的契约加载器 |
| `ContractGate` | 启动时契约验证门禁 |

## 契约文件结构

```
contracts/
├── state-machines/
│   ├── order.state-machine.yaml
│   └── shipment.state-machine.yaml
├── reason-codes/
│   └── reason_codes.json
├── routing/
│   └── event_routing_matrix.yaml
└── events/
    └── envelope.schema.json
```

## 应用层初始化

框架只提供机制，应用层控制初始化时机和配置：

```python
# your_app/main.py 或 FastAPI lifespan

from contextlib import asynccontextmanager
from fastapi import FastAPI

from bento.contracts import ContractLoader
from bento.contracts.gates import ContractGate
from bento.core.exceptions import set_global_catalog
from bento.application.decorators import set_global_contracts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - 初始化 contracts"""

    # 1. 验证 contracts（可选，推荐在生产环境启用）
    gate = ContractGate(
        contracts_root="./contracts",
        require_state_machines=True,   # 必须有状态机
        require_reason_codes=True,     # 必须有错误码
    )
    gate.validate()  # 验证失败会抛出 ContractGateError

    # 2. 加载 contracts
    contracts = ContractLoader.load_from_dir("./")

    # 3. 注册全局 catalog（用于 DomainException 自动获取 http_status）
    set_global_catalog(contracts.reason_codes)

    # 4. 注册全局 contracts（用于 @state_transition 装饰器）
    set_global_contracts(contracts)

    # 5. 存储到 app.state 供其他地方使用
    app.state.contracts = contracts

    yield

    # Cleanup（如需要）
    set_global_catalog(None)
    set_global_contracts(None)


app = FastAPI(lifespan=lifespan)
```

## 使用示例

### 1. 状态机验证

```yaml
# contracts/state-machines/order.state-machine.yaml
aggregate: Order
states:
  - DRAFT
  - SUBMITTED
  - COMPLETED
  - CANCELLED
transitions:
  - from: DRAFT
    command: Submit
    to: SUBMITTED
  - from: SUBMITTED
    command: Complete
    to: COMPLETED
  - from: [DRAFT, SUBMITTED]
    command: Cancel
    to: CANCELLED
```

```python
# 方式1：装饰器自动验证
from bento.application.decorators import state_transition, command_handler

@state_transition(aggregate="Order", command="Submit")
@command_handler
class SubmitOrderHandler(CommandHandler[SubmitOrderCommand, Order]):
    async def handle(self, command):
        order = await self.uow.repository(Order).get(command.order_id)
        order.submit()
        return order

# 方式2：手动验证
contracts.state_machines.validate("Order", "DRAFT", "Submit")
```

### 2. 契约驱动的异常

```json
// contracts/reason-codes/reason_codes.json
{
  "reason_codes": [
    {
      "reason_code": "STATE_CONFLICT",
      "message": "Operation not allowed in current state",
      "http_status": 409,
      "category": "DOMAIN",
      "retryable": false
    }
  ]
}
```

```python
from bento.core import DomainException

# 自动从 contracts 获取 http_status 和 message
raise DomainException("STATE_CONFLICT", order_id="123")
# → http_status=409, message="Operation not allowed in current state"
```

### 3. 事件路由

```yaml
# contracts/routing/event_routing_matrix.yaml
routes:
  - event_type: OrderCreated
    topic: order.events
    produced_by: order-service
  - event_type: OrderCompleted
    topic: order.events
```

```python
topic = contracts.routing.topic_for("OrderCreated")  # → "order.events"
```

### 4. Breaking Change 检测 (P1)

检测 Schema 版本之间的不兼容变更，确保 API 演进的安全性。

```python
from bento.contracts import BreakingChangeDetector, CompatibilityValidator

# 定义旧版本和新版本的 Schema
old_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "status": {"type": "string", "enum": ["DRAFT", "ACTIVE"]},
    },
    "required": ["id"],
}

new_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "status": {"type": "string", "enum": ["ACTIVE"]},  # 移除了 DRAFT
    },
    "required": ["id", "status"],  # 新增必需字段
}

# 1. 检测 Breaking Changes
detector = BreakingChangeDetector()
report = detector.detect(old_schema, new_schema, old_version="v1", new_version="v2")

if not report.is_compatible:
    print(f"Breaking changes detected: {len(report.breaking_changes)}")
    for change in report.breaking_changes:
        print(f"  - {change.description}")
        print(f"    Hint: {change.migration_hint}")

# 2. 验证兼容性
validator = CompatibilityValidator()

# 向后兼容性检查（新 Schema 能否接受旧数据）
backward_result = validator.validate_backward_compatible(old_schema, new_schema)
if not backward_result.is_compatible:
    print("Not backward compatible!")
    for issue in backward_result.issues:
        print(f"  - {issue}")

# 向前兼容性检查（旧 Schema 能否接受新数据）
forward_result = validator.validate_forward_compatible(old_schema, new_schema)

# 完全兼容性检查（双向兼容）
full_result = validator.validate_full_compatible(old_schema, new_schema)

# 3. 获取迁移指南
migration_path = validator.get_migration_path(old_schema, new_schema)
for step in migration_path:
    print(step)

# 4. 生成兼容性矩阵（多版本）
schemas = {
    "v1": old_schema,
    "v2": new_schema,
    "v3": {...},
}
matrix = validator.get_compatibility_matrix(schemas)
print(matrix)  # {"v1": {"v1": True, "v2": False, ...}, ...}
```

#### Breaking Change 类型

| 类型 | 严重性 | 说明 |
|------|--------|------|
| `PROPERTY_REMOVED` | Critical | 属性被移除 |
| `PROPERTY_TYPE_CHANGED` | Critical | 属性类型改变 |
| `PROPERTY_REQUIRED_CHANGED` | Critical | 属性变为必需 |
| `ENUM_VALUE_REMOVED` | Critical | 枚举值被移除 |
| `MIN_LENGTH_INCREASED` | Major | 最小长度增加 |
| `MAX_LENGTH_DECREASED` | Major | 最大长度减少 |
| `PATTERN_CHANGED` | Major | 正则表达式改变 |
| `ADDITIONAL_PROPERTIES_CHANGED` | Major | 额外属性策略改变 |
| `ENUM_VALUE_ADDED` | Minor | 枚举值添加（兼容） |

### 5. Schema 对比

比较两个 Schema 的差异，获取详细的变更信息。

```python
from bento.contracts import SchemaComparator

comparator = SchemaComparator()

# 比较两个 Schema
diff = comparator.compare(old_schema, new_schema)

print(f"Added keys: {list(diff.added_keys.keys())}")
print(f"Removed keys: {list(diff.removed_keys.keys())}")
print(f"Modified keys: {list(diff.modified_keys.keys())}")

# 比较属性部分
props_diff = comparator.compare_properties(old_schema, new_schema)

# 比较必需字段
required_diff = comparator.compare_required(old_schema, new_schema)
print(f"Newly required: {required_diff['added']}")
print(f"No longer required: {required_diff['removed']}")

# 获取特定属性的差异
prop_diff = comparator.get_property_diff(old_schema, new_schema, "status")
if prop_diff:
    old_value, new_value = prop_diff
    print(f"status changed from {old_value} to {new_value}")

# 获取变更摘要
summary = comparator.get_summary(old_schema, new_schema)
print(f"Total changes: {summary['total_changes']}")
print(f"Property changes: {summary['property_changes']}")
```

## CLI 工具

```bash
# 验证 contracts
bento contracts validate ./contracts
bento contracts validate ./contracts --require-state-machines

# 列出 contracts
bento contracts list ./contracts
bento contracts list ./contracts --type state-machines
bento contracts list ./contracts --type reason-codes
```

### 6. Mock 数据生成 (P2)

从 Schema 生成测试数据，用于单元测试和开发。

```python
from bento.contracts import MockGenerator

schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "age": {"type": "integer", "minimum": 0, "maximum": 150},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "name"],
}

# 生成单个 Mock 对象
generator = MockGenerator()
mock_data = generator.generate(schema)
# → {"id": "abc123", "name": "John Doe", "email": "john@example.com", ...}

# 生成多个 Mock 对象
mocks = generator.generate_batch(schema, count=10)

# 使用种子保证可重复性
generator = MockGenerator(seed=42)
mock_data = generator.generate(schema)
```

**支持的格式**:
- `format: "email"` → `user@example.com`
- `format: "uuid"` → UUID 字符串
- `format: "date"` → ISO 日期
- `format: "date-time"` → ISO 日期时间
- `format: "uri"` → URL
- `format: "ipv4"` → IPv4 地址
- `format: "ipv6"` → IPv6 地址

### 7. SDK 代码生成 (P2)

为 Python 生成类型安全的 SDK 代码。

```python
from bento.contracts import SDKGenerator

schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "email": {"type": "string"},
    },
    "required": ["id", "name"],
}

generator = SDKGenerator()

# 生成单个 Dataclass
code = generator.generate_dataclass("User", schema)
print(code)
# → @dataclass
#   class User:
#       id: str
#       name: str
#       email: Optional[str] = None
#       def to_dict(self) -> Dict[str, Any]: ...
#       @classmethod
#       def from_dict(cls, data: Dict[str, Any]) -> 'User': ...

# 生成完整模块
schemas = {
    "User": {...},
    "Post": {...},
}
module_code = generator.generate_module("models", schemas)

# 生成 HTTP 客户端
endpoints = {
    "getUser": {
        "method": "GET",
        "path": "/users/{id}",
    },
    "createUser": {
        "method": "POST",
        "path": "/users",
    },
}
client_code = generator.generate_client(
    "UserClient",
    "https://api.example.com",
    endpoints,
)
```

### 8. OpenAPI 文档生成 (P2)

从 Schema 生成 OpenAPI 3.0 规范。

```python
from bento.contracts import OpenAPIGenerator

schemas = {
    "User": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
        },
        "required": ["id"],
    }
}

endpoints = {
    "getUser": {
        "method": "GET",
        "path": "/users/{id}",
        "description": "Get user by ID",
        "response": schemas["User"],
    },
    "createUser": {
        "method": "POST",
        "path": "/users",
        "description": "Create new user",
        "request": schemas["User"],
        "response": schemas["User"],
    },
}

generator = OpenAPIGenerator()

# 生成 OpenAPI 规范（JSON）
spec = generator.generate(
    title="User API",
    version="1.0.0",
    schemas=schemas,
    endpoints=endpoints,
    base_path="/api/v1",
)

# 生成 YAML 格式
yaml_spec = generator.generate_yaml(
    title="User API",
    version="1.0.0",
    schemas=schemas,
    endpoints=endpoints,
)

# 导出到文件
import json
with open("openapi.json", "w") as f:
    json.dump(spec, f, indent=2)
```

## 最佳实践

### 1. Breaking Change 检测工作流

在 CI/CD 流程中集成 Breaking Change 检测：

```python
# scripts/check_schema_compatibility.py
import sys
from pathlib import Path
from bento.contracts import BreakingChangeDetector, CompatibilityValidator

def check_schema_changes(old_version: str, new_version: str) -> bool:
    """检查 Schema 兼容性，返回是否通过检查"""
    detector = BreakingChangeDetector()
    validator = CompatibilityValidator()

    old_schema = load_schema(old_version)
    new_schema = load_schema(new_version)

    # 检测 breaking changes
    report = detector.detect(old_schema, new_schema, old_version, new_version)

    if not report.is_compatible:
        print(f"❌ Breaking changes detected!")
        for change in report.breaking_changes:
            print(f"  - {change}")
        return False

    # 检查向后兼容性
    result = validator.validate_backward_compatible(old_schema, new_schema)
    if not result.is_compatible:
        print(f"❌ Not backward compatible!")
        for issue in result.issues:
            print(f"  - {issue}")
        return False

    print(f"✅ Schema changes are compatible")
    return True

if __name__ == "__main__":
    if not check_schema_changes("v1", "v2"):
        sys.exit(1)
```

### 2. 版本管理策略

```
contracts/events/
├── OrderCreated.v1.schema.json      # 当前版本
├── OrderCreated.v1.1.schema.json    # 补丁版本（兼容）
├── OrderCreated.v2.schema.json      # 主版本（可能不兼容）
└── OrderCreated.deprecated.v1.schema.json  # 已弃用版本
```

### 3. 兼容性矩阵

维护兼容性矩阵，记录各版本之间的兼容关系：

```python
# contracts/compatibility-matrix.json
{
  "OrderCreated": {
    "v1": {
      "v1": true,
      "v1.1": true,    # 向后兼容
      "v2": false      # 不兼容
    },
    "v1.1": {
      "v1": false,     # 向前不兼容（v1 不能接受 v1.1 的数据）
      "v1.1": true,
      "v2": false
    },
    "v2": {
      "v1": false,
      "v1.1": false,
      "v2": true
    }
  }
}
```

### 4. 迁移指南

为每个不兼容的版本变更提供迁移指南：

```yaml
# contracts/migration-guides/OrderCreated-v1-to-v2.md
# 从 v1 升级到 v2 的迁移指南

## Breaking Changes

1. **属性移除**: `legacy_field` 已移除
   - 迁移: 使用 `new_field` 替代

2. **枚举值移除**: `status` 枚举中移除了 `DRAFT`
   - 迁移: 使用 `PENDING` 替代

## 迁移步骤

1. 更新所有生产者停止发送 `legacy_field`
2. 更新所有消费者处理 `new_field`
3. 部署新版本消费者
4. 部署新版本生产者
5. 监控兼容性问题
```

## 架构原则

1. **框架提供机制** - 加载、验证、装饰器、Breaking Change 检测
2. **应用控制策略** - 何时加载、如何配置、版本管理
3. **契约即代码** - 版本控制、CI 门禁、自动化检测
4. **声明式优先** - YAML/JSON 定义，代码验证
5. **安全演进** - 强制兼容性检查，防止破坏性变更

## P1 & P2 完成情况

✅ **Breaking Change 检测** (P1 - 强烈建议)
- ✅ BreakingChangeDetector - 检测 Schema 版本间的不兼容变更
- ✅ SchemaComparator - 详细的 Schema 对比工具
- ✅ CompatibilityValidator - 向后/向前/完全兼容性验证
- ✅ 完整的单元测试覆盖
- ✅ 详细的使用文档和最佳实践

✅ **Mock / SDK / Generator** (P2 - 可选)
- ✅ MockGenerator - 从 Schema 生成测试数据
- ✅ SDKGenerator - 生成 Python SDK 代码（Dataclass + HTTP Client）
- ✅ OpenAPIGenerator - 生成 OpenAPI 3.0 规范
- ✅ 完整的单元测试覆盖
- ✅ 详细的使用文档和最佳实践

### 核心能力

| 能力 | 状态 | 说明 |
|------|------|------|
| Breaking Change 检测 | ✅ | 自动检测 14 种不兼容变更 |
| 兼容性验证 | ✅ | 向后/向前/完全兼容性检查 |
| Schema 对比 | ✅ | 详细的差异分析 |
| 迁移指南 | ✅ | 自动生成迁移步骤 |
| 兼容性矩阵 | ✅ | 多版本兼容性分析 |
| 严重性分级 | ✅ | Critical/Major/Minor 分级 |
| Mock 数据生成 | ✅ | 支持 7+ 种格式 |
| SDK 代码生成 | ✅ | Dataclass + HTTP Client |
| OpenAPI 生成 | ✅ | OpenAPI 3.0 规范 |

### 使用场景

**P1 - Breaking Change 检测**:
1. **API 版本演进** - 检测 API Schema 变更的兼容性
2. **事件演进** - 验证事件 Schema 的向后兼容性
3. **数据迁移** - 检查数据模型版本升级的影响
4. **CI/CD 集成** - 在部署前自动检查兼容性
5. **文档生成** - 自动生成版本变更和迁移指南

**P2 - Mock / SDK / Generator**:
1. **单元测试** - 生成 Mock 数据进行测试
2. **客户端开发** - 生成类型安全的 SDK 代码
3. **API 文档** - 自动生成 OpenAPI 规范
4. **开发体验** - 加速客户端和测试开发
