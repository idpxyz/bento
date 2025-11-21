# 📚 Repository Pattern 实现指南

## 🎯 关于继承 Bento 的 Repository 协议

### 问题：IOrderRepository 需要继承 Repository 吗？

**简短回答：可以但不是必须。**

---

## 📐 两种实现方式

### 方式 1：继承 Bento Repository（推荐用于新项目）✅

```python
from bento.core.ids import ID
from bento.domain.ports.repository import Repository
from typing import Protocol

class IOrderRepository(Repository[Order, ID], Protocol):
    """继承 Bento 的 Repository 协议"""

    # 自动获得标准方法：
    # - get(id: ID) -> Order | None
    # - save(entity: Order) -> Order
    # - delete(entity: Order) -> None
    # - find_all() -> list[Order]
    # - exists(id: ID) -> bool
    # - count() -> int

    # 添加领域特定方法
    async def find_by_customer(self, customer_id: str) -> list[Order]:
        ...
```

**优点：**
- ✅ 与 Bento 框架完全一致
- ✅ 自动获得标准方法签名
- ✅ 类型检查更严格
- ✅ 符合框架约定

**缺点：**
- ❌ 需要使用 `ID` 类型而不是 `str`
- ❌ 可能需要迁移现有代码

---

### 方式 2：使用 Protocol（当前实现）✅

```python
from typing import Protocol

class IOrderRepository(Protocol):
    """独立的 Protocol，参考 Bento 标准"""

    # 手动定义标准方法（参考 Bento 的 Repository）
    async def get(self, id: str) -> Order | None: ...
    async def save(self, order: Order) -> None: ...
    async def delete(self, order: Order) -> None: ...
    async def find_all(self) -> list[Order]: ...
    async def exists(self, id: str) -> bool: ...
    async def count(self) -> int: ...

    # 领域特定方法
    async def find_by_customer(self, customer_id: str) -> list[Order]: ...
```

**优点：**
- ✅ 灵活性高
- ✅ 可以使用简单的 `str` 作为 ID
- ✅ 不需要修改现有代码
- ✅ 仍然符合六边形架构

**缺点：**
- ❌ 需要手动保持与 Bento 标准一致
- ❌ 类型检查稍弱

---

## 🎯 当前 Ordering BC 的实现

我们选择了**方式 2**，原因：

1. **Order 使用 str 作为 ID**
   ```python
   @dataclass
   class Order(AggregateRoot):
       id: str  # 使用简单的 str
   ```

2. **避免大规模重构**
   - 保持现有代码兼容
   - OrderPO 使用 str 主键
   - 不需要迁移所有 ID 类型

3. **参考 Bento 标准**
   - 方法签名与 Bento Repository 保持一致
   - 遵循相同的命名约定
   - 保持架构原则

---

## 📊 Bento Repository 标准方法

| 方法 | 签名 | 说明 |
|-----|------|------|
| `get` | `async def get(id: ID) -> E \| None` | 根据 ID 获取实体 |
| `save` | `async def save(entity: E) -> E` | 保存实体（创建或更新）|
| `delete` | `async def delete(entity: E) -> None` | 删除实体 |
| `find_all` | `async def find_all() -> list[E]` | 查询所有实体 |
| `exists` | `async def exists(id: ID) -> bool` | 检查是否存在 |
| `count` | `async def count() -> int` | 统计总数 |

我们的 `IOrderRepository` 保持了相同的方法名和语义。

---

## 🔍 实现对比

### Identity BC（使用 Bento Repository）

```python
# identity/domain/ports/user_repository.py
from bento.domain.ports.repository import Repository
from bento.core.ids import ID

class UserRepository(Repository[User, ID], Protocol):
    """继承 Bento Repository"""
    pass
```

### Ordering BC（使用独立 Protocol）

```python
# ordering/domain/ports/repositories/i_order_repository.py
from typing import Protocol

class IOrderRepository(Protocol):
    """独立 Protocol，参考 Bento 标准"""
    async def get(self, id: str) -> Order | None: ...
    async def save(self, order: Order) -> None: ...
    # ...
```

**两种方式都正确！** ✅

---

## 💡 选择建议

### 新项目 → 继承 Repository

```python
# ✅ 推荐：新项目从一开始使用 Bento ID
from bento.core.ids import ID
from bento.domain.ports.repository import Repository

class IOrderRepository(Repository[Order, ID], Protocol):
    pass
```

### 现有项目 → 独立 Protocol

```python
# ✅ 推荐：现有项目保持兼容性
from typing import Protocol

class IOrderRepository(Protocol):
    """参考 Bento 标准实现"""
    async def get(self, id: str) -> Order | None: ...
    # ...
```

---

## 🏗️ 实现示例

### 当前的 OrderRepository 实现

```python
# infrastructure/repositories/order_repository_impl.py
from bento.infrastructure.repository import RepositoryAdapter

class OrderRepository(RepositoryAdapter[Order, OrderPO, ID]):
    """实现 IOrderRepository"""

    async def get(self, order_id: str) -> Order | None:
        # 加载 Order + OrderItems（聚合）
        order = await super().get(order_id)
        if not order:
            return None

        # 加载 OrderItems
        items = await self._load_items(order_id)
        order.items = items

        return order

    async def save(self, order: Order) -> None:
        # 保存 Order
        await super().save(order)

        # 级联保存 OrderItems
        await self._save_items(order)

    # 其他方法...
```

---

## 📋 检查清单

### ✅ 符合六边形架构

- ✅ Port（接口）在 Domain 层
- ✅ Adapter（实现）在 Infrastructure 层
- ✅ Application 层依赖 Port，不依赖 Adapter

### ✅ 符合 DDD 原则

- ✅ Repository 只为聚合根创建（Order）
- ✅ 不为实体创建 Repository（OrderItem）
- ✅ 通过聚合根访问聚合内实体

### ✅ 符合 Bento 标准

- ✅ 方法签名与 Bento Repository 一致
- ✅ 使用 RepositoryAdapter 实现
- ✅ 集成审计、软删除、乐观锁

---

## 🎯 总结

### 关于继承的建议

| 情况 | 建议 | 原因 |
|-----|------|------|
| **新项目** | 继承 `Repository[E, ID]` | 与框架完全一致 |
| **现有项目** | 独立 `Protocol` | 避免大规模重构 |
| **使用 str ID** | 独立 `Protocol` | Bento Repository 需要 EntityId |
| **使用 ID 类型** | 继承 `Repository[E, ID]` | 类型完全匹配 |

### 核心原则

不管选择哪种方式，关键是：

1. ✅ **遵循依赖倒置原则**（DIP）
2. ✅ **Port 在 Domain 层**
3. ✅ **Adapter 在 Infrastructure 层**
4. ✅ **Application 依赖抽象而非实现**
5. ✅ **参考 Bento 标准方法**

**当前实现完全符合以上原则！** 🎯

---

## 📚 参考

- Bento Repository Protocol: `bento/domain/ports/repository.py`
- Identity BC Repository: `identity/domain/ports/user_repository.py`
- Ordering BC Repository: `ordering/domain/ports/repositories/i_order_repository.py`

---

**结论：不继承也可以，只要遵循标准方法签名即可！** ✅
