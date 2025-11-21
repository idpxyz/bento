# 六边形架构（Hexagonal Architecture）实现指南

## 🎯 什么是六边形架构？

六边形架构，也称为 **Ports and Adapters Pattern**，由 Alistair Cockburn 提出，是一种将应用程序核心业务逻辑与外部系统隔离的架构模式。

### 核心思想

```
        ┌─────────────────────────────────────┐
        │                                     │
        │      Application Core               │
        │    ┌─────────────────────┐          │
        │    │                     │          │
        │    │   Domain Model      │          │
        │    │                     │          │
        │    └─────────────────────┘          │
        │              │                       │
        │              ↓                       │
        │    ┌─────────────────────┐          │
        │    │      Ports          │          │
        │    │   (Interfaces)      │          │
        │    └─────────────────────┘          │
        │                                     │
        └──────────┬──────────┬────────────────┘
                   │          │
        ┌──────────┘          └──────────┐
        ↓                                 ↓
┌────────────────┐              ┌────────────────┐
│   Adapters     │              │   Adapters     │
│  (Inbound)     │              │  (Outbound)    │
│                │              │                │
│ - REST API     │              │ - Database     │
│ - GraphQL      │              │ - External API │
│ - CLI          │              │ - Message Queue│
└────────────────┘              └────────────────┘
```

---

## 📐 Ordering BC 的六边形架构实现

### 完整架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    External World (Clients)                     │
└───────────────────────────────┬─────────────────────────────────┘
                                ↓
        ┌───────────────────────────────────────┐
        │    Primary Adapter (Driving)          │
        │    contexts/ordering/interfaces/      │
        │                                       │
        │    order_api.py                       │
        │    - FastAPI Controller               │
        │    - REST Endpoints                   │
        └───────────────────┬───────────────────┘
                            ↓ invokes
        ┌───────────────────────────────────────┐
        │    Application Layer                  │
        │    contexts/ordering/application/     │
        │                                       │
        │    commands/                          │
        │    - CreateOrderUseCase               │
        │    - PayOrderUseCase                  │
        │    queries/                           │
        │    - GetOrderQuery                    │
        │    - ListOrdersQuery                  │
        └───────────────────┬───────────────────┘
                            ↓ uses
        ┌───────────────────────────────────────────────────────┐
        │    Domain Layer (Core Business Logic)                │
        │    contexts/ordering/domain/                          │
        │                                                       │
        │    Aggregates:                                        │
        │    - order.py (Order)                                 │
        │    - order_item.py (OrderItem)                        │
        │                                                       │
        │    Value Objects:                                     │
        │    - vo/product_info.py (ProductInfo)                 │
        │                                                       │
        │    Ports (Interfaces):                                │
        │    - ports/services/i_product_catalog_service.py      │
        │    - ports/repositories/i_order_repository.py         │
        │                                                       │
        │    Events:                                            │
        │    - events/order_created_event.py                    │
        │    - events/order_paid_event.py                       │
        └────────────────┬──────────────────┬───────────────────┘
                         │                  │
         ┌───────────────┘                  └────────────────┐
         ↓                                                   ↓
┌─────────────────────────┐                    ┌─────────────────────────┐
│ Secondary Adapter       │                    │ Secondary Adapter       │
│ (Database - Driven)     │                    │ (External API - Driven) │
│                         │                    │                         │
│ infrastructure/adapters/│                    │ infrastructure/adapters/│
│   repositories/         │                    │   services/             │
│   - order_repository.py │                    │   - product_catalog_    │
│                         │                    │     adapter.py          │
│ implements              │                    │                         │
│ IOrderRepository        │                    │ implements              │
│                         │                    │ IProductCatalogService  │
└────────┬────────────────┘                    └────────┬────────────────┘
         │                                               │
         ↓                                               ↓
┌─────────────────────┐                    ┌─────────────────────────┐
│ PostgreSQL Database │                    │ Catalog BC (External)   │
│ - orders table      │                    │ - Product data          │
│ - order_items table │                    │ - Read-only access      │
└─────────────────────┘                    └─────────────────────────┘
```

---

## 🔑 核心概念详解

### 1. Port（端口）

**定义：** 应用核心定义的接口契约，告诉外部"我需要什么"。

**分类：**
- **Primary Port（驱动端口）**: 应用提供给外部调用的接口
  - 例如：UseCase 接口
  - 位置：通常是 Application Layer 的 UseCase 类

- **Secondary Port（被驱动端口）**: 应用需要的外部依赖接口
  - 例如：Repository、ExternalService
  - 位置：`domain/ports/`

**示例：**
```python
# domain/ports/services/i_product_catalog_service.py
class IProductCatalogService(ABC):
    """Secondary Port - 定义接口契约"""

    @abstractmethod
    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        pass
