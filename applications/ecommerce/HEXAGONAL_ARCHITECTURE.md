# Hexagonal Architecture (Ports & Adapters)

本文档说明 Bento 电商应用的六边形架构设计。

## 📐 核心原则

六边形架构（Hexagonal Architecture），也称为端口-适配器模式（Ports and Adapters），核心思想是：

1. **领域驱动**: 业务逻辑（领域层）位于中心，不依赖外部框架
2. **端口定义**: 领域层定义接口（端口），声明需要什么
3. **适配器实现**: 基础设施层实现接口（适配器），提供具体实现
4. **依赖倒置**: 外层依赖内层，基础设施依赖领域，而非相反

## 🏗️ 目录结构

```
applications/ecommerce/
├── modules/order/                              # Order 业务模块 ⭐
│   ├── domain/                                 # 领域层（核心业务逻辑）
│   │   ├── order.py                            # 聚合根: Order, OrderItem
│   │   ├── events.py                           # 领域事件
│   │   └── ports/                              # 端口定义（接口）⭐
│   │       ├── __init__.py
│   │       └── order_repository.py             # IOrderRepository 接口
│   ├── application/                            # 应用层（用例编排）
│   │   ├── commands/                           # 命令处理器
│   │   └── queries/                            # 查询处理器
│   ├── persistence/                            # 持久化层（模块专属）⭐⭐⭐
│   │   ├── models/                             # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   └── order_model.py                  # OrderModel, OrderItemModel
│   │   ├── mappers/                            # Domain ↔ Persistence 映射器
│   │   │   ├── __init__.py
│   │   │   └── order_mapper.py                 # OrderMapper, OrderItemMapper
│   │   └── repositories/                       # 仓储实现（适配器）
│   │       ├── __init__.py
│   │       └── order_repository.py             # OrderRepository (实现 IOrderRepository)
│   └── adapters/                               # 已废弃（向后兼容）
│       └── __init__.py
│
└── modules/product/                            # Product 业务模块（未来扩展）
    ├── domain/
    ├── application/
    └── persistence/                            # Product 模块专属持久化
```

## 🎯 分层职责

### 1. Domain Layer (领域层) - 核心业务

**位置**: `modules/order/domain/`

**职责**:
- 定义核心业务实体和聚合根（`Order`, `OrderItem`）
- 定义领域事件（`OrderCreated`, `OrderPaid`）
- 定义端口接口（`IOrderRepository`）
- 包含业务规则和不变量

**特点**:
- ✅ 不依赖任何外部框架
- ✅ 不依赖数据库、HTTP、消息队列等
- ✅ 纯粹的业务逻辑

**示例**:

```python
# modules/order/domain/order.py
class Order(AggregateRoot[ID]):
    """订单聚合根 - 纯粹的业务逻辑"""

    def pay(self) -> None:
        """支付订单"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be paid")
        self.status = OrderStatus.PAID
        self.paid_at = datetime.now()
        self.add_event(OrderPaid(order_id=self.id))

# modules/order/domain/ports/order_repository.py
class IOrderRepository(Protocol):
    """订单仓储接口（端口）- 领域层定义契约"""

    async def get(self, id: ID) -> Order | None:
        """获取订单"""
        ...

    async def save(self, order: Order) -> None:
        """保存订单"""
        ...
```

### 2. Application Layer (应用层) - 用例编排

**位置**: `modules/order/application/`

**职责**:
- 编排领域对象完成用例
- 协调多个聚合根
- 触发领域事件
- 事务边界管理

**特点**:
- ✅ 依赖领域层（通过端口接口）
- ✅ 不关心具体实现（数据库、HTTP 等）
- ✅ 编排业务流程

**示例**:

