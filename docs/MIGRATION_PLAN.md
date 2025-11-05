# Bento Framework - Old 架构完整迁移计划

## 📋 执行概要

**目标**：将 `old/` 目录中成熟的企业级 DDD 实现，按照 Bento 的六边形架构和严格分层原则进行重构迁移，打造一个架构科学、功能完整的 Python DDD 框架。

**核心价值**：
- ✅ 保持 Bento 的架构优势（严格分层、端口与适配器分离、依赖反转）
- ✅ 引入 Old 的功能优势（拦截器、Specification、Mapper、缓存、消息等）
- ✅ 实现 **架构科学性 + 功能完整性** 的最佳组合

**时间估算**：14-20 周（约 3.5-5 个月）

**团队规模**：1-2 人全职

---

## 🎯 迁移原则

### 1. 架构原则（不可妥协）

```
严格遵循六边形架构：
┌─────────────────────────────────────────────────────┐
│  Core (无依赖)                                      │
│  ↑                                                  │
│  Domain (只依赖 Core，定义端口 Port)                 │
│  ↑                                                  │
│  Application (只依赖 Domain，定义端口 Port)          │
│  ↑                                                  │
│  Adapters (实现端口，可依赖外部库)                   │
│  ↑                                                  │
│  Interfaces (HTTP/CLI/gRPC 等外部接口)              │
└─────────────────────────────────────────────────────┘

强制约束：
✓ import-linter 检查所有依赖方向
✓ 内层不依赖外层
✓ Domain/Application 只定义 Protocol，不依赖具体实现
✓ 所有具体实现在 Adapters 层
```

### 2. 代码质量原则

- ✅ 所有代码 100% 类型注解（mypy strict mode）
- ✅ 单元测试覆盖率 > 80%
- ✅ 集成测试覆盖核心场景
- ✅ 完善的文档和示例

### 3. 迁移策略