```

### 2. Adapter（适配器）

**定义：** 实现 Port 接口的具体技术，连接外部系统。

**分类：**
- **Primary Adapter（驱动适配器）**: 调用应用核心
  - 例如：REST API Controller、CLI、GraphQL Resolver
  - 位置：`interfaces/api/`

- **Secondary Adapter（被驱动适配器）**: 被应用核心调用
  - 例如：Database Repository、HTTP Client、Message Queue
  - 位置：`infrastructure/adapters/`

**示例：**
```python
# infrastructure/adapters/services/product_catalog_adapter.py
class ProductCatalogAdapter(IProductCatalogService):
    """Secondary Adapter - 实现具体技术"""

    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        # 实现：查询数据库、调用 HTTP 等
        pass
```

---

## 📁 目录结构映射

### 标准六边形架构目录

```
context/
├── domain/                         # 核心业务逻辑
│   ├── aggregates/                 # 聚合根
│   ├── entities/                   # 实体
│   ├── vo/                         # 值对象
│   ├── events/                     # 领域事件
│   ├── services/                   # 领域服务
│   └── ports/                      # ✅ Secondary Ports
│       ├── repositories/           # 仓储接口
│       └── services/               # 外部服务接口
│
├── application/                    # 应用层（用例编排）
│   ├── commands/                   # ✅ Primary Ports (Command)
│   ├── queries/                    # ✅ Primary Ports (Query)
│   └── dto/                        # 数据传输对象
│
├── infrastructure/                 # 基础设施层
│   ├── persistence/                # 持久化相关
│   │   ├── models/                 # ORM 模型
│   │   └── mappers/                # 对象映射器
│   └── adapters/                   # ✅ Secondary Adapters
│       ├── repositories/           # 仓储适配器
│       └── services/               # 外部服务适配器
│
└── interfaces/                     # 接口层
    └── api/                        # ✅ Primary Adapters
        ├── controllers/            # REST 控制器
        └── presenters/             # 视图呈现器
```

---

## 🔄 依赖规则

### 依赖方向

```
┌─────────────────┐
│  Infrastructure │
│   (Adapters)    │
└────────┬────────┘
         │ implements
         ↓
┌─────────────────┐
│     Domain      │ ← 核心，不依赖任何层
│    (Ports)      │
└────────┬────────┘
         ↑ uses
         │
┌─────────────────┐
│   Application   │
│   (Use Cases)   │
└────────┬────────┘
         ↑ invokes
         │
┌─────────────────┐
│   Interfaces    │
│  (Controllers)  │
└─────────────────┘
```

**关键原则：**
1. **Domain 层不依赖任何其他层**
2. **依赖方向：外层 → 内层**
3. **通过接口隔离，实现依赖倒置**

---

## 💻 完整代码示例

### 1. Domain Port（接口定义）

```python
# contexts/ordering/domain/ports/services/i_product_catalog_service.py

from abc import ABC, abstractmethod
from contexts.ordering.domain.vo.product_info import ProductInfo

class IProductCatalogService(ABC):
    """Secondary Port - 产品目录服务接口"""

    @abstractmethod
    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        """获取产品信息"""
        pass
```

### 2. Infrastructure Adapter（实现）

```python
# contexts/ordering/infrastructure/adapters/services/product_catalog_adapter.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.infrastructure.models.product_po import ProductPO
from contexts.ordering.domain.ports.services.i_product_catalog_service import (
    IProductCatalogService,
)
from contexts.ordering.domain.vo.product_info import ProductInfo

