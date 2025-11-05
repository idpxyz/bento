# Bento Framework - 迁移后的目标目录结构

## 完整目录树

```
bento/
├── pyproject.toml                   # 项目配置
├── README.md                        # 项目说明
├── CHANGELOG.md                     # 变更日志
│
├── docs/                            # 文档目录
│   ├── MIGRATION_PLAN.md           # 迁移计划（本计划）
│   ├── architecture/               # 架构文档
│   │   ├── OVERVIEW.md
│   │   ├── HEXAGONAL.md
│   │   ├── LAYERS.md
│   │   ├── PORTS_AND_ADAPTERS.md
│   │   ├── TARGET_STRUCTURE.md     # 本文件
│   │   └── ADR/                    # 架构决策记录
│   ├── ports/                      # 端口文档
│   │   ├── REPOSITORY.md
│   │   ├── SPECIFICATION.md
│   │   ├── UOW.md
│   │   ├── CACHE.md
│   │   ├── MESSAGE_BUS.md
│   │   └── MAPPER.md
│   ├── adapters/                   # 适配器文档
│   │   ├── persistence/
│   │   │   ├── README.md
│   │   │   ├── ARCHITECTURE.md
│   │   │   └── USAGE.md
│   │   ├── INTERCEPTOR.md
│   │   ├── SPECIFICATION.md
│   │   ├── MAPPER.md
│   │   ├── CACHE.md
│   │   └── MESSAGING.md
│   ├── guides/                     # 使用指南
│   │   ├── GETTING_STARTED.md
│   │   ├── REPOSITORY.md
│   │   ├── SPECIFICATION.md
│   │   ├── INTERCEPTOR.md
│   │   └── ...
│   └── diagrams/                   # Mermaid 图表
│       └── ...
│
├── src/                             # 源代码目录
│   │
│   ├── core/                        # ⭐ Layer 0: 核心层（无依赖）
│   │   ├── __init__.py
│   │   ├── ids.py                  # 实体 ID
│   │   ├── result.py               # Result 类型
│   │   └── clock.py                # 时钟抽象
│   │
│   ├── domain/                      # ⭐ Layer 1: 领域层（只依赖 core）
│   │   ├── __init__.py
│   │   ├── entity.py               # 实体基类
│   │   ├── aggregate.py            # 聚合根基类
│   │   ├── value_object.py         # 值对象基类
│   │   ├── domain_event.py         # 领域事件
│   │   │
│   │   └── ports/                  # 🔌 领域端口（Protocol 定义）
│   │       ├── __init__.py
│   │       ├── repository.py       # Repository Port
│   │       ├── specification.py    # Specification Port
│   │       └── event_publisher.py  # EventPublisher Port
│   │
│   ├── application/                 # ⭐ Layer 2: 应用层（只依赖 domain）
│   │   ├── __init__.py
│   │   ├── usecase.py              # 用例基类
│   │   ├── command.py              # 命令基类
│   │   ├── query.py                # 查询基类
│   │   │
│   │   └── ports/                  # 🔌 应用端口（Protocol 定义）
│   │       ├── __init__.py
│   │       ├── uow.py              # UnitOfWork Port
│   │       ├── cache.py            # Cache Port
│   │       ├── message_bus.py      # MessageBus Port
│   │       └── mapper.py           # Mapper Port
│   │
│   ├── adapters/                    # ⭐ Layer 3: 适配器层（实现端口）
│   │   │
│   │   ├── persistence/            # 🔧 持久化适配器
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── specification/      # ✨ Specification 实现
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── types.py
│   │   │   │   ├── composite.py
│   │   │   │   ├── criteria/
│   │   │   │   │   ├── comparison.py
│   │   │   │   │   ├── logical.py
│   │   │   │   │   └── temporal.py
│   │   │   │   └── builder/
│   │   │   │       ├── base.py
│   │   │   │       ├── entity.py
│   │   │   │       └── aggregate.py
│   │   │   │
│   │   │   ├── interceptor/        # ✨ 拦截器系统（核心价值）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── core/
│   │   │   │   │   ├── base.py          # Interceptor Protocol
│   │   │   │   │   ├── chain.py         # 责任链
│   │   │   │   │   ├── context.py       # 上下文
│   │   │   │   │   ├── types.py         # 类型定义
│   │   │   │   │   ├── metadata.py      # 元数据管理
│   │   │   │   │   └── registry.py      # 注册表
│   │   │   │   ├── impl/
│   │   │   │   │   ├── audit.py         # 审计拦截器
│   │   │   │   │   ├── soft_delete.py   # 软删除拦截器
│   │   │   │   │   ├── optimistic_lock.py # 乐观锁拦截器
│   │   │   │   │   ├── cache.py         # 缓存拦截器
│   │   │   │   │   ├── logging.py       # 日志拦截器
│   │   │   │   │   ├── transaction.py   # 事务拦截器
│   │   │   │   │   └── outbox.py        # Outbox 拦截器
│   │   │   │   └── factory.py       # 拦截器工厂
│   │   │   │
│   │   │   ├── in_memory/          # 内存实现（测试用）
│   │   │   │   ├── repository.py
│   │   │   │   └── uow.py
│   │   │   │
│   │   │   └── sqlalchemy/         # ✨ SQLAlchemy 实现
│   │   │       ├── __init__.py
│   │   │       ├── base.py          # SQLAlchemy 基础配置
│   │   │       ├── session.py       # Session 管理
│   │   │       ├── repository.py    # Repository 实现
│   │   │       ├── uow.py           # UoW 实现
│   │   │       ├── outbox.py        # Outbox 实现
│   │   │       ├── po/              # Persistence Objects
│   │   │       │   ├── base.py
│   │   │       │   └── outbox.py
│   │   │       ├── helper/          # 辅助工具
│   │   │       │   ├── query_builder.py
│   │   │       │   ├── pagination.py
│   │   │       │   ├── field_resolver.py
│   │   │       │   ├── audit.py
│   │   │       │   └── soft_delete.py
│   │   │       └── delegate.py      # Delegate 模式
│   │   │
│   │   ├── cache/                  # 🔧 缓存适配器
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── base.py
│   │   │   │   ├── config.py
│   │   │   │   └── manager.py
│   │   │   ├── backends/
│   │   │   │   ├── memory.py
│   │   │   │   └── redis.py
│   │   │   ├── policies/
│   │   │   │   ├── base.py
│   │   │   │   ├── lru.py
│   │   │   │   ├── lfu.py
│   │   │   │   └── adaptive.py
│   │   │   └── decorators.py
│   │   │
│   │   ├── messaging/              # 🔧 消息适配器
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── bus.py
│   │   │   │   ├── dispatcher.py
│   │   │   │   └── consumer.py
│   │   │   ├── kafka/
│   │   │   │   ├── producer.py
│   │   │   │   ├── consumer.py
│   │   │   │   ├── admin.py
│   │   │   │   └── config.py
│   │   │   ├── pulsar/
│   │   │   │   ├── producer.py
│   │   │   │   ├── consumer.py
│   │   │   │   ├── admin.py
│   │   │   │   └── config.py
│   │   │   └── codec/
│   │   │       ├── json.py
│   │   │       ├── avro.py
│   │   │       └── protobuf.py
│   │   │
│   │   ├── mapper/                 # 🔧 映射适配器
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── mapper.py
│   │   │   │   ├── strategy.py
│   │   │   │   ├── context.py
│   │   │   │   ├── converter.py
│   │   │   │   └── protocols.py
│   │   │   ├── registry/
│   │   │   │   ├── base.py
│   │   │   │   ├── dto.py
│   │   │   │   ├── po.py
│   │   │   │   └── vo.py
│   │   │   ├── dto/
│   │   │   │   └── base.py
│   │   │   ├── vo/
│   │   │   │   └── base.py
│   │   │   └── builder.py
│   │   │
│   │   ├── config/                 # 🔧 配置适配器
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── base.py
│   │   │   │   ├── manager.py
│   │   │   │   └── provider.py
│   │   │   └── providers/
│   │   │       ├── env.py
│   │   │       ├── json.py
│   │   │       └── yaml.py
│   │   │
│   │   ├── logger/                 # 🔧 日志适配器
│   │   │   ├── __init__.py
│   │   │   ├── manager.py
│   │   │   ├── context.py
│   │   │   └── processors/
│   │   │       ├── console.py
│   │   │       ├── file.py
│   │   │       ├── kafka.py
│   │   │       └── sentry.py
│   │   │
│   │   ├── observability/          # 🔧 观测性适配器
│   │   │   ├── __init__.py
│   │   │   ├── tracing/
│   │   │   │   └── opentelemetry.py
│   │   │   └── metrics/
│   │   │       └── prometheus.py
│   │   │
│   │   ├── identity/               # 🔧 认证适配器（可选）
│   │   │   ├── __init__.py
│   │   │   └── logto.py
│   │   │
│   │   └── storage/                # 🔧 存储适配器（可选）
│   │       ├── __init__.py
│   │       ├── minio.py
│   │       └── local.py
│   │
│   ├── interfaces/                  # ⭐ Layer 4: 接口层（外部接口）
│   │   ├── __init__.py
│   │   ├── http/                   # HTTP 接口
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── middleware.py
│   │   │   └── schemas/
│   │   ├── cli/                    # CLI 接口
│   │   │   └── __init__.py
│   │   └── grpc/                   # gRPC 接口（可选）
│   │       └── __init__.py
│   │
│   └── toolkit/                     # 🛠️ 工具集（代码生成等）
│       ├── __init__.py
│       ├── cli.py
│       └── templates/
│           ├── aggregate.py.tpl
│           ├── usecase.py.tpl
│           └── event.py.tpl
│
├── runtime/                         # 🚀 运行时（组合根）
│   ├── __init__.py
│   ├── bootstrap.py                # 应用启动
│   ├── container.py                # DI 容器
│   └── config.py                   # 运行时配置
│
├── examples/                        # 📚 示例项目
│   ├── minimal_app/                # 最小示例
│   │   └── main.py
│   ├── full_app/                   # 完整示例（订单系统）
│   │   ├── domain/
│   │   ├── application/
│   │   ├── adapters/
│   │   ├── interfaces/
│   │   └── runtime/
│   ├── best_practices/             # 最佳实践示例
│   │   ├── aggregate_design/
│   │   ├── event_sourcing/
│   │   ├── cqrs/
│   │   └── multi_tenant/
│   ├── specification_demo.py       # Specification 示例
│   ├── interceptor_demo.py         # Interceptor 示例
│   ├── mapper_demo.py              # Mapper 示例
│   ├── cache_demo.py               # Cache 示例
│   └── messaging_demo.py           # Messaging 示例
│
├── tests/                           # 🧪 测试目录
│   ├── unit/                       # 单元测试
│   │   ├── core/
│   │   ├── domain/
│   │   ├── application/
│   │   └── adapters/
│   │       ├── persistence/
│   │       ├── cache/
│   │       ├── messaging/
│   │       └── mapper/
│   ├── integration/                # 集成测试
│   │   ├── persistence/
│   │   │   ├── test_repository.py
│   │   │   ├── test_specification.py
│   │   │   ├── test_interceptor.py
│   │   │   ├── test_uow.py
│   │   │   └── test_outbox.py
│   │   ├── cache/
│   │   ├── messaging/
│   │   └── full_flow/
│   ├── performance/                # 性能测试
│   │   ├── benchmark_repository.py
│   │   ├── benchmark_specification.py
│   │   ├── benchmark_mapper.py
│   │   └── benchmark_cache.py
│   └── conftest.py                 # Pytest 配置
│
├── old/                             # 📦 旧实现（参考，迁移后归档）
│   └── ...                         # 保留作为参考
│
└── deploy/                          # 🐳 部署配置
    └── docker/
        └── compose.dev.yaml
```

