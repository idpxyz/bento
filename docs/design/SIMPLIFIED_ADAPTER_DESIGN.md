# 简化版 Adapter 设计方案

**版本**: 1.0  
**日期**: 2025-11-04  
**设计理念**: 渐进式架构，保持一致性

---

## 🎯 设计目标

### 核心思想

提供**两个 Adapter 实现**，都实现相同的 `domain.ports.Repository` Protocol：

1. **RepositoryAdapter** (完整版) - 适合复杂业务
   - AR ≠ PO 分离
   - 需要 Mapper 转换
   - 完全符合严格 DDD

2. **SimpleRepositoryAdapter** (简化版) - 适合简单项目 ⭐ 新增
   - AR = PO (同一对象)
   - 无需 Mapper
   - 降低复杂度

### 优势

✅ **API 一致性**: 两个 Adapter 实现相同的 Protocol  
✅ **渐进式**: 可以从小型 → 大型平滑迁移  
✅ **灵活性**: 根据项目复杂度选择  
✅ **降低门槛**: 简化版降低学习曲线  

---

## 🏗️ 架构设计

### 简化版 Adapter 设计

```python
# 假设：AR = PO（同一对象）
class SimpleRepositoryAdapter(Generic[T, ID], IRepository[T]):
    """简化版 Repository Adapter
    
    适用于：
    - AR 和 PO 是同一个对象
    - 简单的 CRUD 应用
    - 快速开发场景
    
    使用 SQLAlchemy DeclarativeBase + AggregateRoot
    """
    
    def __init__(
        self,
        repository: BaseRepository[T, ID],  # T 既是 AR 也是 PO
    ):
        self._repository = repository
    
    async def get(self, id: ID) -> T | None:
        # 直接返回，无需转换
        return await self._repository.get_po_by_id(id)
    
    async def save(self, aggregate: T) -> None:
        # 直接保存，无需转换
        entity_id = getattr(aggregate, "id", None)
        if entity_id is None:
            await self._repository.create_po(aggregate)
        else:
            await self._repository.update_po(aggregate)
```

### 对比

| 特性 | RepositoryAdapter (完整版) | SimpleRepositoryAdapter (简化版) |
|------|---------------------------|--------------------------------|
| **AR 类型** | `AggregateRoot` | `AggregateRoot + DeclarativeBase` |
| **PO 类型** | 单独的 SQLAlchemy 模型 | 与 AR 相同 |
| **Mapper** | 需要 | 不需要 |
| **复杂度** | 高 | 低 |
| **性能** | 中等（有转换开销） | 高（无转换） |
| **适用场景** | 复杂业务、AR≠PO | 简单 CRUD、AR=PO |

---

## 📋 实现方案

### 方案 1: 直接委托（推荐）

```python
class SimpleRepositoryAdapter(Generic[T, ID], IRepository[T]):
    """简化版 Repository Adapter
    
    直接委托给 BaseRepository，无需 Mapper。
    适用于 AR = PO 的场景。
    """
    
    def __init__(
        self,
        repository: BaseRepository[T, ID],
    ):
        self._repository = repository
    
    # 所有方法直接委托，无需转换
    async def get(self, id: ID) -> T | None:
        return await self._repository.get_po_by_id(id)
    
    async def save(self, aggregate: T) -> None:
        entity_id = getattr(aggregate, "id", None)
        existing = await self._repository.get_po_by_id(entity_id) if entity_id else None
        
        if existing is None:
            await self._repository.create_po(aggregate)
        else:
            await self._repository.update_po(aggregate)
    
    async def list(self, spec: CompositeSpecification[T] | None = None) -> list[T]:
        if spec is None:
            spec = CompositeSpecification()
        return await self._repository.query_po_by_spec(spec)
    
    # ... 其他方法类似
```

### 方案 2: 继承 BaseRepository（备选）

```python
class SimpleRepositoryAdapter(BaseRepository[T, ID], IRepository[T]):
    """简化版 - 继承 BaseRepository"""
    
    # 直接实现 IRepository 方法
    async def get(self, id: ID) -> T | None:
        return await self.get_po_by_id(id)
    
    # ...
```

**推荐方案 1**，因为：
- ✅ 职责更清晰（委托 vs 继承）
- ✅ 保持 BaseRepository 的纯净性
- ✅ 更容易测试

---

## 💡 使用示例

### 完整版（复杂业务）

```python
# Domain
class Order(AggregateRoot):
    id: OrderId  # ValueObject
    customer: Customer  # 复杂对象
    items: list[OrderItem]  # 嵌套集合

# PO
class OrderPO(Base):
    id = Column(String)
    customer_id = Column(String)
    # ... 扁平化结构

# Mapper
class OrderPOMapper(POMapper[Order, OrderPO]):
    def _map_to_po(self, order: Order) -> OrderPO:
        # 复杂转换逻辑
        ...

# Repository
class OrderRepository(RepositoryAdapter[Order, OrderPO, str]):
    def __init__(self, session, actor):
        mapper = OrderPOMapper()
        base_repo = BaseRepository(session, OrderPO, actor)
        super().__init__(base_repo, mapper)
```

### 简化版（简单业务）⭐