- 🔹 **渐进式迁移**：每个 Phase 独立可用，不阻塞后续开发
- 🔹 **保留 old/**：作为参考实现，迁移完成后归档
- 🔹 **向后兼容**：尽量保持 API 兼容性
- 🔹 **文档先行**：先定义接口和文档，再实现

---

## 📅 迁移路线图

### Phase 0: 准备阶段（1 周）

**目标**：建立迁移基础，明确架构规范

#### 任务清单

- [ ] **0.1 创建架构文档**
  - [ ] 编写 `docs/architecture/HEXAGONAL.md`（六边形架构详解）
  - [ ] 编写 `docs/architecture/LAYERS.md`（分层规范）
  - [ ] 编写 `docs/architecture/PORTS_AND_ADAPTERS.md`（端口与适配器规范）
  - **产出**：架构规范文档
  - **验收**：团队理解并认可架构原则

- [ ] **0.2 设置开发环境**
  - [ ] 更新 `pyproject.toml` 依赖（SQLAlchemy、Redis、Kafka 等）
  - [ ] 配置 import-linter 规则（更严格的约束）
  - [ ] 配置 mypy strict mode
  - [ ] 设置 pre-commit hooks
  - **产出**：完善的开发环境配置
  - **验收**：所有检查工具正常运行

- [ ] **0.3 建立目录结构**
  - [ ] 创建新的目录结构骨架
  - [ ] 编写 `docs/architecture/DIRECTORY_STRUCTURE.md`
  - **产出**：清晰的目录结构
  - **验收**：import-linter 验证通过

```bash
src/
├── core/                    # Layer 0: 无依赖
├── domain/                  # Layer 1: 只依赖 core
│   └── ports/              # 端口定义（Protocol）
├── application/             # Layer 2: 只依赖 domain
│   └── ports/              # 端口定义（Protocol）
├── adapters/                # Layer 3: 实现端口
│   ├── persistence/
│   ├── cache/
│   ├── messaging/
│   ├── mapper/
│   └── observability/
└── interfaces/              # Layer 4: 外部接口
```

- [ ] **0.4 建立测试框架**
  - [ ] 设置单元测试框架
  - [ ] 设置集成测试框架
  - [ ] 设置性能测试框架
  - [ ] 编写测试指南文档
  - **产出**：完善的测试基础设施
  - **验收**：示例测试运行通过

**里程碑**：✅ Phase 0 完成 - 准备就绪，可开始迁移

---

### Phase 1: 端口层定义（2-3 周）

**目标**：定义所有端口（Port）接口，建立领域和应用层的契约

#### 1.1 Domain Ports（1 周）

- [ ] **1.1.1 Repository Port**
  ```python
  # src/domain/ports/repository.py
  from typing import Protocol, TypeVar, Generic, Optional, List
  from bento.core.ids import EntityId
  from bento.domain.entity import Entity
  
  E = TypeVar("E", bound=Entity, contravariant=True)
  ID = TypeVar("ID", bound=EntityId)
  
  class Repository(Protocol, Generic[E, ID]):
      """Repository 端口 - 领域层定义的契约"""
      async def find_by_id(self, id: ID) -> Optional[E]: ...
      async def save(self, entity: E) -> E: ...
      async def delete(self, entity: E) -> None: ...
      async def find_all(self) -> List[E]: ...
  ```
  - **参考**：`old/adapter/repository.py` + 当前 `src/domain/repository.py`
  - **产出**：完整的 Repository Protocol
  - **测试**：类型检查通过

- [ ] **1.1.2 Specification Port**
  ```python
  # src/domain/ports/specification.py
  from typing import Protocol, TypeVar, Generic, Dict, Any
  
  T = TypeVar("T")
  
  class Specification(Protocol, Generic[T]):
      """Specification 端口 - 查询规格契约"""
      def is_satisfied_by(self, candidate: T) -> bool: ...
      def to_query_params(self) -> Dict[str, Any]: ...
      def and_(self, other: "Specification[T]") -> "Specification[T]": ...
      def or_(self, other: "Specification[T]") -> "Specification[T]": ...
      def not_(self) -> "Specification[T]": ...
  ```
  - **参考**：`old/persistence/specification/core/base.py`
  - **产出**：Specification Protocol
  - **测试**：类型检查通过

- [ ] **1.1.3 Event Publisher Port**
  ```python
  # src/domain/ports/event_publisher.py
  from typing import Protocol
  from bento.domain.domain_event import DomainEvent
  
  class EventPublisher(Protocol):
      """Event Publisher 端口 - 事件发布契约"""
      async def publish(self, event: DomainEvent) -> None: ...
      async def publish_all(self, events: list[DomainEvent]) -> None: ...
  ```
  - **参考**：当前 `src/messaging/event_bus.py`
  - **产出**：EventPublisher Protocol
  - **测试**：类型检查通过

#### 1.2 Application Ports（1-2 周）

- [ ] **1.2.1 UnitOfWork Port**
  ```python
  # src/application/ports/uow.py
  from typing import Protocol, List
  from bento.domain.domain_event import DomainEvent
  
  class UnitOfWork(Protocol):
      """Unit of Work 端口 - 事务管理契约"""
      pending_events: List[DomainEvent]
      
      async def begin(self) -> None: ...
      async def commit(self) -> None: ...
      async def rollback(self) -> None: ...
      async def collect_events(self) -> List[DomainEvent]: ...
      
      async def __aenter__(self) -> "UnitOfWork": ...
      async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
  ```
  - **参考**：`old/persistence/sqlalchemy/uow.py` + 当前 `src/application/uow.py`
  - **产出**：UnitOfWork Protocol
  - **测试**：类型检查通过

- [ ] **1.2.2 Cache Port**
  ```python
  # src/application/ports/cache.py
  from typing import Protocol, TypeVar, Optional, Any
  
  T = TypeVar("T")
  
  class Cache(Protocol):
      """Cache 端口 - 缓存契约"""
      async def get(self, key: str) -> Optional[Any]: ...
      async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: ...
      async def delete(self, key: str) -> None: ...
      async def exists(self, key: str) -> bool: ...
      async def clear(self) -> None: ...
  ```
  - **参考**：`old/cache/core/base.py`
  - **产出**：Cache Protocol
  - **测试**：类型检查通过

- [ ] **1.2.3 MessageBus Port**
  ```python
  # src/application/ports/message_bus.py
  from typing import Protocol
  from bento.domain.domain_event import DomainEvent
  
  class MessageBus(Protocol):
      """Message Bus 端口 - 消息总线契约"""
      async def publish(self, event: DomainEvent) -> None: ...
      async def subscribe(self, event_type: type, handler: callable) -> None: ...
  ```
  - **参考**：`old/messaging/core/`
  - **产出**：MessageBus Protocol
  - **测试**：类型检查通过

- [ ] **1.2.4 Mapper Port**
  ```python
  # src/application/ports/mapper.py
  from typing import Protocol, TypeVar, Generic
  
  S = TypeVar("S")
  T = TypeVar("T")
  
  class Mapper(Protocol, Generic[S, T]):
      """Mapper 端口 - 对象映射契约"""
      def map(self, source: S) -> T: ...
      def map_to_target(self, source: S, target: T) -> T: ...
  ```
  - **参考**：`old/mapper/core/interfaces.py`
  - **产出**：Mapper Protocol
  - **测试**：类型检查通过

#### 1.3 文档和验证

- [ ] **1.3.1 编写端口文档**
  - [ ] `docs/ports/REPOSITORY.md`
  - [ ] `docs/ports/SPECIFICATION.md`
  - [ ] `docs/ports/UOW.md`
  - [ ] `docs/ports/CACHE.md`
  - [ ] `docs/ports/MESSAGE_BUS.md`
  - [ ] `docs/ports/MAPPER.md`

- [ ] **1.3.2 import-linter 验证**
  - [ ] 验证 Domain 层不依赖外层
  - [ ] 验证 Application 层不依赖外层
  - [ ] 验证所有 Port 都是 Protocol

**里程碑**：✅ Phase 1 完成 - 所有端口定义完成，契约清晰

---

### Phase 2: 持久化层迁移（4-6 周）

**目标**：迁移 Specification、Interceptor、BaseRepository - 最核心、最复杂的部分

#### 2.1 Specification 实现（1-2 周）

- [ ] **2.1.1 核心 Specification**
  ```bash
  src/adapters/persistence/specification/
  ├── __init__.py
  ├── base.py                    # 基础实现
  ├── types.py                   # 类型定义
  └── composite.py               # 组合规格
  ```
  - **源文件**：`old/persistence/specification/core/`
  - **改造**：实现 `domain/ports/specification.py` Protocol
  - **测试**：单元测试 + 集成测试

- [ ] **2.1.2 Criteria 实现**
  ```bash
  src/adapters/persistence/specification/criteria/
  ├── comparison.py              # 比较操作（=, >, <, IN 等）
  ├── logical.py                 # 逻辑操作（AND, OR, NOT）
  └── temporal.py                # 时间操作
  ```
  - **源文件**：`old/persistence/specification/criteria/`
  - **测试**：单元测试覆盖所有操作符

- [ ] **2.1.3 Builder 实现**
  ```bash
  src/adapters/persistence/specification/builder/
  ├── base.py
  ├── entity.py
  └── aggregate.py
  ```
  - **源文件**：`old/persistence/specification/builder/`
  - **测试**：Builder 模式测试

- [ ] **2.1.4 文档和示例**
  - [ ] `docs/adapters/SPECIFICATION.md`
  - [ ] `examples/specification_demo.py`

#### 2.2 Interceptor 系统（2-3 周）⭐ 核心价值

- [ ] **2.2.1 Interceptor 核心**
  ```bash
  src/adapters/persistence/interceptor/
  ├── core/
  │   ├── base.py                # Interceptor Protocol + 抽象类
  │   ├── chain.py               # InterceptorChain 实现
  │   ├── context.py             # InterceptorContext
  │   ├── types.py               # OperationType 等枚举
  │   ├── metadata.py            # 元数据管理
  │   └── registry.py            # 注册表
  ```
  - **源文件**：`old/persistence/sqlalchemy/interceptor/core/`
  - **改造**：解耦 SQLAlchemy，抽象为通用拦截器
  - **测试**：拦截器链测试

- [ ] **2.2.2 标准拦截器实现**
  ```bash
  src/adapters/persistence/interceptor/impl/
  ├── audit.py                   # 审计拦截器
  ├── soft_delete.py             # 软删除拦截器
  ├── optimistic_lock.py         # 乐观锁拦截器
  ├── cache.py                   # 缓存拦截器
  ├── logging.py                 # 日志拦截器
  ├── transaction.py             # 事务拦截器
  └── outbox.py                  # Outbox 拦截器
  ```
  - **源文件**：`old/persistence/sqlalchemy/interceptor/impl/`
  - **改造**：每个拦截器独立测试
  - **测试**：每个拦截器 > 90% 覆盖率

- [ ] **2.2.3 Factory 和配置**
  ```python
  # src/adapters/persistence/interceptor/factory.py
  class InterceptorFactory:
      @staticmethod
      def create_chain(
          enable_audit: bool = True,
          enable_soft_delete: bool = True,
          enable_optimistic_lock: bool = True,
          custom_interceptors: list = None,
      ) -> InterceptorChain:
          ...
  ```
  - **源文件**：`old/persistence/sqlalchemy/interceptor/factory.py`
  - **测试**：Factory 测试

- [ ] **2.2.4 文档和示例**
  - [ ] `docs/adapters/INTERCEPTOR.md`（详细设计文档）
  - [ ] `examples/interceptor_demo.py`

#### 2.3 SQLAlchemy Repository（1-2 周）

- [ ] **2.3.1 BaseRepository 实现**
  ```python
  # src/adapters/persistence/sqlalchemy/repository.py
  from bento.domain.ports.repository import Repository
  from bento.adapters.persistence.interceptor import InterceptorChain
  
  class SqlAlchemyRepository(Repository[E, ID]):
      """SQLAlchemy Repository 适配器 - 实现 Repository Port"""
      
      def __init__(
          self,
          session: AsyncSession,
          model_class: Type[PO],
          interceptor_chain: InterceptorChain,
      ):
          ...
  ```
  - **源文件**：`old/persistence/sqlalchemy/repository/base.py`
  - **改造**：实现 `domain/ports/repository.py` Protocol
  - **集成**：使用 Interceptor 系统
  - **测试**：集成测试（需要真实数据库）

- [ ] **2.3.2 Helper 工具**
  ```bash
  src/adapters/persistence/sqlalchemy/helper/
  ├── query_builder.py
  ├── pagination.py
  ├── field_resolver.py
  ├── audit.py
  └── soft_delete.py
  ```
  - **源文件**：`old/persistence/sqlalchemy/repository/helper/`
  - **测试**：单元测试

- [ ] **2.3.3 Delegate 模式**
  ```python
  # src/adapters/persistence/sqlalchemy/delegate.py
  ```
  - **源文件**：`old/persistence/sqlalchemy/repository/delegate.py`
  - **测试**：单元测试

#### 2.4 UnitOfWork 完整实现（1 周）

- [ ] **2.4.1 SQLAlchemy UoW**
  ```python
  # src/adapters/persistence/sqlalchemy/uow.py
  from bento.application.ports.uow import UnitOfWork
  
  class SqlAlchemyUnitOfWork(UnitOfWork):
      """SQLAlchemy UoW 适配器 - 实现 UnitOfWork Port"""
      ...
  ```
  - **源文件**：`old/persistence/sqlalchemy/uow.py`
  - **改造**：实现 `application/ports/uow.py` Protocol
  - **特性**：ContextVar、Retry、Event Collection
  - **测试**：集成测试

- [ ] **2.4.2 Outbox 整合**
  ```python
  # src/adapters/persistence/sqlalchemy/outbox.py
  ```
  - **源文件**：`old/persistence/sqlalchemy/interceptor/impl/outbox.py` + 当前 `src/persistence/sqlalchemy/outbox_sql.py`
  - **测试**：集成测试（验证事务性）

- [x] **2.4.3 OutboxProjector** ✅ **已完成**
  ```python
  # src/infrastructure/projection/projector.py
  ```
  - **功能**：轮询 Outbox 表并发布事件到 MessageBus
  - **特性**：
    - 行级锁 (`FOR UPDATE SKIP LOCKED`)
    - 批量处理（默认 200 条）
    - 自适应休眠策略
    - 错误处理和重试
    - 优雅关闭
  - **源文件**：`old/infrastructure/projection/projector.py`
  - **测试**：单元测试 + 集成测试
  - **文档**：`docs/infrastructure/PROJECTION_USAGE.md`
  - **状态**：✅ 已完成

#### 2.5 PersistenceObject (PO) 基类

- [ ] **2.5.1 BasePO**
  ```python
  # src/adapters/persistence/sqlalchemy/po/base.py
  ```
  - **源文件**：`old/persistence/sqlalchemy/po/base.py`
  - **测试**：单元测试

- [ ] **2.5.2 OutboxPO**
  ```python
  # src/adapters/persistence/sqlalchemy/po/outbox.py
  ```
  - **源文件**：`old/persistence/sqlalchemy/po/outbox.py`

#### 2.6 集成测试和文档

- [ ] **2.6.1 完整的集成测试**
  ```bash
  tests/integration/persistence/
  ├── test_repository.py
  ├── test_specification.py
  ├── test_interceptor.py
  ├── test_uow.py
  └── test_outbox.py
  ```

- [ ] **2.6.2 性能测试**
  ```bash
  tests/performance/
  └── test_repository_benchmark.py
  ```

- [ ] **2.6.3 文档**
  - [ ] `docs/adapters/persistence/README.md`
  - [ ] `docs/adapters/persistence/ARCHITECTURE.md`
  - [ ] `docs/adapters/persistence/USAGE.md`

**里程碑**：✅ Phase 2 完成 - 持久化层功能完整，性能优异

---

### Phase 3: Mapper 系统（2-3 周）

**目标**：迁移对象映射系统，处理 Domain ↔ DTO ↔ PO 转换

#### 3.1 Mapper Core（1 周）

- [ ] **3.1.1 Mapper 核心接口**
  ```bash
  src/adapters/mapper/
  ├── core/
  │   ├── mapper.py              # Mapper 实现
  │   ├── strategy.py            # 映射策略
  │   ├── context.py             # 映射上下文
  │   ├── converter.py           # 类型转换器
  │   └── protocols.py           # Protocol 定义
  ```
  - **源文件**：`old/mapper/core/`
  - **改造**：实现 `application/ports/mapper.py` Protocol
  - **测试**：单元测试

- [ ] **3.1.2 映射策略**
  ```python
  # 支持的策略：
  - AutoMappingStrategy         # 自动映射
  - ExplicitMappingStrategy     # 显式映射
  - CustomMappingStrategy       # 自定义映射
  - CompositeMappingStrategy    # 组合策略
  ```
  - **源文件**：`old/mapper/core/strategies.py`
  - **测试**：每种策略独立测试

#### 3.2 Registry 和 Builder（1 周）

- [ ] **3.2.1 Mapper Registry**
  ```bash
  src/adapters/mapper/registry/
  ├── base.py                    # 基础注册表
  ├── dto.py                     # DTO 映射器注册表
  ├── po.py                      # PO 映射器注册表
  └── vo.py                      # VO 映射器注册表
  ```
  - **源文件**：`old/mapper/registry/`
  - **测试**：注册表测试

- [ ] **3.2.2 Mapper Builder**
  ```python
  # src/adapters/mapper/builder.py
  from bento.adapters.mapper.core.mapper import Mapper
  
  class MapperBuilder:
      @staticmethod
      def for_types(source_type, target_type) -> "MapperBuilder":
          ...
      
      def map(self, source_field: str, target_field: str) -> "MapperBuilder":
          ...
      
      def map_custom(self, target_field: str, func: Callable) -> "MapperBuilder":
          ...
      
      def build(self) -> Mapper:
          ...
  ```
  - **测试**：Builder 测试

#### 3.3 DTO/PO/VO Base Classes（1 周）

- [ ] **3.3.1 DTO Base**
  ```python
  # src/adapters/mapper/dto/base.py
  ```
  - **源文件**：`old/mapper/dto/base.py`

- [ ] **3.3.2 PO Base**（整合到 persistence）
  - **源文件**：`old/mapper/po/base.py`

- [ ] **3.3.3 VO Base**
  ```python
  # src/adapters/mapper/vo/base.py
  ```
  - **源文件**：`old/mapper/vo/base.py`

#### 3.4 文档和示例

- [ ] **3.4.1 Mapper 文档**
  - [ ] `docs/adapters/MAPPER.md`
  - [ ] `docs/adapters/mapper/USAGE.md`

- [ ] **3.4.2 示例代码**
  - [ ] `examples/mapper_demo.py`

**里程碑**：✅ Phase 3 完成 - Mapper 系统功能完整

---

### Phase 4: Cache 系统（1-2 周）

**目标**：迁移缓存系统，支持多后端和多策略

#### 4.1 Cache 核心（1 周）

- [ ] **4.1.1 Cache Manager**
  ```bash
  src/adapters/cache/
  ├── core/
  │   ├── base.py                # 基础 Cache 实现
  │   ├── config.py              # 缓存配置
  │   └── manager.py             # 缓存管理器
  ```
  - **源文件**：`old/cache/core/`
  - **改造**：实现 `application/ports/cache.py` Protocol
  - **测试**：单元测试

- [ ] **4.1.2 Cache Backends**
  ```bash
  src/adapters/cache/backends/
  ├── memory.py                  # 内存缓存
  └── redis.py                   # Redis 缓存
  ```
  - **源文件**：`old/cache/backends/`
  - **测试**：每个后端独立测试

#### 4.2 Cache Policies（1 周）

- [ ] **4.2.1 驱逐策略**
  ```bash
  src/adapters/cache/policies/
  ├── base.py
  ├── lru.py                     # LRU 策略
  ├── lfu.py                     # LFU 策略
  └── adaptive.py                # 自适应策略
  ```
  - **源文件**：`old/cache/policies/`
  - **测试**：策略测试

- [ ] **4.2.2 Decorators**
  ```python
  # src/adapters/cache/decorators.py
  @cached(ttl=3600)
  async def expensive_operation():
      ...
  ```
  - **源文件**：`old/cache/decorators.py`

#### 4.3 文档和示例

- [ ] **4.3.1 文档**
  - [ ] `docs/adapters/CACHE.md`

- [ ] **4.3.2 示例**
  - [ ] `examples/cache_demo.py`

**里程碑**：✅ Phase 4 完成 - Cache 系统功能完整

---

### Phase 5: Messaging 系统（2-3 周）

**目标**：迁移消息系统，支持 Pulsar（优先）

#### 5.1 Messaging 核心（1 周）

- [ ] **5.1.1 Message Bus 核心**
  ```bash
  src/adapters/messaging/
  ├── core/
  │   ├── bus.py                 # MessageBus 实现
  │   ├── dispatcher.py          # 事件分发器
  │   └── consumer.py            # 消费者基类
  ```
  - **源文件**：`old/messaging/core/`
  - **改造**：实现 `application/ports/message_bus.py` Protocol
  - **测试**：单元测试

#### 5.2 Pulsar & Kafka 适配器（1-2 周）

- [ ] **5.2.1 Pulsar 适配器**（优先）
  ```bash
  src/adapters/messaging/pulsar/
  ├── producer.py
  ├── consumer.py
  ├── admin.py
  └── config.py
  ```
  - **源文件**：`old/messaging_pulsar/`
  - **测试**：集成测试（需要 Pulsar）
  - **优先级**：⭐⭐⭐⭐⭐

- [ ] **5.2.2 Kafka 适配器**（可选）
  ```bash
  src/adapters/messaging/kafka/
  ├── producer.py
  ├── consumer.py
  ├── admin.py
  └── config.py
  ```
  - **源文件**：`old/messaging-kafka/`
  - **测试**：集成测试（需要 Kafka）
  - **优先级**：⭐⭐⭐（可选）

#### 5.3 Codec 系统（1 周）

- [ ] **5.3.1 编解码器**
  ```bash
  src/adapters/messaging/codec/
  ├── json.py
  ├── avro.py
  └── protobuf.py
  ```
  - **源文件**：`old/messaging_pulsar/codec/`
  - **测试**：编解码测试

#### 5.4 文档和示例

- [ ] **5.4.1 文档**
  - [ ] `docs/adapters/MESSAGING.md`
  - [ ] `docs/adapters/messaging/KAFKA.md`
  - [ ] `docs/adapters/messaging/PULSAR.md`

- [ ] **5.4.2 示例**
  - [ ] `examples/messaging_demo.py`

**里程碑**：✅ Phase 5 完成 - Messaging 系统功能完整

---

### Phase 6: 其他基础设施（2-3 周）

**目标**：迁移配置、日志、观测性、认证、存储等

#### 6.1 Config 系统（1 周）

- [ ] **6.1.1 Config Core**
  ```bash
  src/adapters/config/
  ├── core/
  │   ├── base.py
  │   ├── manager.py
  │   └── provider.py
  └── providers/
      ├── env.py
      ├── json.py
      └── yaml.py
  ```
  - **源文件**：`old/config/`
  - **测试**：单元测试

#### 6.2 Logger 系统（1 周）

- [ ] **6.2.1 Logger Core**
  ```bash
  src/adapters/logger/
  ├── manager.py
  ├── context.py
  └── processors/
      ├── console.py
      ├── file.py
      ├── kafka.py
      └── sentry.py
  ```
  - **源文件**：`old/logger/`
  - **测试**：单元测试

#### 6.3 Observability（1 周）

- [ ] **6.3.1 Tracing & Metrics**
  ```bash
  src/adapters/observability/
  ├── tracing/
  │   └── opentelemetry.py
  └── metrics/
      └── prometheus.py
  ```
  - **源文件**：`old/observability/`
  - **测试**：集成测试

#### 6.4 Identity & Auth（可选）

- [ ] **6.4.1 Logto 适配器**
  ```bash
  src/adapters/identity/
  └── logto.py
  ```
  - **源文件**：`old/identity/`

#### 6.5 Object Storage（可选）

- [ ] **6.5.1 Storage 适配器**
  ```bash
  src/adapters/storage/
  ├── minio.py
  └── local.py
  ```
  - **源文件**：`old/object_storage/`

**里程碑**：✅ Phase 6 完成 - 基础设施完整

---

### Phase 7: 完善和优化（2-3 周）

**目标**：完善文档、示例、性能优化、发布准备

#### 7.1 文档完善（1 周）

- [ ] **7.1.1 架构文档**
  - [ ] `docs/architecture/OVERVIEW.md`
  - [ ] `docs/architecture/ADR/`（架构决策记录）

- [ ] **7.1.2 使用指南**
  - [ ] `docs/guides/GETTING_STARTED.md`
  - [ ] `docs/guides/REPOSITORY.md`
  - [ ] `docs/guides/SPECIFICATION.md`
  - [ ] `docs/guides/INTERCEPTOR.md`
  - [ ] `docs/guides/MAPPER.md`
  - [ ] `docs/guides/CACHE.md`
  - [ ] `docs/guides/MESSAGING.md`

- [ ] **7.1.3 API 文档**
  - [ ] 使用 Sphinx 生成完整 API 文档

#### 7.2 示例项目（1 周）

- [ ] **7.2.1 完整示例**
  ```bash
  examples/full_app/
  ├── domain/                    # 领域模型（订单系统）
  ├── application/               # 用例
  ├── adapters/                  # 适配器配置
  ├── interfaces/                # HTTP API
  └── runtime/                   # 启动入口
  ```

- [ ] **7.2.2 最佳实践示例**
  ```bash
  examples/best_practices/
  ├── aggregate_design/
  ├── event_sourcing/
  ├── cqrs/
  └── multi_tenant/
  ```

#### 7.3 性能优化（1 周）

- [ ] **7.3.1 性能基准测试**
  ```bash
  tests/performance/
  ├── benchmark_repository.py
  ├── benchmark_specification.py
  ├── benchmark_mapper.py
  └── benchmark_cache.py
  ```

- [ ] **7.3.2 优化**
  - [ ] 识别性能瓶颈
  - [ ] 优化热点代码
  - [ ] 验证优化效果

#### 7.4 发布准备

- [ ] **7.4.1 版本发布**
  - [ ] 更新 `pyproject.toml` 版本到 `1.0.0`
  - [ ] 编写 `CHANGELOG.md`
  - [ ] 编写 `MIGRATION_GUIDE.md`（从 old 迁移指南）

- [ ] **7.4.2 CI/CD**
  - [ ] 完善 GitHub Actions 工作流
  - [ ] 自动化测试
  - [ ] 自动化发布

**里程碑**：✅ Phase 7 完成 - 框架成熟，可以发布

---

## 📊 风险评估和应对

### 高风险项

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|---------|
| **Interceptor 系统复杂度高** | 中 | 高 | 分步实现，先核心后扩展 |
| **Specification 性能问题** | 中 | 中 | 性能测试，优化查询构建 |
| **Mapper 循环引用** | 低 | 中 | 严格测试，文档说明 |
| **时间超期** | 高 | 高 | 每个 Phase 设置缓冲时间 |

### 中风险项

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|---------|
| **Import-linter 约束过严** | 中 | 中 | 灵活调整规则 |
| **测试覆盖率不足** | 中 | 中 | 强制覆盖率检查 |
| **文档滞后** | 高 | 低 | 文档先行策略 |

---

## 🎯 成功标准

### 技术指标

- ✅ **架构合规性**：100% import-linter 检查通过
- ✅ **类型安全性**：100% mypy strict mode 通过
- ✅ **测试覆盖率**：单元测试 > 80%，集成测试覆盖核心场景
- ✅ **性能基准**：性能不低于 old 实现的 90%

### 功能指标

- ✅ **Repository**：支持 CRUD、分页、排序、Specification 查询
- ✅ **Interceptor**：支持审计、软删除、乐观锁、缓存、日志、事务
- ✅ **Specification**：支持复杂查询构建、逻辑组合、统计聚合
- ✅ **Mapper**：支持自动映射、显式映射、嵌套映射、集合映射
- ✅ **Cache**：支持 Memory/Redis 后端，LRU/LFU/Adaptive 策略
- ✅ **Messaging**：支持 Kafka/Pulsar，JSON/Avro/Protobuf 编解码

### 文档指标

- ✅ **架构文档**：完整的六边形架构说明
- ✅ **使用指南**：每个模块都有详细指南
- ✅ **API 文档**：自动生成的完整 API 文档
- ✅ **示例代码**：至少 5 个完整示例

---

## 📋 检查清单

### Phase 0 检查清单
- [ ] 架构文档完成
- [ ] 开发环境配置完成
- [ ] 目录结构创建完成
- [ ] 测试框架建立完成
- [ ] import-linter 验证通过

### Phase 1 检查清单
- [ ] 所有端口定义完成
- [ ] 所有端口都是 Protocol
- [ ] 端口文档完成
- [ ] import-linter 验证通过
- [ ] mypy strict mode 通过

### Phase 2 检查清单
- [ ] Specification 实现完成且测试通过
- [ ] Interceptor 系统实现完成且测试通过
- [ ] BaseRepository 实现完成且测试通过
- [ ] UnitOfWork 实现完成且测试通过
- [ ] 集成测试通过
- [ ] 性能测试通过
- [ ] 文档完成

### Phase 3-7 检查清单
- [ ] 各模块实现完成
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 文档完成
- [ ] 示例代码完成

---

## 📅 时间线总览

```
Week 1:     Phase 0 - 准备阶段
Week 2-4:   Phase 1 - 端口层定义
Week 5-10:  Phase 2 - 持久化层迁移 ⭐ 核心
Week 11-13: Phase 3 - Mapper 系统
Week 14-15: Phase 4 - Cache 系统
Week 16-18: Phase 5 - Messaging 系统
Week 19-21: Phase 6 - 其他基础设施
Week 22-24: Phase 7 - 完善和优化

Total: 24 周（约 6 个月）
```

---

## 🚀 后续计划

### v1.1.0 - 高级特性（3 个月）
- [ ] Event Sourcing 支持
- [ ] CQRS 完整实现
- [ ] Multi-tenant 支持
- [ ] Saga 模式支持

### v1.2.0 - 性能优化（2 个月）
- [ ] 连接池优化
- [ ] 缓存预热
- [ ] 批量操作优化
- [ ] 异步性能优化

### v2.0.0 - 生态建设（长期）
- [ ] CLI 工具增强
- [ ] IDE 插件
- [ ] 可视化工具
- [ ] 社区建设

---

## 📞 联系和协作

**项目负责人**：[待定]

**技术评审**：每个 Phase 完成后进行技术评审

**每周同步**：每周一同步进度，讨论问题

**文档协作**：使用 Markdown + Git 协作

---

**最后更新**：2025-01-04

**状态**：📝 计划制定完成，等待批准