---

## 🏗️ 架构层次说明

### Layer 0: Core（核心层）
- **职责**：提供最基础的抽象（ID、Result、Clock 等）
- **依赖**：无依赖
- **特点**：纯 Python，无外部库依赖

### Layer 1: Domain（领域层）
- **职责**：定义领域模型和领域端口
- **依赖**：只依赖 Core
- **特点**：
  - `entity.py`、`aggregate.py` 等领域概念
  - `ports/` 定义领域需要的端口（Repository、Specification 等）
  - 所有端口都是 Protocol（不依赖具体实现）

### Layer 2: Application（应用层）
- **职责**：定义用例和应用端口
- **依赖**：只依赖 Domain 和 Core
- **特点**：
  - `usecase.py`、`command.py`、`query.py` 等应用概念
  - `ports/` 定义应用需要的端口（UoW、Cache、MessageBus 等）
  - 所有端口都是 Protocol

### Layer 3: Adapters（适配器层）
- **职责**：实现端口，连接外部世界
- **依赖**：可以依赖 Domain、Application、Core，以及外部库
- **特点**：
  - **persistence/**：实现 Repository、UoW、Specification 端口
  - **cache/**：实现 Cache 端口
  - **messaging/**：实现 MessageBus 端口
  - **mapper/**：实现 Mapper 端口
  - 可以使用 SQLAlchemy、Redis、Kafka 等外部库

### Layer 4: Interfaces（接口层）
- **职责**：提供外部访问接口
- **依赖**：可以依赖所有内层
- **特点**：
  - **http/**：FastAPI/Flask 等 HTTP 接口
  - **cli/**：命令行接口
  - **grpc/**：gRPC 接口

---

## 🔌 端口与适配器映射

| 端口（Port）| 定义位置 | 适配器（Adapter）| 实现位置 |
|------------|---------|----------------|---------|
| **Repository** | `domain/ports/repository.py` | InMemoryRepository | `adapters/persistence/in_memory/repository.py` |
| | | SqlAlchemyRepository | `adapters/persistence/sqlalchemy/repository.py` |
| **Specification** | `domain/ports/specification.py` | CompositeSpecification | `adapters/persistence/specification/composite.py` |
| **EventPublisher** | `domain/ports/event_publisher.py` | PulsarEventPublisher ⭐ | `adapters/messaging/pulsar/publisher.py` |
| **UnitOfWork** | `application/ports/uow.py` | InMemoryUoW | `adapters/persistence/in_memory/uow.py` |
| | | SqlAlchemyUoW | `adapters/persistence/sqlalchemy/uow.py` |
| **Cache** | `application/ports/cache.py` | MemoryCache | `adapters/cache/backends/memory.py` |
| | | RedisCache | `adapters/cache/backends/redis.py` |
| **MessageBus** | `application/ports/message_bus.py` | PulsarMessageBus ⭐ | `adapters/messaging/pulsar/bus.py` |
| | | KafkaMessageBus (可选) | `adapters/messaging/kafka/bus.py` |
| **Mapper** | `application/ports/mapper.py` | GenericMapper | `adapters/mapper/core/mapper.py` |

---

## 📦 核心模块说明

### 🌟 拦截器系统（Interceptor）

**位置**：`src/adapters/persistence/interceptor/`

**价值**：横切关注点处理，避免重复代码

**核心组件**：
- **InterceptorChain**：责任链，按优先级执行拦截器
- **InterceptorContext**：上下文，传递拦截器间数据
- **标准拦截器**：
  - `AuditInterceptor`：自动记录创建人、修改人、时间
  - `SoftDeleteInterceptor`：软删除（逻辑删除）
  - `OptimisticLockInterceptor`：乐观锁（版本号）
  - `CacheInterceptor`：自动缓存管理
  - `LoggingInterceptor`：日志记录
  - `TransactionInterceptor`：事务管理
  - `OutboxInterceptor`：Outbox 模式

**示例**：
```python
# 使用拦截器
from bento.adapters.persistence.interceptor import InterceptorFactory

chain = InterceptorFactory.create_chain(
    enable_audit=True,
    enable_soft_delete=True,
    enable_optimistic_lock=True,
)

repo = SqlAlchemyRepository(session, UserPO, chain)
```

**注意**：本框架优先使用 **Apache Pulsar** 作为消息系统（而非 Kafka）。

### 🔍 Specification 模式

**位置**：`src/adapters/persistence/specification/`

**价值**：灵活的查询构建，可组合、可复用

**核心组件**：
- **CompositeSpecification**：组合规格，支持 AND、OR、NOT
- **Criteria**：各种查询条件（=、>、<、IN、LIKE 等）
- **Builder**：流式构建器

**示例**：
```python
# 构建复杂查询
from bento.adapters.persistence.specification import SpecificationBuilder

spec = SpecificationBuilder.for_entity(User) \
    .where("age").greater_than(18) \
    .and_("status").equals("active") \
    .or_("vip_level").in_([1, 2, 3]) \
    .order_by("created_at", desc=True) \
    .page(1, 20) \
    .build()

users = await repo.find_by_spec(spec)
```

### 🗺️ Mapper 系统

**位置**：`src/adapters/mapper/`

**价值**：自动化对象转换，减少样板代码

**核心组件**：
- **GenericMapper**：通用映射器
- **MapperBuilder**：流式构建器
- **MappingStrategy**：映射策略（自动、显式、自定义）
- **Registry**：映射器注册表

**示例**：
```python
# 构建 Mapper
from bento.adapters.mapper import MapperBuilder

mapper = MapperBuilder.for_types(UserEntity, UserDTO) \
    .map("id", "user_id") \
    .map_custom("full_name", lambda u: f"{u.first_name} {u.last_name}") \
    .auto_map() \
    .build()

dto = mapper.map(user_entity)
```

---

## ✅ import-linter 规则

```toml
[tool.importlinter]
root_package = "bento"

[[tool.importlinter.contracts]]
name = "Hexagonal layering"
type = "layers"
layers = [
  "bento.core",
  "bento.domain",
  "bento.application",
  "bento.adapters",
  "bento.interfaces",
]

[[tool.importlinter.contracts]]
name = "Domain ports are protocols"
type = "forbidden"
source_modules = ["bento.domain.ports"]
forbidden_modules = ["bento.adapters"]

[[tool.importlinter.contracts]]
name = "Application ports are protocols"
type = "forbidden"
source_modules = ["bento.application.ports"]
forbidden_modules = ["bento.adapters"]

[[tool.importlinter.contracts]]
name = "No adapters into domain or application"
type = "forbidden"
source_modules = ["bento.adapters"]
forbidden_modules = ["bento.domain", "bento.application"]
```

---

## 📊 对比：迁移前 vs 迁移后

| 特性 | 迁移前（current） | 迁移后（target） |
|------|------------------|----------------|
| **Repository** | 简单 Protocol + 内存实现 | 完整实现 + Interceptor + Specification |
| **UnitOfWork** | 抽象 Protocol | 完整实现 + ContextVar + Retry |
| **Specification** | ❌ 无 | ✅ 完整实现 |
| **Interceptor** | ❌ 无 | ✅ 8+ 拦截器 |
| **Mapper** | ❌ 无 | ✅ 完整实现 |
| **Cache** | 简单 Protocol | 多后端 + 多策略 |
| **Messaging** | 简单 Protocol | Pulsar 适配器（优先） |
| **文档** | 基础 | 完善（架构 + 端口 + 适配器 + 指南）|
| **测试** | 基础 | 完整（单元 + 集成 + 性能）|

---

**最后更新**：2025-01-04