```python
# modules/order/application/commands/create_order.py
class CreateOrderHandler:
    def __init__(self, order_repo: IOrderRepository):  # 依赖端口，不是具体实现
        self._order_repo = order_repo

    async def handle(self, cmd: CreateOrderCommand) -> ID:
        # 1. 创建领域对象
        order = Order.create(
            order_id=ID.generate(),
            customer_id=cmd.customer_id,
        )

        # 2. 通过端口保存（不关心具体实现）
        await self._order_repo.save(order)

        return order.id
```

### 3. Persistence Layer (持久化层) - 模块专属基础设施

**位置**: `modules/order/persistence/` ⭐⭐⭐

**职责**:
- 定义数据库模型（ORM）
- 实现领域对象 ↔ 数据库对象的映射
- 实现仓储接口（适配器）
- 处理数据库交互细节

**特点**:
- ✅ **模块化**: 每个模块有自己的 persistence 目录
- ✅ **高内聚**: 模块的所有持久化代码在一起
- ✅ **独立演进**: 模块可以独立修改、部署
- ✅ **依赖领域层**: 实现领域层定义的端口接口
- ✅ **可替换**: 换数据库只需换这一层

#### 3.1 Models (ORM 模型)

```python
# modules/order/persistence/models/order_model.py
from bento.persistence import Base  # 框架提供的 Base

class OrderModel(Base):
    """订单持久化模型 - 数据库表结构"""
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(26))
    status: Mapped[str] = mapped_column(String(20))
    # ... SQLAlchemy 特定配置
```

#### 3.2 Mappers (映射器)

```python
# modules/order/persistence/mappers/order_mapper.py
from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.persistence.models import OrderModel

class OrderMapper(AutoMapper[Order, OrderModel]):
    """领域对象 ↔ 持久化对象映射器"""

    def __init__(self):
        super().__init__(Order, OrderModel)
        self.register_child("items", OrderItemMapper(), parent_key="order_id")
```

#### 3.3 Repositories (仓储实现 - 适配器)

```python
# modules/order/persistence/repositories/order_repository.py
from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.persistence.models import OrderModel
from applications.ecommerce.modules.order.persistence.mappers import OrderMapper

class OrderRepository(RepositoryAdapter[Order, OrderModel, ID]):
    """订单仓储实现 - 适配器

    实现领域层定义的 IOrderRepository 接口
    """

    def __init__(self, session: AsyncSession, actor: str = "system"):
        mapper = OrderMapper()
        base_repo = BaseRepository(
            session=session,
            po_type=OrderModel,
            actor=actor,
            interceptor_chain=create_default_chain(actor),
        )
        super().__init__(repository=base_repo, mapper=mapper)

    async def get(self, id: ID) -> Order | None:
        """实现接口定义的方法"""
        # ... 数据库查询细节
```

## 🔄 依赖方向

```
┌────────────────────────────────────────┐
│         Domain Layer (核心)             │
│  ┌──────────────┐  ┌─────────────┐    │
│  │ Order        │  │ Ports       │    │
│  │ OrderItem    │  │ (Interfaces)│    │
│  └──────────────┘  └─────────────┘    │
└────────────────────────────────────────┘
           ▲                    ▲
           │                    │
           │ depends on         │ implements
           │                    │
┌──────────┴────────────────────┴────────┐
│      Application Layer (用例)           │
│  ┌──────────────┐  ┌─────────────┐    │
│  │ Commands     │  │ Queries     │    │
│  └──────────────┘  └─────────────┘    │
└─────────────────────────────────────────┘
           ▲
           │ uses
           │
┌──────────┴──────────────────────────────┐
│   Persistence Layer (基础设施)           │
│  ┌──────────┐ ┌────────┐ ┌──────────┐  │
│  │ Models   │ │Mappers │ │Repos     │  │
│  │(ORM)     │ │        │ │(Adapters)│  │
│  └──────────┘ └────────┘ └──────────┘  │
└─────────────────────────────────────────┘
```

