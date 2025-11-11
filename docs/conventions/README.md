# Bento 编码规范与约定

本文档定义 Bento DDD 框架的编码规范、命名约定和最佳实践。

## 📋 目录

- [核心原则](#核心原则)
- [分层约定](#分层约定)
- [命名规范](#命名规范)
- [文件组织](#文件组织)
- [DDD 模式约定](#ddd-模式约定)
- [类型注解](#类型注解)
- [错误处理](#错误处理)
- [测试约定](#测试约定)
- [代码风格](#代码风格)

---

## 核心原则

### 1. 清晰边界
✅ **Domain 层必须是纯粹的**
- ❌ 禁止任何 I/O 操作（数据库、文件、网络）
- ❌ 禁止依赖框架（FastAPI, SQLAlchemy 等）
- ✅ 只包含业务逻辑和规则
- ✅ 只依赖 `core` 层

```python
# ❌ 错误示例
class Order(Entity):
    async def save_to_db(self):  # Domain 不应有 I/O
        await db.execute(...)

# ✅ 正确示例
class Order(Entity):
    def apply_discount(self, rate: Decimal) -> Result[None, str]:
        if rate < 0 or rate > 1:
            return Err("Invalid discount rate")
        self.total = self.total * (1 - rate)
        return Ok(None)
```

### 2. 应用层是编排者
- ✅ 协调领域对象
- ✅ 管理事务（UnitOfWork）
- ✅ 调用基础设施（通过端口）
- ❌ 不包含业务逻辑

```python
# ✅ 应用层职责：编排
class CreateOrderUseCase:
    def __init__(self, repo: OrderRepository, uow: UnitOfWork):
        self.repo = repo
        self.uow = uow

    async def __call__(self, inp: CreateOrderInput) -> Result[OrderOutput, str]:
        # 1. 创建聚合（领域逻辑）
        order = Order.create(inp.customer_id, inp.items)

        # 2. 验证业务规则（领域逻辑）
        if not order.validate():
            return Err("Invalid order")

        # 3. 持久化（基础设施）
        async with self.uow:
            await self.repo.save(order)
            await self.uow.commit()

        return Ok(OrderOutput.from_entity(order))
```

### 3. 端口与适配器分离
- ✅ Domain/Application 定义端口（Protocol）
- ✅ Infrastructure 实现适配器
- ✅ 运行时通过依赖注入选择实现

```python
# domain/repository.py - 端口
class OrderRepository(Protocol):
    async def save(self, order: Order) -> None: ...

# persistence/in_memory.py - 适配器1
class InMemoryOrderRepository:
    async def save(self, order: Order) -> None:
        self._storage[order.id.value] = order

# persistence/sqlalchemy/order_repo.py - 适配器2
class SQLAlchemyOrderRepository:
    async def save(self, order: Order) -> None:
        await self.session.execute(...)
```

---

## 分层约定

### 依赖方向（洋葱模型）
```
Interfaces → Infrastructure → Application → Domain → Core
```

**规则**：
- ✅ 外层可以导入内层
- ❌ 内层不能导入外层
- ✅ 使用 `import-linter` 强制执行

### 各层职责速查

| 层级 | 路径 | 可以做 | 不能做 |
|-----|------|--------|--------|
| **Core** | `src/core/` | 通用工具、Result类型 | 依赖任何业务层 |
| **Domain** | `src/domain/` | 业务逻辑、规则 | I/O操作、依赖框架 |
| **Application** | `src/application/` | 用例编排、事务管理 | 直接访问数据库 |
| **Infrastructure** | `src/infrastructure/` | 实现端口、技术细节 | 包含业务逻辑 |
| **Persistence** | `src/persistence/` | 数据持久化 | 业务规则验证 |
| **Messaging** | `src/messaging/` | 事件发布订阅 | 领域逻辑 |
| **Interfaces** | `src/interfaces/` | 协议转换（HTTP/gRPC） | 直接调用Domain |

---

## 命名规范

### 1. 文件命名
- 使用 `snake_case`
- 一个文件一个主要概念

```
✅ order_repository.py
✅ create_order_usecase.py
❌ OrderRepository.py
❌ createOrder.py
```

### 2. 类命名

#### Domain 层
```python
# Entity - 名词
class Order(Entity): ...
class Product(Entity): ...

# ValueObject - 名词 + VO 后缀（可选）
class Money(ValueObject): ...
class Address(ValueObject): ...
class EmailAddress(ValueObject): ...  # 或 Email

# DomainEvent - 过去式 + Event 后缀
class OrderCreatedEvent(DomainEvent): ...
class PaymentProcessedEvent(DomainEvent): ...

# DomainService - 动词 + Service 后缀
class PricingService(DomainService): ...
class InventoryService(DomainService): ...

# Specification - 条件 + Specification 后缀
class HighValueOrderSpecification(Specification[Order]): ...
```

#### Application 层
```python
# UseCase - 动词开头
class CreateOrder(UseCase): ...
class CancelOrder(UseCase): ...
class GetOrderById(UseCase): ...  # 查询

# DTO - 名词 + Input/Output 后缀
@dataclass
class CreateOrderInput: ...

@dataclass
class OrderOutput: ...

# Command/Query（可选，CQRS 风格）
@dataclass
class CreateOrderCommand: ...

@dataclass
class GetOrderQuery: ...
```

#### Infrastructure 层
```python
# Repository 实现 - 技术 + 实体 + Repository
class SQLAlchemyOrderRepository: ...
class InMemoryOrderRepository: ...

# 其他适配器 - 技术 + 功能
class RedisCache: ...
class PulsarEventBus: ...  # 优先使用 Pulsar
class KafkaEventBus: ...   # 可选
class MinIOStorage: ...
```

### 3. 变量命名

```python
# 实体实例 - 小写单数
order = Order.create(...)
customer = await repo.get(customer_id)

# 集合 - 复数
orders = await repo.list()
items = order.items

# 布尔值 - is_/has_/can_ 前缀
is_valid = order.validate()
has_discount = order.discount_rate > 0
can_cancel = order.status == OrderStatus.PENDING

# 常量 - 大写 + 下划线
MAX_ORDER_ITEMS = 100
DEFAULT_CURRENCY = "USD"
```

### 4. 函数/方法命名

```python
# Domain - 业务语言
class Order:
    def apply_discount(self, rate: Decimal) -> None: ...
    def cancel(self, reason: str) -> Result[None, str]: ...
    def add_item(self, product: Product, quantity: int) -> None: ...

# Repository - CRUD 动词
class OrderRepository(Protocol):
    async def get(self, id: EntityId) -> Optional[Order]: ...
    async def save(self, order: Order) -> None: ...
    async def delete(self, id: EntityId) -> None: ...
    async def find_by_customer(self, customer_id: str) -> List[Order]: ...

# UseCase - 业务动作
async def create_order(inp: CreateOrderInput) -> Result[...]: ...
async def process_payment(inp: ProcessPaymentInput) -> Result[...]: ...
```

---

## 文件组织

### 模块结构

#### Domain 模块（按聚合组织）
```
src/domain/
├── __init__.py
├── order/               # 订单聚合
│   ├── __init__.py
│   ├── order.py        # 聚合根
│   ├── order_item.py   # 实体
│   ├── order_status.py # 值对象/枚举
│   ├── events.py       # 领域事件
│   └── repository.py   # 仓储端口
├── product/             # 产品聚合
│   └── ...
└── shared/              # 共享概念
    ├── money.py
    └── address.py
```

#### Application 模块（按用例组织）
```
src/application/
├── order/
│   ├── create_order.py
│   ├── cancel_order.py
│   └── dtos.py
└── payment/
    └── ...
```

### 导入顺序
```python
# 1. 标准库
from datetime import datetime
from typing import Optional, List

# 2. 第三方库
from pydantic import BaseModel

# 3. 本项目 - 按层级从内到外
from bento.core.result import Result, Ok, Err
from bento.domain.order import Order
from bento.application.uow import UnitOfWork

# 4. 本模块相对导入
from .dtos import CreateOrderInput
```

---

## DDD 模式约定

### 1. Entity（实体）

```python
from dataclasses import dataclass
from bento.core.ids import EntityId

@dataclass
class Order(Entity):
    id: EntityId
    customer_id: str
    items: List[OrderItem]
    status: OrderStatus

    @staticmethod
    def create(customer_id: str, items: List[dict]) -> "Order":
        """工厂方法"""
        return Order(
            id=EntityId.generate(),
            customer_id=customer_id,
            items=[OrderItem.from_dict(i) for i in items],
            status=OrderStatus.PENDING,
        )

    def cancel(self, reason: str) -> Result[None, str]:
        """业务方法"""
        if self.status == OrderStatus.COMPLETED:
            return Err("Cannot cancel completed order")
        self.status = OrderStatus.CANCELLED
        return Ok(None)
```

**约定**：
- ✅ 使用 `@dataclass`
- ✅ 提供 `create()` 工厂方法
- ✅ 业务方法返回 `Result` 类型
- ✅ 方法命名使用业务语言（`cancel` 而非 `set_status_cancelled`）

### 2. ValueObject（值对象）

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)  # 不可变
class Money(ValueObject):
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        """验证不变量"""
        require(self.amount >= 0, "Amount must be non-negative")
        require(len(self.currency) == 3, "Invalid currency code")

    def add(self, other: "Money") -> "Money":
        require(self.currency == other.currency, "Currency mismatch")
        return Money(self.amount + other.amount, self.currency)
```

**约定**：
- ✅ 使用 `frozen=True` 确保不可变
- ✅ 在 `__post_init__` 中验证不变量
- ✅ 操作返回新实例而非修改自身

### 3. AggregateRoot（聚合根）

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class Order(AggregateRoot):  # 继承 AggregateRoot
    id: EntityId
    items: List[OrderItem]
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    @staticmethod
    def create(customer_id: str) -> "Order":
        order = Order(id=EntityId.generate(), items=[])
        order.record_event(OrderCreatedEvent(order_id=order.id.value))
        return order

    def add_item(self, product: Product, quantity: int) -> None:
        item = OrderItem(product_id=product.id, quantity=quantity)
        self.items.append(item)
        self.record_event(ItemAddedEvent(order_id=self.id.value, item=item))
```

**约定**：
- ✅ 聚合根保护聚合边界
- ✅ 所有修改通过聚合根方法
- ✅ 状态变化记录领域事件
- ❌ 外部不能直接修改聚合内的实体

### 4. DomainEvent（领域事件）

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    name: str = "order.created"  # 事件名称
    order_id: str
    customer_id: str
    occurred_at: datetime = field(default_factory=now_utc)

    def to_dict(self) -> dict:
        """序列化为字典（用于事件总线）"""
        return asdict(self)
```

**约定**：
- ✅ 不可变（`frozen=True`）
- ✅ 使用过去式命名（`Created`, `Cancelled`）
- ✅ 包含 `occurred_at` 时间戳
- ✅ 提供 `to_dict()` 序列化方法

### 5. Repository（仓储）

```python
# domain/order/repository.py - 端口
from typing import Protocol, Optional, List

class OrderRepository(Protocol):
    async def get(self, id: EntityId) -> Optional[Order]: ...
    async def save(self, order: Order) -> None: ...
    async def find_by_customer(self, customer_id: str) -> List[Order]: ...

# persistence/sqlalchemy/order_repo.py - 适配器
class SQLAlchemyOrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: EntityId) -> Optional[Order]:
        result = await self.session.execute(
            select(OrderModel).where(OrderModel.id == id.value)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    def _to_entity(self, model: OrderModel) -> Order:
        """ORM → Entity 转换"""
        ...
```

**约定**：
- ✅ Domain 定义 Protocol
- ✅ Infrastructure 提供实现
- ✅ 方法返回领域对象（Entity）而非 ORM 模型
- ✅ 提供 `_to_entity()` 和 `_to_model()` 转换方法

---

## 类型注解

### 1. 强制类型注解
所有公共 API 必须有完整的类型注解：

```python
# ✅ 正确
async def create_order(
    customer_id: str,
    items: List[dict],
) -> Result[Order, str]:
    ...

# ❌ 错误（缺少类型）
async def create_order(customer_id, items):
    ...
```

### 2. 使用 Protocol 而非 ABC

```python
# ✅ 推荐 - Protocol
from typing import Protocol

class Repository(Protocol, Generic[T]):
    async def save(self, entity: T) -> None: ...

# ❌ 不推荐 - ABC
from abc import ABC, abstractmethod

class Repository(ABC, Generic[T]):
    @abstractmethod
    async def save(self, entity: T) -> None: ...
```

**原因**：Protocol 支持结构化子类型（duck typing），更灵活。

### 3. 泛型使用

```python
from typing import TypeVar, Generic

T = TypeVar("T")
E = TypeVar("E")

class Result(Generic[T, E]):
    ...

# 使用时指定具体类型
def process() -> Result[Order, str]:
    ...
```

---

## 错误处理

### 1. 使用 Result 类型

```python
from bento.core.result import Result, Ok, Err

# ✅ 领域层/应用层 - 使用 Result
def apply_discount(self, rate: Decimal) -> Result[None, str]:
    if rate < 0 or rate > 1:
        return Err("Discount rate must be between 0 and 1")
    self.discount_rate = rate
    return Ok(None)

# ✅ 调用方处理结果
result = order.apply_discount(0.1)
if result.is_err:
    return Err(result.unwrap_err())
```

### 2. 异常使用场景

```python
# ✅ 系统级错误 - 使用异常
class DatabaseConnectionError(Exception):
    pass

# ✅ 不变量违反 - 使用 Guard
from bento.core.guard import require

def __post_init__(self):
    require(self.amount >= 0, "Amount cannot be negative")

# ❌ 业务规则失败 - 不要用异常
def cancel_order(self):
    if self.status == OrderStatus.COMPLETED:
        raise ValueError("Cannot cancel")  # ❌ 应该用 Result
```

**原则**：
- ✅ **预期的业务失败** → `Result[T, E]`
- ✅ **系统错误/编程错误** → `Exception`
- ✅ **前置条件检查** → `Guard.require()`

---

## 测试约定

### 1. 测试文件组织

```
tests/
├── unit/              # 单元测试（Domain/Application）
│   ├── domain/
│   │   └── test_order.py
│   └── application/
│       └── test_create_order.py
├── integration/       # 集成测试（Infrastructure）
│   └── test_order_repository.py
└── e2e/              # 端到端测试
    └── test_order_flow.py
```

### 2. 测试命名

```python
# 模式：test_<被测试的行为>_<预期结果>
def test_order_cancel_when_pending_succeeds(): ...
def test_order_cancel_when_completed_fails(): ...
def test_create_order_with_invalid_items_returns_error(): ...
```

### 3. 测试分层策略

#### 单元测试（Domain）
```python
# 纯业务逻辑，无需 Mock
def test_order_total_calculation():
    order = Order.create("customer-1")
    order.add_item(Product(id=..., price=Money(100, "USD")), quantity=2)

    assert order.total_amount == Money(200, "USD")
```

#### 集成测试（Application）
```python
# 使用 InMemory 适配器
async def test_create_order_usecase():
    repo = InMemoryOrderRepository()
    uow = InMemoryUnitOfWork()
    usecase = CreateOrder(repo, uow)

    result = await usecase(CreateOrderInput(
        customer_id="customer-1",
        items=[{"product_id": "p1", "quantity": 2}]
    ))

    assert result.is_ok
    order = await repo.get(result.unwrap().order_id)
    assert order is not None
```

#### E2E 测试（Interfaces）
```python
# 完整的 HTTP → DB 流程
async def test_order_api_creates_order_in_database(client: TestClient, db: Database):
    response = await client.post("/api/orders", json={
        "customer_id": "customer-1",
        "items": [{"product_id": "p1", "quantity": 2}]
    })

    assert response.status_code == 201
    order_id = response.json()["order_id"]

    # 验证数据库
    order = await db.query(OrderModel).filter_by(id=order_id).first()
    assert order is not None
```

### 4. Fixture 组织

```python
# tests/conftest.py
import pytest

@pytest.fixture
def in_memory_repo() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()

@pytest.fixture
def sample_order() -> Order:
    return Order.create(customer_id="customer-1")

# 使用
def test_something(in_memory_repo, sample_order):
    ...
```

---

## 代码风格

### 1. 格式化工具
- **Ruff**: 代码检查和格式化
- **MyPy**: 类型检查

```bash
# 格式化
make fmt

# 检查
make lint
```

### 2. 行长度
- 最大 100 字符（已在 `pyproject.toml` 配置）

### 3. 导入排序
- 使用 Ruff 自动排序（isort 规则）

### 4. Docstring 风格

```python
def create_order(customer_id: str, items: List[dict]) -> Result[Order, str]:
    """创建新订单。

    Args:
        customer_id: 客户 ID
        items: 订单项列表，格式 [{"product_id": str, "quantity": int}]

    Returns:
        成功时返回 Ok(Order)，失败时返回 Err(error_message)

    Example:
        >>> result = create_order("c1", [{"product_id": "p1", "quantity": 2}])
        >>> if result.is_ok:
        ...     order = result.unwrap()
    """
    ...
```

### 5. 注释原则

```python
# ✅ 解释"为什么"而非"是什么"
# 使用悲观锁防止库存超卖
order = await repo.get_for_update(order_id)

# ❌ 重复代码的注释
# 获取订单
order = await repo.get(order_id)
```

---

## 快速检查清单

在提交代码前，确保：

- [ ] ✅ 所有公共 API 有类型注解
- [ ] ✅ Domain 层没有 I/O 操作
- [ ] ✅ 使用 `Result` 类型处理业务错误
- [ ] ✅ Entity/ValueObject 使用 `@dataclass`
- [ ] ✅ 聚合根记录领域事件
- [ ] ✅ Repository 返回 Entity 而非 ORM 模型
- [ ] ✅ UseCase 通过 UnitOfWork 管理事务
- [ ] ✅ 运行 `make lint` 通过
- [ ] ✅ 运行 `make test` 通过
- [ ] ✅ 新功能有对应测试

---

## 参考资料

- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [Protocols (PEP 544)](https://peps.python.org/pep-0544/)
- [Domain-Driven Design](https://www.domainlanguage.com/ddd/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