class ProductCatalogAdapter(IProductCatalogService):
    """Secondary Adapter - 产品目录适配器"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        stmt = select(ProductPO).where(
            ProductPO.id == product_id,
            ProductPO.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        product_po = result.scalar_one_or_none()

        if not product_po:
            return None

        return ProductInfo(
            product_id=product_po.id,
            product_name=product_po.name,
            unit_price=float(product_po.price),
            is_available=not product_po.is_deleted
        )
```

### 3. Application Use Case（使用 Port）

```python
# contexts/ordering/application/commands/create_order.py

from bento.application.usecase import BaseUseCase
from contexts.ordering.domain.ports.services.i_product_catalog_service import (
    IProductCatalogService,
)

class CreateOrderUseCase(BaseUseCase):
    """Application Layer - 使用 Port，不依赖具体实现"""

    def __init__(
        self,
        uow: IUnitOfWork,
        product_catalog: IProductCatalogService  # ✅ 依赖接口
    ):
        super().__init__(uow)
        self._product_catalog = product_catalog

    async def execute(self, command):
        # 通过 Port 调用，不知道具体实现
        product_info = await self._product_catalog.get_product_info(
            command.product_id
        )
        # ...
```

### 4. Interface Controller（依赖注入）

```python
# contexts/ordering/interfaces/api/order_api.py

from fastapi import APIRouter, Depends
from contexts.ordering.infrastructure.adapters.services.product_catalog_adapter import (
    ProductCatalogAdapter,
)

async def get_create_order_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
):
    # ✅ 依赖注入：注入具体的 Adapter
    product_catalog = ProductCatalogAdapter(uow.session)
    return CreateOrderUseCase(uow, product_catalog)
```

---

## 🎯 优势总结

### 1. **可测试性**
```python
# 测试时可以轻松 Mock Port
mock_product_catalog = Mock(spec=IProductCatalogService)
use_case = CreateOrderUseCase(uow, mock_product_catalog)
```

### 2. **可替换性**
```python
# 轻松切换不同实现，无需修改 Use Case
# 方案 A: 数据库查询
product_catalog = ProductCatalogAdapter(session)

# 方案 B: HTTP 调用
product_catalog = ProductCatalogHttpAdapter(http_client)

# 方案 C: 本地缓存
product_catalog = ProductCatalogCacheAdapter(cache)
```

### 3. **独立演进**
- Domain 层完全独立，可以单独测试
- Adapter 可以独立更换技术栈
- Application 层专注业务编排

### 4. **清晰的职责分离**
- **Domain**: 业务规则和逻辑
- **Application**: 用例编排
- **Infrastructure**: 技术实现
- **Interfaces**: 外部交互

---

## 📋 检查清单

使用以下清单验证你的实现是否符合六边形架构：

- [ ] Port 接口在 `domain/ports/` 目录
- [ ] Adapter 实现在 `infrastructure/adapters/` 目录
- [ ] Domain 层不依赖任何外部库（除了标准库）
- [ ] Application 层依赖 Port 接口，不依赖 Adapter
- [ ] 所有外部依赖都通过 Port 隔离
- [ ] 可以轻松 Mock Port 进行测试
- [ ] 可以轻松替换 Adapter 实现
- [ ] 依赖方向正确：Infrastructure → Domain ← Application

---

## 📚 参考资料

### 经典文章
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Alistair Cockburn
- [Ports and Adapters Pattern](https://web.archive.org/web/20180822100852/http://alistair.cockburn.us/Hexagonal+architecture)

### 书籍
- "Clean Architecture" - Robert C. Martin
- "Get Your Hands Dirty on Clean Architecture" - Tom Hombergs
- "Implementing Domain-Driven Design" - Vaughn Vernon

### 在线资源
- [Netflix 的六边形架构实践](https://netflixtechblog.com/)
- [Martin Fowler's Blog](https://martinfowler.com/)

---

## 💡 常见问题

### Q1: Port 应该放在 domain 还是 application 层？

**A:** 应该放在 **domain 层**。

- Port 是领域需求的体现（"我需要持久化"）
- Application 层只是使用这些接口
- 这样 Domain 层可以完全独立

### Q2: 什么时候用 Port，什么时候直接调用？

**A:** 当需要与外部系统交互时使用 Port：

- ✅ 使用 Port: Database、External API、Message Queue、File System
- ❌ 不需要 Port: Domain Services、Value Objects、Entities

### Q3: 一个 Adapter 可以实现多个 Port 吗？

**A:** 可以，但要谨慎：

- ✅ 如果多个 Port 逻辑相关，可以合并
- ❌ 避免 Adapter 职责过多，违反单一职责原则

### Q4: Primary Port 和 Secondary Port 的区别？

**A:**
- **Primary Port**: 应用提供的接口（Use Case）- 被外部调用
- **Secondary Port**: 应用需要的接口（Repository、ExternalService）- 调用外部

---

## 🎉 总结

六边形架构的核心是 **Ports and Adapters**：

1. **Domain 定义 Port**（我需要什么）
2. **Infrastructure 提供 Adapter**（如何提供）
3. **Application 使用 Port**（编排业务流程）
4. **Interfaces 连接外部**（API、CLI 等）

通过这种方式，实现了：
- ✅ 业务逻辑与技术细节分离
- ✅ 易于测试
- ✅ 易于替换技术栈
- ✅ 清晰的依赖方向

**记住：好的架构是为了应对变化，而六边形架构让变化变得简单！** 🚀
