# Repository Adapter 对比指南

**版本**: 1.0  
**日期**: 2025-11-04

---

## 📊 快速对比

| 特性 | RepositoryAdapter | SimpleRepositoryAdapter |
|------|-------------------|------------------------|
| **AR 和 PO** | 分离（不同对象） | 相同（同一对象） |
| **需要 Mapper** | ✅ 是 | ❌ 否 |
| **复杂度** | ⭐⭐⭐⭐⭐ 高 | ⭐⭐ 低 |
| **性能** | ⭐⭐⭐ 中（有转换） | ⭐⭐⭐⭐⭐ 高（无转换） |
| **适用场景** | 复杂业务、核心域 | 简单 CRUD、辅助域 |
| **代码量** | 多（4 个类） | 少（2 个类） |

---

## 🎯 选择指南

### 使用 RepositoryAdapter（完整版）

✅ **复杂业务逻辑**
```python
# AR 有复杂的 ValueObject 和嵌套结构
class Order(AggregateRoot):
    id: OrderId  # ValueObject
    customer: Customer  # 复杂对象
    items: list[OrderItem]  # 嵌套集合

# PO 需要扁平化
class OrderPO(Base):
    id = Column(String)
    customer_id = Column(String)
    # 需要单独的表存储 items
```

✅ **需要严格隔离**
- Domain 层绝不能依赖 SQLAlchemy
- 需要支持多种持久化方案
- 完整的 DDD 实践

✅ **核心域实体**
- 订单、支付、库存等
- 需要领域专家参与
- 业务逻辑复杂

### 使用 SimpleRepositoryAdapter（简化版）⭐

✅ **简单 CRUD 实体**
```python
# AR = PO（同一对象）
class User(DeclarativeBase, AggregateRoot):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
```

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
- 字典表

---

## 💻 代码对比

### 完整版 RepositoryAdapter

```python
# 1. Domain
class Order(AggregateRoot):
    id: OrderId
    customer: Customer
    items: list[OrderItem]

# 2. PO
class OrderPO(Base):
    id = Column(String)
    customer_id = Column(String)

# 3. Mapper
class OrderPOMapper(POMapper[Order, OrderPO]):
    def _map_to_po(self, order: Order) -> OrderPO:
        return OrderPO(
            id=order.id.value,
            customer_id=order.customer.id.value
        )

# 4. Repository
class OrderRepository(RepositoryAdapter[Order, OrderPO, str]):
    def __init__(self, session, actor):
        mapper = OrderPOMapper()
        base_repo = BaseRepository(session, OrderPO, actor)
        super().__init__(base_repo, mapper)

# 总计：4 个类，约 200+ 行代码
```

### 简化版 SimpleRepositoryAdapter ⭐

```python
# 1. Domain + PO（同一对象）
class User(DeclarativeBase, AggregateRoot):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)

# 2. Repository（无需 Mapper）
class UserRepository(SimpleRepositoryAdapter[User, str]):
    def __init__(self, session, actor):
        base_repo = BaseRepository(session, User, actor)
        super().__init__(base_repo)

# 总计：2 个类，约 50 行代码
```

---

## 🔄 迁移路径

### 从小型 → 大型的平滑迁移

```python
# 阶段 1: MVP（简化版）
class UserRepository(SimpleRepositoryAdapter[User, str]):
    def __init__(self, session, actor):
        base_repo = BaseRepository(session, User, actor)
        super().__init__(base_repo)

# 阶段 2: 业务复杂化（切换到完整版）
# 1. 分离 PO
class UserPO(Base):
    id = Column(String)
    name = Column(String)

# 2. 创建 Mapper
class UserPOMapper(POMapper[User, UserPO]):
    ...

# 3. 切换 Adapter
class UserRepository(RepositoryAdapter[User, UserPO, str]):
    def __init__(self, session, actor):
        mapper = UserPOMapper()
        base_repo = BaseRepository(session, UserPO, actor)
        super().__init__(base_repo, mapper)

# Application 层代码无需修改！
# repo.get(), repo.save() 等 API 完全一致
```

---

## 📈 性能对比

### 查询 10000 条记录

**RepositoryAdapter**:
```
Database → PO (10000) → Mapper → AR (10000)
          ↑                      ↑
      创建 10000 个 PO      创建 10000 个 AR
内存占用：2x
```

**SimpleRepositoryAdapter**:
```
Database → AR (10000)
          ↑
      只创建 10000 个对象
内存占用：1x（节省 50%）
```

---

## ✅ 最佳实践

### 推荐策略

1. **MVP / 原型**: SimpleRepositoryAdapter
2. **核心域**: RepositoryAdapter
3. **辅助域**: SimpleRepositoryAdapter
4. **性能敏感**: SimpleRepositoryAdapter

### 项目结构建议

```
src/
└── infrastructure/
    └── repository/
        ├── adapters/
        │   ├── order_repository.py      # 完整版（核心域）
        │   ├── user_repository.py      # 简化版（简单实体）
        │   └── audit_log_repository.py # 简化版（辅助域）
```

---

## 🎓 总结

### 设计优势

✅ **保持一致性**: 两个 Adapter 实现相同的 Protocol  
✅ **降低门槛**: 简化版让新手快速上手  
✅ **灵活选择**: 根据场景选择合适的实现  
✅ **平滑迁移**: 可以从小型 → 大型演进  
✅ **性能优化**: 简化版无转换开销  

### 使用建议

- **简单项目**: 优先使用 SimpleRepositoryAdapter
- **复杂项目**: 核心域用 RepositoryAdapter，辅助域用 SimpleRepositoryAdapter
- **性能敏感**: 使用 SimpleRepositoryAdapter
- **学习阶段**: 从 SimpleRepositoryAdapter 开始，逐步理解完整版

---

**这个设计非常合理！既保持了架构的完整性，又提供了灵活性！** 🎉