**关键点**:
1. Domain Layer 不依赖任何外部层
2. Application Layer 依赖 Domain Layer 的接口（端口）
3. Persistence Layer 实现 Domain Layer 的接口（适配器）
4. 依赖倒置: 外层依赖内层，而非相反

## 📦 Import 规则

### ✅ 允许的导入

```python
# 1. 应用层导入领域层（端口）
from applications.ecommerce.modules.order.domain.ports import IOrderRepository
from applications.ecommerce.modules.order.domain.order import Order

# 2. 持久化层导入领域层和框架 Base
from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.domain.ports import IOrderRepository
from bento.persistence import Base  # 框架提供的 Base

# 3. 组合根导入所有层（依赖注入）
from applications.ecommerce.modules.order.domain.ports import IOrderRepository
from applications.ecommerce.modules.order.persistence import OrderRepository

# 4. 模块内部导入（persistence 层内部）
from applications.ecommerce.modules.order.persistence.models import OrderModel
from applications.ecommerce.modules.order.persistence.mappers import OrderMapper
```

### ❌ 禁止的导入

```python
# ❌ 领域层不能导入持久化层
from applications.ecommerce.modules.order.persistence.models import OrderModel  # 错误！

# ❌ 领域层不能导入应用层
from applications.ecommerce.modules.order.application.commands import CreateOrderCommand  # 错误！

# ❌ 应用层不能导入具体实现（只能用端口）
from applications.ecommerce.modules.order.persistence import OrderRepository  # 错误！

# ❌ 跨模块导入持久化层（模块间应该独立）
from applications.ecommerce.modules.product.persistence import ProductModel  # 避免！
```

## 🔌 端口 vs 适配器

### 端口 (Ports) - 接口定义

**定义位置**: `modules/order/domain/ports/`

```python
# domain/ports/order_repository.py
class IOrderRepository(Protocol):
    """端口: 领域层定义需要什么

    这是一个契约，说明领域层需要什么功能
    """
    async def get(self, id: ID) -> Order | None: ...
    async def save(self, order: Order) -> None: ...
    async def find_by_customer(self, customer_id: ID) -> list[Order]: ...
```

### 适配器 (Adapters) - 接口实现

**实现位置**: `modules/order/persistence/repositories/`

```python
# modules/order/persistence/repositories/order_repository.py
class OrderRepository(RepositoryAdapter[Order, OrderModel, ID]):
    """适配器: 基础设施层提供具体实现

    实现 IOrderRepository 接口，连接领域层和数据库
    """
    async def get(self, id: ID) -> Order | None:
        # 具体的数据库查询实现
        stmt = select(OrderModel).where(OrderModel.id == id.value)
        result = await self._session.execute(stmt)
        po = result.scalar_one_or_none()
        return self._mapper.map_reverse(po) if po else None
```

## 🎨 为什么采用模块化 Persistence？

### 1. 高内聚、低耦合

**模块化 persistence** (`modules/order/persistence/`):
```
modules/order/
├── domain/
│   ├── order.py                            # 业务逻辑
│   └── ports/order_repository.py           # 接口定义
├── application/                            # 用例编排
└── persistence/                            # ⭐ 模块专属持久化
    ├── models/order_model.py               # Order 模型
    ├── mappers/order_mapper.py             # Order 映射器
    └── repositories/order_repository.py    # Order 仓储
```

**优点**:
- ✅ **高内聚**: Order 相关的所有代码（领域、应用、持久化）都在 `modules/order/` 下
- ✅ **清晰边界**: 一眼看出哪些持久化代码属于哪个模块
- ✅ **独立演进**: 修改 Order 持久化不影响 Product 模块
- ✅ **微服务友好**: 将来拆分为微服务时，直接拿走整个 `modules/order/` 目录
- ✅ **团队协作**: 不同团队可以独立开发不同模块，减少冲突

**对比全局 persistence**:
```
persistence/                                # ❌ 全局持久化
├── models/
│   ├── order_model.py                      # Order 和 Product 混在一起
│   └── product_model.py
├── mappers/
│   ├── order_mapper.py
│   └── product_mapper.py
└── repositories/
    ├── order_repository.py
    └── product_repository.py
```

