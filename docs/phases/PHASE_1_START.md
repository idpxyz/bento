# Phase 1: 端口层定义 - 启动指南

## 📋 阶段概览

**阶段**: Phase 1 - 端口层定义  
**预计时长**: 2-3 周  
**开始时间**: 待定  
**状态**: ⏳ 待开始  

---

## 🎯 阶段目标

定义所有端口（Port）接口，建立领域和应用层的契约。所有端口必须使用 `Protocol` 定义，确保依赖反转原则。

---

## 📋 任务清单

### 1.1 Domain Ports（1 周）

#### Task 1.1.1: Repository Port
**文件**: `src/domain/ports/repository.py`

**参考**: 
- `old/adapter/repository.py`
- 当前 `src/domain/repository.py`

**要求**:
```python
from typing import Protocol, TypeVar, Generic, Optional, List
from bento.core.ids import EntityId
from bento.domain.entity import Entity

E = TypeVar("E", bound=Entity, contravariant=True)
ID = TypeVar("ID", bound=EntityId)

class Repository(Protocol, Generic[E, ID]):
    """Repository 端口 - 领域层定义的契约"""
    
    async def find_by_id(self, id: ID) -> Optional[E]:
        """Find entity by ID."""
        ...
    
    async def save(self, entity: E) -> E:
        """Save entity."""
        ...
    
    async def delete(self, entity: E) -> None:
        """Delete entity."""
        ...
    
    async def find_all(self) -> List[E]:
        """Find all entities."""
        ...
```

**验收标准**:
- [ ] Protocol 定义正确
- [ ] 泛型类型正确
- [ ] 方法签名完整
- [ ] mypy 检查通过
- [ ] import-linter 检查通过

---

#### Task 1.1.2: Specification Port
**文件**: `src/domain/ports/specification.py`

**参考**: `old/persistence/specification/core/base.py`

**要求**:
```python
from typing import Protocol, TypeVar, Generic, Dict, Any

T = TypeVar("T")

class Specification(Protocol, Generic[T]):
    """Specification 端口 - 查询规格契约"""
    
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies the specification."""
        ...
    
    def to_query_params(self) -> Dict[str, Any]:
        """Convert to query parameters."""
        ...
    
    def and_(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with AND logic."""
        ...
    
    def or_(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with OR logic."""
        ...
    
    def not_(self) -> "Specification[T]":
        """Negate the specification."""
        ...
```

**验收标准**:
- [ ] Protocol 定义正确
- [ ] 支持逻辑组合（AND, OR, NOT）
- [ ] mypy 检查通过

---

#### Task 1.1.3: EventPublisher Port
**文件**: `src/domain/ports/event_publisher.py`

**参考**: 当前 `src/messaging/event_bus.py`

**要求**:
```python
from typing import Protocol
from bento.domain.domain_event import DomainEvent

class EventPublisher(Protocol):
    """Event Publisher 端口 - 事件发布契约"""
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish a single event."""
        ...
    
    async def publish_all(self, events: list[DomainEvent]) -> None:
        """Publish multiple events."""
        ...
```

**验收标准**:
- [ ] Protocol 定义正确
- [ ] 异步方法签名正确
- [ ] mypy 检查通过

---

### 1.2 Application Ports（1 周）

#### Task 1.2.1: UnitOfWork Port
**文件**: `src/application/ports/uow.py`

**参考**: 
- `old/persistence/sqlalchemy/uow.py`
- 当前 `src/application/uow.py`

**要求**:
```python
from typing import Protocol, List
from bento.domain.domain_event import DomainEvent

class UnitOfWork(Protocol):
    """Unit of Work 端口 - 事务管理契约"""
    
    pending_events: List[DomainEvent]
    
    async def begin(self) -> None:
        """Begin a new transaction."""
        ...
    
    async def commit(self) -> None:
        """Commit the transaction."""
        ...
    
    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...
    
    async def collect_events(self) -> List[DomainEvent]:
        """Collect all pending events."""
        ...
    
    async def __aenter__(self) -> "UnitOfWork":
        ...
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        ...
```

**验收标准**:
- [ ] Protocol 定义正确
- [ ] 支持 async context manager
- [ ] 事件收集机制清晰
- [ ] mypy 检查通过

---

#### Task 1.2.2: Cache Port
**文件**: `src/application/ports/cache.py`

**参考**: `old/cache/core/base.py`

**要求**:
```python
from typing import Protocol, TypeVar, Optional, Any

T = TypeVar("T")

class Cache(Protocol):
    """Cache 端口 - 缓存契约"""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value with optional TTL."""
        ...
    
    async def delete(self, key: str) -> None:
        """Delete value by key."""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...
    
    async def clear(self) -> None:
        """Clear all cached values."""
        ...
```

