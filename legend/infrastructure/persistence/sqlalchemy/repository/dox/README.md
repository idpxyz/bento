# SQLAlchemy 仓储模式实现指南 (V2)

## 1. 概览

本文档旨在详细阐述我们设计的第二代（V2）仓储模式的架构、设计思想、使用方法和最佳实践。这套实现严格遵循领域驱动设计（DDD）和SOLID原则，旨在为应用提供一个高度解耦、可测试、可扩展且高性能的数据持久化层。

## 2. 核心设计思想

我们架构的基石是**关注点分离 (Separation of Concerns)**。每一层、每一个组件都有其单一、明确的职责，有效地避免了业务逻辑、领域知识和基础设施细节的混杂。

- **领域驱动设计 (DDD)**: 仓储的接口（`RepositoryProtocol`）完全根据领域层的需求定义，它只关心领域聚合根（AR），对底层数据库技术一无所知。
- **依赖倒置原则 (DIP)**: 应用层和领域层依赖于抽象的 `RepositoryProtocol`，而不是具体的实现。这使得底层实现可以被轻松替换，极大地提高了代码的可测试性和灵活性。
- **单一职责原则 (SRP)**:
  - `BaseRepository` 只负责与数据库交互和操作持久化对象（PO）。
  - `BaseAdapter` 只负责适配领域层和基础设施层，转换对象和规范。
  - `RepositoryProtocol` 只负责定义领域仓储的契约。
- **接口隔离原则 (ISP)**: 通过将读写操作分离到 `ReadRepositoryProtocol` 和 `WriteRepositoryProtocol`，调用方可以只依赖于它们需要的功能。

## 3. 架构分层解析

我们的仓储模式被清晰地划分为三个逻辑层次，每一层都有明确的边界和职责。

