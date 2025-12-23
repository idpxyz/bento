# Bento Contracts - Contract-as-Code

Contract-as-Code 模块，提供声明式的业务契约管理，包括状态机、错误码、事件路由等。

## 核心组件

| 组件 | 说明 |
|------|------|
| `StateMachineEngine` | 基于 YAML 定义的状态机验证引擎 |
| `ReasonCodeCatalog` | 错误/原因码目录（JSON） |
| `RoutingMatrix` | 事件路由矩阵（YAML） |
| `EventSchemaRegistry` | 事件 Schema 验证（JSON Schema） |
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

## 架构原则

1. **框架提供机制** - 加载、验证、装饰器
2. **应用控制策略** - 何时加载、如何配置
3. **契约即代码** - 版本控制、CI 门禁
4. **声明式优先** - YAML/JSON 定义，代码验证