- ❌ **低内聚**: Order 的持久化代码散落在多个目录
- ❌ **模块不清晰**: 看不出哪些代码属于 Order
- ❌ **耦合风险**: 所有模块的持久化代码在一起，可能产生依赖
- ❌ **拆分困难**: 要拆分为微服务需要重新组织代码

### 2. 测试更容易

**领域层测试** - 不需要数据库：
```python
def test_order_payment():
    # 测试业务逻辑，不需要数据库
    order = Order.create(order_id=ID.generate(), customer_id=ID.generate())
    order.pay()
    assert order.status == OrderStatus.PAID
```

**应用层测试** - 使用 Mock：
```python
async def test_create_order_handler():
    # Mock 端口接口，不需要真实数据库
    mock_repo = Mock(spec=IOrderRepository)
    handler = CreateOrderHandler(order_repo=mock_repo)

    result = await handler.handle(CreateOrderCommand(...))
    mock_repo.save.assert_called_once()
```

### 3. 共享基础设施

虽然每个模块有自己的 persistence，但使用框架的 Base 是合理的：

```python
# 框架提供 Base (bento/persistence/base.py)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Framework base for all SQLAlchemy models"""
    # ...

# modules/order/persistence/models/order_model.py
from bento.persistence import Base  # 使用框架 Base

class OrderModel(Base):
    __tablename__ = "orders"
    # ...

# modules/product/persistence/models/product_model.py
from bento.persistence import Base  # 同样使用框架 Base

class ProductModel(Base):
    __tablename__ = "products"
    # ...
```

**好处**:
- ✅ 所有模型共享框架的 Base，便于 Alembic 迁移
- ✅ 数据库初始化只需要一个 Base
- ✅ 跨模块外键关联（如果需要）也能正常工作
- ✅ 框架统一管理，无需应用层重复定义

### 4. 可替换性

因为依赖接口而非实现，可以轻松替换：

```python
# 开发环境: SQLite
from applications.ecommerce.modules.order.persistence import OrderRepository
order_repo = OrderRepository(sqlite_session)

# 生产环境: PostgreSQL
order_repo = OrderRepository(postgres_session)

# 测试环境: In-Memory
order_repo = InMemoryOrderRepository()  # 不同实现，同样的接口

# 所有实现都满足 IOrderRepository 接口，可互换！
```

## 🚀 实际应用示例

### 创建订单流程

```python
# 1. Domain Layer: 定义业务逻辑和接口
# modules/order/domain/order.py
class Order(AggregateRoot[ID]):
    @classmethod
    def create(cls, order_id: ID, customer_id: ID) -> "Order":
        order = cls(id=order_id, customer_id=customer_id)
        order.add_event(OrderCreated(order_id=order_id))
        return order

# modules/order/domain/ports/order_repository.py
class IOrderRepository(Protocol):
    async def save(self, order: Order) -> None: ...

# 2. Application Layer: 编排用例
# modules/order/application/commands/create_order.py
class CreateOrderHandler:
    def __init__(self, order_repo: IOrderRepository):  # 依赖端口
        self._order_repo = order_repo

    async def handle(self, cmd: CreateOrderCommand) -> ID:
        order = Order.create(cmd.order_id, cmd.customer_id)
        await self._order_repo.save(order)  # 不关心怎么保存
        return order.id

# 3. Persistence Layer: 实现技术细节
# modules/order/persistence/repositories/order_repository.py
class OrderRepository(RepositoryAdapter[Order, OrderModel, ID]):
    async def save(self, order: Order) -> None:
        # 1. 映射: Domain -> PO
        po = self._mapper.map(order)
        # 2. 数据库操作
        self._session.add(po)
        await self._session.flush()

# 4. Composition Root: 依赖注入
# runtime/composition.py
def wire_dependencies(session: AsyncSession):
    # 注入具体实现（适配器）
    from applications.ecommerce.modules.order.persistence import OrderRepository
    order_repo = OrderRepository(session)  # 实现 IOrderRepository
    create_handler = CreateOrderHandler(order_repo)
    return create_handler
```