```python
# Domain + PO（同一对象）
from sqlalchemy.orm import DeclarativeBase
from domain.entity import AggregateRoot

class User(DeclarativeBase, AggregateRoot):  # AR = PO
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    is_active = Column(Boolean)
    
    # 业务方法
    def activate(self):
        self.is_active = True
    
    def deactivate(self):
        self.is_active = False

# Repository（无需 Mapper）
class UserRepository(SimpleRepositoryAdapter[User, str]):
    def __init__(self, session: AsyncSession, actor: str = "system"):
        base_repo = BaseRepository(
            session=session,
            po_type=User,  # 注意：这里用 User 本身
            actor=actor,
            interceptor_chain=create_default_chain(actor)
        )
        super().__init__(repository=base_repo)

# 使用（API 完全一致）
repo = UserRepository(session, actor="admin")
user = await repo.get("user-001")  # 直接返回 User，无需转换
await repo.save(user)  # 直接保存 User
```

---

## 🎯 选择指南

### 何时使用完整版 RepositoryAdapter

✅ **AR 和 PO 结构差异大**
- AR 有复杂的 ValueObject
- AR 有嵌套集合
- AR 需要业务逻辑转换

✅ **需要严格隔离**
- Domain 层绝不能依赖 SQLAlchemy
- 需要支持多种持久化方案
- 需要完整的 DDD 实践

✅ **复杂业务逻辑**
- 订单、支付、库存等核心域
- 需要领域专家参与

### 何时使用简化版 SimpleRepositoryAdapter ⭐

✅ **AR 和 PO 结构一致**
- 简单的 CRUD 实体
- 字段直接对应

✅ **快速开发**
- MVP 阶段
- 原型开发
- 小团队项目

✅ **性能敏感**
- 高并发场景
- 大数据量查询
- 需要避免转换开销

✅ **辅助域/支撑域**
- 审计日志
- 配置表
- 简单的字典表

---

## 📊 迁移路径

### 渐进式演进

```
阶段 1: MVP (简化版)
UserRepository(SimpleRepositoryAdapter)
    ↓
阶段 2: 业务复杂化 (切换到完整版)
UserRepository(RepositoryAdapter) + UserPOMapper
    ↓
阶段 3: 核心域严格化
OrderRepository(RepositoryAdapter) + OrderPOMapper
```

### 代码迁移示例

```python
# 阶段 1: 简化版
class UserRepository(SimpleRepositoryAdapter[User, str]):
    def __init__(self, session, actor):
        base_repo = BaseRepository(session, User, actor)
        super().__init__(base_repo)

# 阶段 2: 切换到完整版（只需修改 Repository）
class UserRepository(RepositoryAdapter[User, UserPO, str]):
    def __init__(self, session, actor):
        # 1. 创建 UserPO（分离 PO）
        # 2. 创建 UserPOMapper
        # 3. 使用完整版 Adapter
        mapper = UserPOMapper()
        base_repo = BaseRepository(session, UserPO, actor)
        super().__init__(base_repo, mapper)

# Application 层代码无需修改！
# repo.get(), repo.save() 等 API 完全一致
```

---

## ✅ 优势总结

### 1. 保持一致性 ⭐⭐⭐⭐⭐

```python
# 两个 Adapter 实现相同的 Protocol
repo: IRepository[User]  # 可以是 Simple 或 完整版

# Application 层代码完全一致
user = await repo.get(id)
await repo.save(user)
```

### 2. 降低门槛 ⭐⭐⭐⭐⭐

```python
# 新手可以快速上手
class UserRepository(SimpleRepositoryAdapter[User, str]):
    # 无需理解 Mapper
    # 无需创建 PO
    # 直接使用
```

### 3. 渐进式演进 ⭐⭐⭐⭐⭐

```python
# 从小型 → 大型平滑迁移
# 代码无需大量重构
# 只需要切换 Adapter 实现
```

### 4. 性能优化 ⭐⭐⭐⭐

```python
# 简化版：无转换开销
# 适合高并发场景
```

---

## 🎓 最佳实践

### 推荐策略

1. **MVP 阶段**: 使用 SimpleRepositoryAdapter
2. **核心域**: 使用 RepositoryAdapter（完整版）
3. **辅助域**: 使用 SimpleRepositoryAdapter
4. **性能敏感**: 使用 SimpleRepositoryAdapter

### 代码组织

```
src/
├── infrastructure/
│   └── repository/
│       ├── adapter.py          # 完整版
│       ├── simple_adapter.py   # 简化版 ⭐ 新增
│       └── __init__.py
```

---

## 📝 总结

### 设计评估

✅ **非常合理**: 渐进式架构，保持一致性  
✅ **降低门槛**: 简化版让新手快速上手  
✅ **灵活选择**: 根据场景选择合适的实现  
✅ **平滑迁移**: 可以从小型 → 大型演进  

### 建议

**立即实现 SimpleRepositoryAdapter**，这样：

1. ✅ 框架更完整（支持两种场景）
2. ✅ 降低使用门槛（新手友好）
3. ✅ 保持 API 一致性（无缝切换）
4. ✅ 提供最佳实践（渐进式演进）

---

**这个设计非常棒！让我立即实现它！** 🚀

