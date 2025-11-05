# Adapter + Mapper 完整设计方案

**版本**: 1.0  
**日期**: 2025-11-04  
**作者**: Bento Architecture Team

---

## 📋 目录

1. [问题分析](#问题分析)
2. [架构设计](#架构设计)
3. [核心组件](#核心组件)
4. [实现细节](#实现细节)
5. [使用示例](#使用示例)
6. [集成方案](#集成方案)
7. [工作量评估](#工作量评估)

---

## 🔍 问题分析

### 当前架构的问题

**Phase 2 实现的 BaseRepository**:

```python
# ❌ 问题：T 的语义不清晰
class BaseRepository(Generic[T, ID], IRepository[T]):
    async def get(self, id: ID) -> T | None: ...
    async def save(self, entity: T) -> None: ...
```

**问题**:
1. ❌ `T` 既可以是 `AR` (Aggregate Root) 也可以是 `PO` (Persistence Object)
2. ❌ Domain 层可能直接依赖 PO，违反 DDD 分层
3. ❌ 缺少 AR ↔ PO 的映射层
4. ❌ 不符合六边形架构的端口-适配器模式

---

## 🏗️ 架构设计

### 正确的分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                           │
│  ┌───────────────┐         ┌──────────────────┐            │
│  │ AggregateRoot │         │ Repository Port  │            │
│  │    (AR)       │         │   (Protocol)     │            │
│  └───────────────┘         └──────────────────┘            │
└─────────────────────────────────────────────────────────────┘
                                    ↑
                                    │ implements
                                    │
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Repository Adapter (适配器)              │   │
│  │  - 实现 Domain Repository Port                      │   │
│  │  - 使用 Mapper 进行 AR ↔ PO 转换                   │   │
│  │  - 委托给 BaseRepository 执行数据库操作              │   │
│  └─────────────────────────────────────────────────────┘   │
│                        ↓ uses                                │
│  ┌──────────────┐     ┌──────────────┐                     │
│  │   Mapper     │     │ BaseRepository│                     │
│  │  AR ↔ PO     │     │  (PO 操作)    │                     │
│  └──────────────┘     └──────────────┘                     │
│                                ↓                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Persistence Object (PO)                       │   │
│  │        + Interceptor Chain                           │   │
│  │        + SQLAlchemy ORM                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 职责划分

| 组件 | 层次 | 职责 | 依赖 |
|------|------|------|------|
| **AggregateRoot** | Domain | 业务逻辑、领域模型 | 无 |
| **Repository Port** | Domain | 定义仓储接口 | 无 |
| **Mapper Protocol** | Application | 定义映射接口 | 无 |
| **Mapper Implementation** | Infrastructure | AR ↔ PO 映射 | AR, PO |
| **Repository Adapter** | Infrastructure | 实现 Repository Port | Mapper, BaseRepository |
| **BaseRepository** | Infrastructure | PO 数据库操作 | PO, Session |
| **PO** | Infrastructure | 数据库表映射 | SQLAlchemy |

---

## 🧩 核心组件

### 1. Mapper Protocol (Application Port)

**位置**: `src/application/ports/mapper.py`

```python
from typing import Protocol, TypeVar, Generic

S = TypeVar("S")  # Source
T = TypeVar("T")  # Target

class Mapper(Protocol[S, T]):
    """单向映射器 Protocol"""
    
    def map(self, source: S) -> T:
        """映射单个对象"""
        ...
    
    def map_list(self, sources: list[S]) -> list[T]:
        """批量映射"""
        ...


class BidirectionalMapper(Protocol[S, T]):
    """双向映射器 Protocol"""
    
    def map(self, source: S) -> T:
        """S → T"""
        ...
    
    def map_reverse(self, target: T) -> S:
        """T → S"""
        ...
    
    def map_list(self, sources: list[S]) -> list[T]:
        """批量 S → T"""
        ...
    
    def map_reverse_list(self, targets: list[T]) -> list[S]:
        """批量 T → S"""
        ...
```

### 2. POMapper (Infrastructure Implementation)

**位置**: `src/infrastructure/mapper/po_mapper.py`

```python
from typing import Generic, TypeVar
from application.ports.mapper import BidirectionalMapper

D = TypeVar("D")  # Domain (AR)
P = TypeVar("P")  # Persistence (PO)

class POMapper(Generic[D, P], BidirectionalMapper[D, P]):
    """AR ↔ PO 映射器"""
    
    def __init__(
        self,
        domain_type: type[D],
        po_type: type[P],
        auto_map: bool = True,
    ) -> None:
        self._domain_type = domain_type
        self._po_type = po_type
        self._auto_map = auto_map
    
    # AR → PO
    def map(self, domain: D) -> P:
        """领域对象 → 持久化对象"""
        return self.to_po(domain)
    
    # PO → AR
    def map_reverse(self, po: P) -> D:
        """持久化对象 → 领域对象"""
        return self.to_domain(po)
    
    def to_po(self, domain: D) -> P:
        """AR → PO (语义化方法名)"""
        if self._auto_map:
            return self._auto_map_to_po(domain)
        else:
            return self._custom_map_to_po(domain)
    
    def to_domain(self, po: P) -> D:
        """PO → AR (语义化方法名)"""
        if self._auto_map:
            return self._auto_map_to_domain(po)
        else:
            return self._custom_map_to_domain(po)
    
    # 批量映射
    def map_list(self, domains: list[D]) -> list[P]:
        return [self.to_po(d) for d in domains]
    
    def map_reverse_list(self, pos: list[P]) -> list[D]:
        return [self.to_domain(p) for p in pos]
    
    # 便捷方法
    def to_pos(self, domains: list[D]) -> list[P]:
        return self.map_list(domains)
    
    def to_domains(self, pos: list[P]) -> list[D]:
        return self.map_reverse_list(pos)
    
    # 映射实现（简化版，完整实现在 Phase 3）
    def _auto_map_to_po(self, domain: D) -> P:
        """自动映射 AR → PO"""
        po_dict = {}
        for field in self._get_common_fields():
            if hasattr(domain, field):
                po_dict[field] = getattr(domain, field)
        return self._po_type(**po_dict)
    
    def _auto_map_to_domain(self, po: P) -> D:
        """自动映射 PO → AR"""
        domain_dict = {}
        for field in self._get_common_fields():
            if hasattr(po, field):
                domain_dict[field] = getattr(po, field)
        return self._domain_type(**domain_dict)
    
    def _custom_map_to_po(self, domain: D) -> P:
        """自定义映射（子类重写）"""
        raise NotImplementedError("Custom mapping not implemented")
    
    def _custom_map_to_domain(self, po: P) -> D:
        """自定义映射（子类重写）"""
        raise NotImplementedError("Custom mapping not implemented")
    
    def _get_common_fields(self) -> list[str]:
        """获取共同字段（简化版）"""
        # 实际实现会更复杂，这里简化
        domain_fields = set(vars(self._domain_type).keys())
        po_fields = set(vars(self._po_type).keys())
        return list(domain_fields & po_fields)
```

### 3. BaseRepository (纯 PO 操作)

**位置**: `src/persistence/repository/sqlalchemy/base.py`

```python
# ✅ 重构后：专注于 PO 操作
class BaseRepository(Generic[PO, ID]):
    """SQLAlchemy Repository - 仅处理 PO"""
    
    def __init__(
        self,
        session: AsyncSession,
        po_type: type[PO],
        actor: str = "system",
        interceptor_chain: InterceptorChain[PO] | None = None,
    ) -> None:
        self._session = session
        self._po_type = po_type
        self._actor = actor
        self._interceptor_chain = interceptor_chain
    
    # PO 操作方法
    async def get_po_by_id(self, id: ID) -> PO | None:
        """获取 PO"""
        return await self._session.get(self._po_type, id)
    
    async def create_po(self, po: PO) -> PO:
        """创建 PO"""
        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.CREATE,
                entity=po,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)
        
        self._session.add(po)
        await self._session.flush()
        
        if self._interceptor_chain:
            po = await self._interceptor_chain.process_result(context, po)
        
        return po
    
    async def update_po(self, po: PO) -> PO:
        """更新 PO"""
        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.UPDATE,
                entity=po,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)
        
        merged = await self._session.merge(po)
        await self._session.flush()
        
        if self._interceptor_chain:
            merged = await self._interceptor_chain.process_result(context, merged)
        
        return merged
    
    async def delete_po(self, po: PO) -> None:
        """删除 PO"""
        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.DELETE,
                entity=po,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)
        
        await self._session.delete(po)
        await self._session.flush()
    
    async def query_po_by_spec(
        self, spec: CompositeSpecification[PO]
    ) -> list[PO]:
        """使用 Specification 查询 PO"""
        # 使用 QueryBuilder 执行查询
        # 简化版实现
        stmt = select(self._po_type)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    # 批量操作
    async def batch_po_create(self, pos: list[PO]) -> list[PO]:
        """批量创建"""
        # ...实现
        pass
    
    async def batch_po_update(self, pos: list[PO]) -> list[PO]:
        """批量更新"""
        # ...实现
        pass
    
    async def batch_po_delete(self, pos: list[PO]) -> None:
        """批量删除"""
        # ...实现
        pass
```

### 4. RepositoryAdapter (核心适配器)

**位置**: `src/infrastructure/repository/adapter.py`

```python
from typing import Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ports.repository import Repository as IRepository
from application.ports.mapper import BidirectionalMapper
from persistence.repository.sqlalchemy import BaseRepository
from persistence.specification import CompositeSpecification, Page, PageParams

AR = TypeVar("AR")  # Aggregate Root
PO = TypeVar("PO")  # Persistence Object
ID = TypeVar("ID")


class RepositoryAdapter(Generic[AR, PO, ID], IRepository[AR]):
    """Repository Adapter - 实现 Domain Repository Port
    
    职责：
    1. 实现 domain.ports.Repository Protocol
    2. 使用 Mapper 进行 AR ↔ PO 转换
    3. 委托给 BaseRepository 执行数据库操作
    4. 处理异常和日志
    
    Example:
        ```python
        class UserRepositoryAdapter(RepositoryAdapter[User, UserPO, str]):
            def __init__(self, session: AsyncSession, actor: str = "system"):
                mapper = UserPOMapper()  # AR ↔ PO 映射器
                base_repo = BaseRepository(
                    session=session,
                    po_type=UserPO,
                    actor=actor,
                    interceptor_chain=create_default_chain(actor)
                )
                super().__init__(base_repo, mapper)
        ```
    """
    
    def __init__(
        self,
        repository: BaseRepository[PO, ID],
        mapper: BidirectionalMapper[AR, PO],
    ) -> None:
        """初始化适配器
        
        Args:
            repository: PO 操作的 Repository
            mapper: AR ↔ PO 映射器
        """
        self._repository = repository
        self._mapper = mapper
    
    # ==================== IRepository Implementation ====================
    
    async def get(self, id: ID) -> AR | None:
        """获取聚合根
        
        流程: DB → PO → AR
        """
        po = await self._repository.get_po_by_id(id)
        if po is None:
            return None
        return self._mapper.map_reverse(po)  # PO → AR
    
    async def save(self, aggregate: AR) -> None:
        """保存聚合根
        
        流程: AR → PO → DB
        """
        entity_id = getattr(aggregate, "id", None)
        
        if entity_id is None:
            # Create
            po = self._mapper.map(aggregate)  # AR → PO
            await self._repository.create_po(po)
        else:
            # Update
            po = self._mapper.map(aggregate)  # AR → PO
            await self._repository.update_po(po)
    
    async def list(
        self, specification: CompositeSpecification[AR] | None = None
    ) -> list[AR]:
        """列表查询"""
        if specification is None:
            # 查询全部（需要创建空 Specification）
            pos = await self._repository.query_po_by_spec(
                CompositeSpecification()
            )
        else:
            # 转换 Specification: AR → PO
            po_spec = self._convert_spec_to_po(specification)
            pos = await self._repository.query_po_by_spec(po_spec)
        
        # PO → AR
        return self._mapper.map_reverse_list(pos)
    
    # ==================== Extended Query Methods ====================
    
    async def find_one(
        self, specification: CompositeSpecification[AR]
    ) -> AR | None:
        """查找单个"""
        limited_spec = specification.with_page(PageParams(page=1, size=1))
        results = await self.find_all(limited_spec)
        return results[0] if results else None
    
    async def find_all(
        self, specification: CompositeSpecification[AR]
    ) -> list[AR]:
        """查找全部"""
        po_spec = self._convert_spec_to_po(specification)
        pos = await self._repository.query_po_by_spec(po_spec)
        return self._mapper.map_reverse_list(pos)
    
    async def find_page(
        self,
        specification: CompositeSpecification[AR],
        page_params: PageParams,
    ) -> Page[AR]:
        """分页查询"""
        # 1. 统计总数
        total = await self.count(specification)
        
        if total == 0:
            return Page.create(items=[], total=0, page=1, size=page_params.size)
        
        # 2. 查询分页数据
        paged_spec = specification.with_page(page_params)
        po_spec = self._convert_spec_to_po(paged_spec)
        pos = await self._repository.query_po_by_spec(po_spec)
        
        # 3. 转换 PO → AR
        items = self._mapper.map_reverse_list(pos)
        
        return Page.create(
            items=items,
            total=total,
            page=page_params.page,
            size=page_params.size,
        )
    
    async def count(self, specification: CompositeSpecification[AR]) -> int:
        """计数"""
        po_spec = self._convert_spec_to_po(specification)
        # 使用 Repository 的 count 方法
        # 简化版：实际需要实现
        return 0
    
    async def exists(self, specification: CompositeSpecification[AR]) -> bool:
        """存在性检查"""
        count = await self.count(specification)
        return count > 0
    
    async def delete(self, aggregate: AR) -> None:
        """删除聚合根"""
        po = self._mapper.map(aggregate)  # AR → PO
        await self._repository.delete_po(po)
    
    # ==================== Batch Operations ====================
    
    async def save_all(self, aggregates: list[AR]) -> None:
        """批量保存"""
        pos = self._mapper.map_list(aggregates)  # AR → PO
        await self._repository.batch_po_create(pos)
    
    async def delete_all(self, aggregates: list[AR]) -> None:
        """批量删除"""
        pos = self._mapper.map_list(aggregates)  # AR → PO
        await self._repository.batch_po_delete(pos)
    
    # ==================== Helper Methods ====================
    
    def _convert_spec_to_po(
        self, ar_spec: CompositeSpecification[AR]
    ) -> CompositeSpecification[PO]:
        """转换 Specification: AR → PO
        
        注意：Specification 的字段名需要保持一致
        或者使用字段映射机制
        """
        # 简化版：直接返回
        # 完整实现需要处理字段映射
        return CompositeSpecification(
            filters=ar_spec.filters,
            groups=ar_spec.groups,
            sorts=ar_spec.sorts,
            page=ar_spec.page,
            fields=ar_spec.fields,
            includes=ar_spec.includes,
            statistics=ar_spec.statistics,
            group_by=ar_spec.group_by,
            having=ar_spec.having,
            joins=ar_spec.joins,
        )
```

---

## 💡 使用示例

### 完整使用流程

```python
# ==================== 1. 定义领域模型 ====================
# Domain Layer
from domain.entity import AggregateRoot
from domain.value_object import ValueObject

class UserId(ValueObject):
    value: str

class User(AggregateRoot):
    id: UserId
    name: str
    email: str
    is_active: bool


# ==================== 2. 定义 PO ====================
# Infrastructure Layer
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserPO(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    is_active = Column(Boolean)
    
    # Audit fields (自动维护)
    created_at = Column(DateTime)
    created_by = Column(String)
    updated_at = Column(DateTime)
    updated_by = Column(String)


# ==================== 3. 定义 Mapper ====================
# Infrastructure Layer
from infrastructure.mapper import POMapper

class UserPOMapper(POMapper[User, UserPO]):
    def __init__(self):
        super().__init__(
            domain_type=User,
            po_type=UserPO,
            auto_map=True  # 自动映射
        )
    
    # 如果需要自定义映射，可以重写
    def _custom_map_to_po(self, user: User) -> UserPO:
        return UserPO(
            id=user.id.value,  # ValueObject 转换
            name=user.name,
            email=user.email,
            is_active=user.is_active,
        )
    
    def _custom_map_to_domain(self, po: UserPO) -> User:
        return User(
            id=UserId(po.id),  # 转换为 ValueObject
            name=po.name,
            email=po.email,
            is_active=po.is_active,
        )


# ==================== 4. 定义 Repository ====================
# Infrastructure Layer
from infrastructure.repository import RepositoryAdapter
from persistence.repository import BaseRepository
from persistence.interceptor import create_default_chain

class UserRepository(RepositoryAdapter[User, UserPO, str]):
    def __init__(self, session: AsyncSession, actor: str = "system"):
        # 创建 Mapper
        mapper = UserPOMapper()
        
        # 创建 BaseRepository
        base_repo = BaseRepository(
            session=session,
            po_type=UserPO,
            actor=actor,
            interceptor_chain=create_default_chain(actor)
        )
        
        # 初始化 Adapter
        super().__init__(base_repo, mapper)


# ==================== 5. 使用 Repository ====================
# Application Layer
async def main():
    # 创建 Repository
    repo = UserRepository(session, actor="admin@example.com")
    
    # 创建用户
    user = User(
        id=UserId("user-001"),
        name="John Doe",
        email="john@example.com",
        is_active=True
    )
    await repo.save(user)  # AR → PO → DB
    
    # 查询用户
    user = await repo.get("user-001")  # DB → PO → AR
    print(user.name)  # "John Doe"
    
    # Specification 查询
    spec = (EntitySpecificationBuilder()
        .is_active()
        .order_by("created_at", "desc")
        .build())
    
    users = await repo.find_all(spec)  # DB → PO → AR
    
    # 分页查询
    page = await repo.find_page(
        spec,
        PageParams(page=1, size=20)
    )
    
    # 更新用户
    user.name = "Jane Doe"
    await repo.save(user)  # AR → PO → DB (Interceptor 自动更新 updated_at)
    
    # 删除用户
    await repo.delete(user)  # AR → PO → 软删除 (Interceptor 处理)
```

---

## 🔧 集成方案

### Phase 2 代码调整

#### 调整 1: BaseRepository 重构

```python
# 当前 (Phase 2)
class BaseRepository(Generic[T, ID], IRepository[T]):
    ...

# 重构后
class BaseRepository(Generic[PO, ID]):
    # 移除 IRepository 继承
    # 专注于 PO 操作
    ...
```

#### 调整 2: 创建 Mapper Port

```python
# 新文件: src/application/ports/mapper.py
class BidirectionalMapper(Protocol[S, T]):
    def map(self, source: S) -> T: ...
    def map_reverse(self, target: T) -> S: ...
    def map_list(self, sources: list[S]) -> list[T]: ...
    def map_reverse_list(self, targets: list[T]) -> list[S]: ...
```

#### 调整 3: 实现 POMapper

```python
# 新文件: src/infrastructure/mapper/po_mapper.py
class POMapper(Generic[D, P], BidirectionalMapper[D, P]):
    ...
```

#### 调整 4: 实现 RepositoryAdapter

```python
# 新文件: src/infrastructure/repository/adapter.py
class RepositoryAdapter(Generic[AR, PO, ID], IRepository[AR]):
    ...
```

### 文件结构

```
src/
├── application/
│   └── ports/
│       ├── __init__.py
│       ├── uow.py (已存在)
│       ├── cache.py (已存在)
│       ├── message_bus.py (已存在)
│       └── mapper.py (新增) ⭐
├── infrastructure/
│   ├── mapper/
│   │   ├── __init__.py (新增) ⭐
│   │   └── po_mapper.py (新增) ⭐
│   └── repository/
│       ├── __init__.py (新增) ⭐
│       └── adapter.py (新增) ⭐
└── persistence/
    ├── repository/
    │   └── sqlalchemy/
    │       └── base.py (调整) 🔧
    └── ...
```

---

## 📊 工作量评估

### 核心任务

| 任务 | 文件 | 代码行数 | 预计时间 |
|------|------|----------|----------|
| Mapper Protocol | `application/ports/mapper.py` | ~100 | 30 分钟 |
| POMapper 基类 | `infrastructure/mapper/po_mapper.py` | ~200 | 1 小时 |
| RepositoryAdapter | `infrastructure/repository/adapter.py` | ~300 | 1.5 小时 |
| BaseRepository 调整 | `persistence/repository/sqlalchemy/base.py` | ~50 (修改) | 30 分钟 |
| 测试代码 | `tests/...` | ~200 | 1 小时 |
| 文档更新 | `docs/...` | - | 30 分钟 |

**总计**: 约 **5 小时** (包含测试和文档)

### 依赖关系

- ✅ **Phase 2** 已完成：Specification, Interceptor, BaseRepository
- 🟡 **本次**：Mapper Protocol, POMapper, RepositoryAdapter
- 🔵 **Phase 3** (可选)：高级 Mapper 功能（自动映射、字段映射、嵌套映射等）

---

## ✅ 优势总结

### 架构优势

1. ✅ **完全遵循 DDD 分层**
   - Domain 层完全不知道 PO
   - Infrastructure 层负责映射

2. ✅ **符合六边形架构**
   - Repository Port (Domain)
   - Repository Adapter (Infrastructure)
   - Mapper Port (Application)

3. ✅ **类型安全**
   - 泛型支持: `RepositoryAdapter[AR, PO, ID]`
   - Protocol-based: `BidirectionalMapper[S, T]`

4. ✅ **关注点分离**
   - BaseRepository: 纯 PO 操作
   - Mapper: AR ↔ PO 转换
   - Adapter: 编排和适配

5. ✅ **可测试性**
   - 每个组件可独立测试
   - Mock 友好

6. ✅ **可扩展性**
   - Mapper 可自定义
   - Adapter 可继承

### 实现优势

1. ✅ **批量操作优化**
   - `map_list()` 批量转换
   - 减少循环开销

2. ✅ **错误处理**
   - 统一的异常处理
   - 清晰的错误信息

3. ✅ **日志追踪**
   - Adapter 层统一日志

4. ✅ **性能**
   - Mapper 可缓存
   - 批量转换优化

---

## 🎯 结论

### 推荐方案

**立即实现 Adapter + Mapper 系统**

**理由**:
1. ✅ 补全 Phase 2 的架构缺失
2. ✅ 保证 DDD 分层的完整性
3. ✅ 为后续开发打下坚实基础
4. ✅ 工作量可控（约 5 小时）

### 下一步行动

如果您同意此方案，我将立即开始：

1. 创建 Mapper Protocol (`application/ports/mapper.py`)
2. 实现 POMapper (`infrastructure/mapper/po_mapper.py`)
3. 实现 RepositoryAdapter (`infrastructure/repository/adapter.py`)
4. 调整 BaseRepository
5. 编写示例和测试
6. 更新文档

**准备好了吗？** 🚀