**验收标准**:
- [ ] Protocol 定义正确
- [ ] TTL 支持
- [ ] mypy 检查通过

---

#### Task 1.2.3: MessageBus Port
**文件**: `src/application/ports/message_bus.py`

**参考**: `old/messaging_pulsar/core/`（优先使用 Pulsar）

**要求**:
```python
from typing import Protocol, Callable
from bento.domain.domain_event import DomainEvent

class MessageBus(Protocol):
    """Message Bus 端口 - 消息总线契约"""
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish an event."""
        ...
    
    async def subscribe(self, event_type: type, handler: Callable) -> None:
        """Subscribe to an event type."""
        ...
```

**验收标准**:
- [ ] Protocol 定义正确
- [ ] 发布/订阅模式支持
- [ ] mypy 检查通过

---

#### Task 1.2.4: Mapper Port
**文件**: `src/application/ports/mapper.py`

**参考**: `old/mapper/core/interfaces.py`

**要求**:
```python
from typing import Protocol, TypeVar, Generic

S = TypeVar("S")
T = TypeVar("T")

class Mapper(Protocol, Generic[S, T]):
    """Mapper 端口 - 对象映射契约"""
    
    def map(self, source: S) -> T:
        """Map source to target."""
        ...
    
    def map_to_target(self, source: S, target: T) -> T:
        """Map source to existing target."""
        ...
```

**验收标准**:
- [ ] Protocol 定义正确
- [ ] 泛型类型正确
- [ ] mypy 检查通过

---

### 1.3 文档和验证（1 周）

#### Task 1.3.1: 编写端口文档

**文件**:
- `docs/ports/REPOSITORY.md`
- `docs/ports/SPECIFICATION.md`
- `docs/ports/EVENT_PUBLISHER.md`
- `docs/ports/UOW.md`
- `docs/ports/CACHE.md`
- `docs/ports/MESSAGE_BUS.md`
- `docs/ports/MAPPER.md`

**内容要求**:
- 端口用途说明
- 接口方法文档
- 使用示例
- 注意事项

---

#### Task 1.3.2: import-linter 验证

**验证项**:
```bash
uv run import-linter
```

**期望结果**:
- ✅ Hexagonal layering: PASSED
- ✅ Domain ports are protocols: PASSED
- ✅ Application ports are protocols: PASSED

---

#### Task 1.3.3: mypy 类型检查

**验证项**:
```bash
uv run mypy src/
```

**期望结果**:
- ✅ Success: no issues found

---

## 🔑 关键原则

### 1. 使用 Protocol，不用 ABC

```python
# ✅ 正确：使用 Protocol
from typing import Protocol

class Repository(Protocol):
    async def save(self, entity: Entity) -> None: ...

# ❌ 错误：使用抽象类
from abc import ABC, abstractmethod

class Repository(ABC):  # ❌ 不要在 Port 中使用 ABC
    @abstractmethod
    async def save(self, entity: Entity) -> None: ...
```

### 2. 端口不依赖适配器

```python
# ✅ 正确：只导入领域层
from bento.domain.entity import Entity
from bento.core.ids import EntityId

# ❌ 错误：导入适配器层
from bento.adapters.persistence.sqlalchemy import SqlRepository  # ❌
```

### 3. 泛型类型使用

```python
# ✅ 正确：使用泛型
from typing import Protocol, TypeVar, Generic

E = TypeVar("E", bound=Entity)

class Repository(Protocol, Generic[E]):
    ...
```

---

## 🧪 验证清单

### 开发完成后

- [ ] 所有端口文件已创建
- [ ] 所有端口都是 Protocol
- [ ] 所有端口都有完整的类型注解
- [ ] mypy strict mode 检查通过
- [ ] import-linter 检查通过
- [ ] 所有端口文档已编写
- [ ] 示例代码已添加

---

## 📚 参考资源

### 内部文档
- [MIGRATION_PLAN.md](../MIGRATION_PLAN.md)
- [TARGET_STRUCTURE.md](../architecture/TARGET_STRUCTURE.md)
- [QUICK_REFERENCE.md](../QUICK_REFERENCE.md)

### Old 实现参考
- `old/adapter/repository.py`
- `old/persistence/specification/core/base.py`
- `old/persistence/sqlalchemy/uow.py`
- `old/cache/core/base.py`
- `old/messaging/core/`
- `old/mapper/core/interfaces.py`

---

## 🚀 开始 Phase 1

当你准备好开始时：

1. 从 **Task 1.1.1: Repository Port** 开始
2. 参考 [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) 的每日执行清单
3. 每完成一个端口，运行 mypy 和 import-linter 验证
4. 编写对应的端口文档

**祝开发顺利！** 🎉

---

**文档版本**: v1.0  
**创建时间**: 2025-01-04  
**状态**: ⏳ 待开始