![Architecture Diagram](https://user-images.githubusercontent.com/12543999/220804868-b749f7e8-c5a4-4328-912f-9c4c7951e737.png)  
*(这是一个示意图，仅用于说明分层概念)*

---

### 3.1. 领域层 (Domain Layer)

- **文件**: `src/idp/framework/domain/repository/v_base.py`
- **核心组件**: `RepositoryProtocol`, `ReadRepositoryProtocol`, `WriteRepositoryProtocol`
- **职责**:
  - **定义契约**: 这是仓储对外的唯一公共契约。应用服务和领域服务通过此协议与数据持久化层交互。
  - **领域为中心**: 协议中的所有方法都使用领域对象（如聚合根 `AR`）和领域概念（如 `Specification[AR]`）进行定义，完全隔离了基础设施细节。
  - **稳定**: 这是最稳定的一层。只要领域的业务需求不变，这一层的代码就不需要改变。

---

### 3.2. 适配器层 (Adapter Layer)

- **文件**: `src/idp/framework/infrastructure/persistence/sqlalchemy/repository/v_adapter.py`
- **核心组件**: `BaseAdapter`
- **职责**:
  - **连接桥梁**: `BaseAdapter` 是连接领域层和基础设施层的关键桥梁。它是整个架构中唯一一个同时"知道"领域对象（AR）和持久化对象（PO）的地方。
  - **双向适配**:
    1.  **方法适配**: 它实现了领域层的 `RepositoryProtocol` 接口。
    2.  **对象适配**: 它使用 `_to_domain` 和 `_from_domain` 映射函数，在 `AR` 和 `PO` 之间进行双向转换。
    3.  **规范适配**: 它使用 `spec.with_type(PO)` 将领域层的 `Specification[AR]` 转换为基础设施层能理解的 `Specification[PO]`。
  - **委托**: 它不包含任何实际的数据库查询逻辑，而是将调用委托给基础设施层的 `RepositoryDelegate`。

---

### 3.3. 基础设施层 (Infrastructure Layer)

这是与数据库进行实际交互的底层。

- **文件**: `.../repository/delegate.py`
- **核心组件**: `RepositoryDelegate`
- **职责**:
  - **内部契约**: 定义了基础设施层内部的接口协议。`BaseAdapter` 依赖此协议，而 `BaseRepository` 则是此协议的实现。这保证了 `Adapter` 和 `Repository` 之间的解耦。
  - **命名约定**: 所有方法都使用 `_po` 后缀（如 `get_po_by_id`, `query_po_by_spec`），清晰地表明其操作的是持久化对象。

- **文件**: `.../repository/v_base.py`
- **核心组件**: `BaseRepository`
- **职责**:
  - **数据持久化**: 负责所有针对 `PO` 的 CRUD (创建、读取、更新、删除) 操作。
  - **数据库技术封装**: 封装了所有与 SQLAlchemy 相关的实现细节，如 `session` 操作、`QueryBuilder` 的使用等。
  - **性能优化**: 实现了如 `session.get()` 的最高效查询路径，以及 `QueryBuilder` 池化等机制。
  - **横切关注点**: 通过拦截器模式（Interceptor），优雅地处理了缓存、审计、乐观锁等跨业务的通用逻辑。

## 4. 核心功能与可配置特性

我们的仓储实现通过 **拦截器 (Interceptor)** 机制，内置了多个强大的、可配置的横切关注点功能。这些功能在 `BaseAdapter` 的构造函数中默认启用，但可以在具体仓储的实现中按需覆盖。

- `enable_cache`: 是否启用缓存。**默认 `True`**。
- `enable_optimistic_lock`: 是否启用乐观锁。**默认 `True`**。
- `enable_audit`: 是否启用审计日志（自动记录创建和更新信息）。**默认 `True`**。
- `enable_soft_delete`: 是否启用软删除（逻辑删除而非物理删除）。**默认 `True`**。
- `enable_logging`: 是否启用详细的操作日志。**默认 `False`**。
- `custom_interceptors`: 允许注入用户自定义的拦截器列表。

### 配置示例

假设我们需要创建一个只读且不希望使用乐观锁的 `Order` 仓储，可以在其构造函数中覆盖默认配置：

```python
# infrastructure/persistence/sqlalchemy/repository/order_repository.py

class OrderReadOnlyRepository(BaseAdapter[Order, OrderPO, str], IOrderRepository):
    # ... (_to_domain, _from_domain 映射) ...
    
    def __init__(self, session: AsyncSession, actor: str = "system"):
        super().__init__(
            session=session,
            model_class=OrderPO,
            actor=actor,
            # 覆盖默认配置
            enable_optimistic_lock=False,
            enable_audit=False
            # 其他配置将使用默认值 (cache=True, soft_delete=True)
        )
```

## 5. 如何使用：为新聚合根创建仓储

假设我们要为一个新的聚合根 `Order` 创建仓储，请遵循以下步骤：

### 第1步: 定义领域对象 (AR) 和持久化对象 (PO)

```python
# domain/aggregate/order.py
class Order(BaseAggregateRoot):
    # ... 领域属性和方法
    pass

# infrastructure/persistence/sqlalchemy/po/order_po.py
class OrderPO(BasePO):
    __tablename__ = 'orders'
    # ... SQLAlchemy 表字段定义
    pass
```

### 第2步: 创建具体的仓储实现

创建 `OrderRepository`，它继承自 `BaseAdapter`，并提供 `AR` 与 `PO` 之间的映射逻辑。

```python
# infrastructure/persistence/sqlalchemy/repository/order_repository.py
from .v_adapter import BaseAdapter
from ...po.order_po import OrderPO
from .....domain.aggregate.order import Order

# 1. 定义映射函数
def _order_to_domain(po: OrderPO) -> Order:
    # 实现从 PO 到 AR 的转换逻辑
    return Order(...)

def _order_from_domain(ar: Order) -> OrderPO:
    # 实现从 AR 到 PO 的转换逻辑
    return OrderPO(...)

# 2. 创建仓储类
class OrderRepository(BaseAdapter[Order, OrderPO, str], IOrderRepository): # IOrderRepository 是可选的领域接口
    
    _to_domain = _order_to_domain
    _from_domain = _order_from_domain

    def __init__(self, session: AsyncSession, actor: str = "system"):
        # 初始化时传入 session 和 PO 的类型
        super().__init__(session, OrderPO, actor=actor)

    # 3. (可选) 实现特有的仓储方法
    async def find_by_customer_id(self, customer_id: str) -> List[Order]:
        spec = CompositeSpecification(
            filters=[Filter(field='customer_id', operator=FilterOperator.EQUALS, value=customer_id)]
        )
        return await self.query_all_by_spec(spec)
```

### 第3步: 在应用服务中使用

通过依赖注入，在你的应用服务中使用 `OrderRepository`。

```python
# application/services/order_service.py
class OrderService:
    def __init__(self, order_repo: IOrderRepository):
        self.order_repo = order_repo

    async def get_order(self, order_id: str) -> Optional[Order]:
        # 现在可以像操作一个普通集合一样使用仓储
        return await self.order_repo.get_by_id(order_id)
```

## 6. 如何扩展

### 6.1. 添加新的通用便捷方法

如果我们想添加一个所有仓储都应该具备的新方法（如 `get_by_code`），请遵循我们添加 `get_by_id` 的三步流程：

1.  **更新协议**: 在 `domain/.../v_base.py` 的 `ReadRepositoryProtocol` 中添加方法定义。
2.  **更新底层实现**: 在 `infrastructure/.../v_base.py` 的 `BaseRepository` 中添加对应的 `_po` 方法（如 `get_po_by_code`）。
3.  **更新适配器**: 在 `infrastructure/.../v_adapter.py` 的 `BaseAdapter` 中实现协议方法，并调用底层的 `_po` 方法。

### 6.2. 添加新的业务特定方法

如果某个方法只与特定的聚合根相关（如 `find_by_customer_id`），则**不应该**修改基类。正确的做法是：

1.  (可选，推荐) 在该聚合根的特定领域接口中（如 `IOrderRepository`）定义此方法。
2.  在具体的仓储实现中（如 `OrderRepository`）直接实现该方法。其内部可以利用 `self.query_..._by_spec` 方法来构建查询，如上文示例所示。

## 7. 错误处理原则

- **查询无果**: 当 `get_by_id` 或 `query_one_by_spec` 找不到对应的实体时，方法将返回 `None`，而**不会**抛出异常。调用方需要处理 `None` 的情况。
- **并发冲突**: 当启用乐观锁（`enable_optimistic_lock=True`）并发生并发更新时，系统会抛出一个特定的并发冲突异常，应用层需要捕获并处理此异常（例如，提示用户数据已过期，请刷新重试）。
- **数据库错误**: 底层的数据库连接或语法错误会被捕获并记录日志，然后向上层抛出，以便进行统一的异常处理。

## 8. 维护指南和反模式

为了保持架构的健康，请务必遵守以下原则：

- **严禁跨层引用**:
  - 领域层**绝不**能 `import` 任何来自基础设施层的东西。
  - 应用层应该只 `import` 领域层的协议（接口），而非具体的仓储实现。这对于依赖注入和可测试性至关重要。
- **严禁PO泄漏**: 持久化对象（PO）的生命周期必须被严格限制在基础设施层内部，**绝不**能让它"泄漏"到适配器层之外。
- **保持`BaseRepository`纯净**: `BaseRepository` 中只应包含通用的、与具体业务无关的持久化逻辑。任何与特定业务（如`Order`）相关的逻辑都应在具体的子类（`OrderRepository`）中实现。
- **优先使用规范 (Specification)**: 对于所有复杂的`WHERE`查询，都应优先使用`Specification`模式，而不是在仓储中硬编码查询逻辑或添加大量`find_by_...`方法。这能有效避免仓储接口的臃肿。
- **合理使用缓存**: 对于频繁读取且不经常变化的数据，启用缓存能显著提升性能。但在高频写入的场景下，需要仔细评估缓存失效策略带来的开销。



## SQLAlchemy 仓储 helper 目录设计说明

### 目录定位

`helper/` 目录下的各类工具和构建器，承担了"将领域查询规范（Specification）高效、安全地转换为 SQLAlchemy 查询语句"的桥梁作用，是基础设施层解耦、可扩展、可维护的关键。

---

### 主要组件与分工

#### 1. SpecificationBuilder
- **职责**：面向领域/应用层，提供流式API构建业务查询意图（如过滤、排序、分页、分组、统计等），生成领域无关的 `Specification` 对象。
- **特点**：
  - 只关心"查什么"，不关心"怎么查"。
  - 组合业务条件，表达复杂查询意图。
  - 与ORM/数据库无关。
- **典型用法**：
  ```python
  spec = (SpecificationBuilder()
      .where("status", "=", "active")
      .add_sort("created_at", "desc")
      .set_page(page=2, size=20)
      .build())
  ```

#### 2. QueryBuilder
- **职责**：面向基础设施/ORM层，将 `Specification` 对象翻译为 SQLAlchemy 查询语句（select/where/order_by/limit/offset 等）。
- **特点**：
  - 只关心"怎么查"，不关心"查什么"。
  - 负责将领域规范映射为高效、正确的SQL。
  - 支持复杂的过滤、分组、排序、分页、统计等。
- **典型用法**：
  ```python
  query_builder = QueryBuilder(UserPO)
  stmt = (query_builder
      .apply_filters(spec.filters, field_resolver)
      .apply_sorts(spec.sorts, field_resolver)
      .apply_pagination(spec.page)
      .build())
  ```

#### 3. CountQueryBuilder
- **职责**：专门用于构建高效的计数（COUNT）SQL查询，避免不必要的字段和排序。
- **用法**：通常由 QueryBuilder 内部或仓储层自动调用。

#### 4. 其它辅助类
- **build_condition**：将单个 Filter 转换为 SQLAlchemy 的表达式。
- **FieldResolver**（在其它helper中）：负责将领域字段名映射为ORM模型的实际属性。
- **各种 Criterion/Filter/Sort/Statistic/Group/Having**：用于表达和传递查询条件、排序、分组、统计等。

---

### 分层协作流程

1. **应用/领域层** 用 `SpecificationBuilder` 构建查询规范（Specification）。
2. **基础设施层** 用 `QueryBuilder` 读取 Specification，把它翻译成 SQLAlchemy 查询。
3. **仓储层** 执行查询，返回结果。

---

### 设计优势
- **关注点分离**：业务与技术实现彻底解耦。
- **可扩展性**：支持多种后端（如SQL、NoSQL、内存等），只需实现不同的QueryBuilder。
- **可测试性**：领域规范和SQL生成可分别单元测试。
- **灵活性**：同一套Specification可用于数据库、缓存、权限等多场景。

---

### 维护建议
- **新增查询能力时**，优先扩展 SpecificationBuilder 和 QueryBuilder 的API。
- **如需支持新后端**，实现新的 QueryBuilder 即可。
- **保持领域层与ORM/SQL解耦**，不要在 SpecificationBuilder 中引入SQLAlchemy等依赖。

---

如需进一步了解各类helper的具体实现和用法，请查阅本目录下各模块源码和注释。 

---
*此文档旨在成为团队共享知识的核心部分，请在使用和维护过程中持续更新。*