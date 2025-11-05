# Bento Framework - Ports (端口) 文档

## 📋 概述

**Ports (端口)** 是 Bento Framework 六边形架构的核心组成部分。端口定义了**领域层和应用层**需要的外部服务契约,使用 Python 的 `Protocol` 类型实现依赖反转原则。

### 什么是端口？

端口是一个**接口定义**（`Protocol`），它：
- ✅ 定义了领域/应用层需要什么功能
- ✅ 不依赖任何具体实现
- ✅ 使用类型检查确保实现正确性
- ✅ 支持结构化子类型（structural subtyping）

### 端口 vs 适配器

```
┌─────────────────────────────────────────────────┐
│  内层 (Domain/Application)                      │
│  ┌──────────────────────────────────┐          │
│  │  Port (Protocol)                 │          │
│  │  - Repository                    │          │
│  │  - UnitOfWork                    │          │
│  │  - Cache                         │          │
│  └──────────────────────────────────┘          │
│           ↓ 依赖反转                            │
│  ┌──────────────────────────────────┐          │
│  │  Adapter (Implementation)        │          │
│  │  - SqlAlchemyRepository          │          │
│  │  - RedisCache                    │          │
│  │  - PulsarMessageBus              │          │
│  └──────────────────────────────────┘          │
│  外层 (Infrastructure)                          │
└─────────────────────────────────────────────────┘
```

---

## 📦 端口列表

### Domain Ports（领域端口）

定义在 `src/domain/ports/`，供领域层使用。

| 端口 | 文件 | 用途 |
|------|------|------|
| **Repository** | [repository.py](../src/domain/ports/repository.py) | 实体持久化契约 |
| **Specification** | [specification.py](../src/domain/ports/specification.py) | 查询规格契约 |
| **EventPublisher** | [event_publisher.py](../src/domain/ports/event_publisher.py) | 事件发布契约 |

### Application Ports（应用端口）

定义在 `src/application/ports/`，供应用层使用。

| 端口 | 文件 | 用途 |
|------|------|------|
| **UnitOfWork** | [uow.py](../src/application/ports/uow.py) | 事务管理契约 |
| **Cache** | [cache.py](../src/application/ports/cache.py) | 缓存契约 |
| **MessageBus** | [message_bus.py](../src/application/ports/message_bus.py) | 消息总线契约 |
| **Mapper** | [mapper.py](../src/application/ports/mapper.py) | 对象映射契约 |

---

## 🎯 核心原则

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

**原因**：
- Protocol 支持结构化子类型（duck typing + 类型检查）
- 无需继承，更灵活
- 更符合 Python 的哲学

### 2. 端口不依赖适配器

```python
# ✅ 正确：只导入领域层
from bento.domain.entity import Entity
from bento.core.ids import EntityId

# ❌ 错误：导入适配器层
from bento.adapters.persistence.sqlalchemy import SqlRepository  # ❌
```

### 3. 完整的类型注解

```python
# ✅ 正确：完整类型注解
async def find_by_id(self, id: EntityId) -> Optional[Entity]: ...

# ❌ 错误：缺少类型注解
async def find_by_id(self, id): ...  # ❌
```

---

## 📚 详细文档

每个端口都有详细的文档说明：

### Domain Ports

- 📖 [Repository Port](./REPOSITORY.md) - 实体持久化
- 📖 [Specification Port](./SPECIFICATION.md) - 查询规格
- 📖 [EventPublisher Port](./EVENT_PUBLISHER.md) - 事件发布

### Application Ports

- 📖 [UnitOfWork Port](./UOW.md) - 事务管理
- 📖 [Cache Port](./CACHE.md) - 缓存
- 📖 [MessageBus Port](./MESSAGE_BUS.md) - 消息总线
- 📖 [Mapper Port](./MAPPER.md) - 对象映射

---

## 🔍 使用示例

### 在领域层使用 Repository Port

```python
# src/domain/services/user_service.py
from bento.domain.ports.repository import Repository
from bento.domain.entities.user import User

class UserDomainService:
    def __init__(self, repo: Repository[User, UserId]):
        self.repo = repo  # 依赖抽象，不依赖具体实现
    
    async def find_active_user(self, user_id: UserId) -> Optional[User]:
        user = await self.repo.find_by_id(user_id)
        if user and user.is_active:
            return user
        return None
```

### 在应用层使用 UnitOfWork Port

```python
# src/application/usecases/create_user.py
from bento.application.ports.uow import UnitOfWork
from bento.domain.ports.repository import Repository

class CreateUserUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        repo: Repository[User, UserId],
    ):
        self.uow = uow
        self.repo = repo
    
    async def execute(self, command: CreateUserCommand) -> Result:
        async with self.uow:  # 开始事务
            user = User.create(
                name=command.name,
                email=command.email,
            )
            await self.repo.save(user)
            await self.uow.commit()  # 提交事务并发布事件
        return Ok(user.id)
```

### 在运行时注入适配器

```python
# runtime/composition.py
from bento.domain.ports.repository import Repository
from bento.adapters.persistence.sqlalchemy.repository import SqlAlchemyRepository

# 依赖注入：将具体实现注入到端口
def setup_dependencies():
    # 创建适配器实例
    repo = SqlAlchemyRepository(session, UserPO)
    
    # 注册到容器（实现 Repository Port）
    container.register(Repository[User, UserId], repo)
```

---

## ✅ 验证

### import-linter 检查

确保端口不依赖适配器：

```bash
uv run import-linter
```

**期望结果**：
```
✅ Domain ports are protocols: PASSED
✅ Application ports are protocols: PASSED
✅ No adapters into domain or application: PASSED
```

### mypy 类型检查

确保类型注解正确：

```bash
uv run mypy src/domain/ports/ src/application/ports/
```

**期望结果**：
```
Success: no issues found
```

---

## 🔗 相关文档

- [六边形架构总览](../architecture/TARGET_STRUCTURE.md)
- [适配器实现指南](../adapters/)
- [迁移计划](../MIGRATION_PLAN.md)

---

**最后更新**：2025-01-04  
**Phase**: 1 - 端口层定义  
**状态**: ✅ 已完成