## 📋 迁移清单

从全局 `persistence/` 迁移到模块化 `modules/order/persistence/`：

### Step 1: 创建模块 persistence 结构

```bash
# 创建模块 persistence 目录
mkdir -p modules/order/persistence/models
mkdir -p modules/order/persistence/mappers
mkdir -p modules/order/persistence/repositories
```

### Step 2: 移动模型

```bash
# 从全局 persistence 移动到模块 persistence
mv persistence/models/order_model.py \
   modules/order/persistence/models/order_model.py
```

更新模型导入：
```python
# modules/order/persistence/models/order_model.py
from bento.persistence import Base  # 使用框架 Base

class OrderModel(Base):
    __tablename__ = "orders"
    # ...
```

### Step 3: 移动映射器和仓储

```bash
# 移动 mapper
mv persistence/mappers/order_mapper.py \
   modules/order/persistence/mappers/order_mapper.py

# 移动 repository
mv persistence/repositories/order_repository.py \
   modules/order/persistence/repositories/order_repository.py
```

更新导入：
```python
# modules/order/persistence/mappers/order_mapper.py
from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.persistence.models import OrderModel

# modules/order/persistence/repositories/order_repository.py
from applications.ecommerce.modules.order.persistence.models import OrderModel
from applications.ecommerce.modules.order.persistence.mappers import OrderMapper
```

### Step 4: 更新导入路径

```python
# 旧代码（全局 persistence）
from applications.ecommerce.persistence.repositories import OrderRepository

# 新代码（模块化 persistence）
from applications.ecommerce.modules.order.persistence import OrderRepository

# 框架 Base（直接从框架导入）
from bento.persistence import Base
```

### Step 5: 创建领域端口（如果还没有）

```python
# modules/order/domain/ports/order_repository.py
from typing import Protocol
from applications.ecommerce.modules.order.domain.order import Order
from bento.core.ids import ID

class IOrderRepository(Protocol):
    async def get(self, id: ID) -> Order | None: ...
    async def save(self, order: Order) -> None: ...
    # ... 其他方法
```

## 📚 参考资料

- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [DDD Distilled (Vaughn Vernon)](https://www.oreilly.com/library/view/domain-driven-design-distilled/9780134434964/)

## ✅ 总结

| 层级 | 位置 | 职责 | 依赖方向 |
|------|------|------|----------|
| **Domain** | `modules/order/domain/` | 业务逻辑 + 端口定义 | 不依赖任何外部 |
| **Application** | `modules/order/application/` | 用例编排 | → Domain (端口) |
| **Persistence** | `modules/order/persistence/` ⭐ | 模块专属技术实现 | → Domain + Framework |
| **Framework** | `bento/persistence/` | Base + Mixins | - |

**核心思想**:
- **Domain** 定义"需要什么" (端口)
- **Persistence** 提供"怎么做" (适配器)
- **Application** 编排"做什么" (用例)
- **模块化**: 每个模块有自己的 persistence 层，高内聚、低耦合

**关键优势**:
- ✅ **高内聚**: 模块的所有代码（领域、应用、持久化）都在一起
- ✅ **清晰边界**: 模块边界清晰，职责明确
- ✅ **独立演进**: 模块可以独立修改、测试、部署
- ✅ **微服务友好**: 将来拆分为微服务时，直接拿走整个模块目录
- ✅ **团队协作**: 不同团队可以独立开发不同模块

通过这种设计，实现了业务逻辑与技术细节的彻底分离，同时保持了模块的高内聚和独立性，提高了系统的可测试性、可维护性、可扩展性和可替换性。

