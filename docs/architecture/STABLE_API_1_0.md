# Bento 1.0 Stable API 列表

本文件列出计划在 **Bento 1.0** 中视为“稳定（Stable）”的公共 API。稳定意味着：

- 1.x 版本中不会随意改变其名称、模块路径或函数/方法签名；
- 如需破坏性变更，会在 2.0 之后进行，或提供兼容层；
- 推荐应用和示例（如 my‑shop）优先使用这些 API。

> 说明：这里的“稳定”只针对 **对外可见的接口**，内部实现仍可能在 1.x 中重构。

---

## 1. Domain 层

这些类型定义了领域模型的基础，是所有聚合根与实体的基类和语义约束。

- ✅ `bento.domain.aggregate.AggregateRoot`
  - 聚合根基类，提供：
    - ID 管理
    - 领域事件收集
    - `to_cache_dict()` 默认缓存序列化行为
- ✅ `bento.domain.entity.Entity`
  - 实体基类，提供 ID 等通用行为。
- ✅ `bento.domain.domain_event.DomainEvent`
  - 领域事件基类，Outbox 等机制依赖该抽象。
- ✅ `bento.domain.ports.repository.IRepository[AR, ID]`
  - 仓储端口协议，定义聚合根级别的持久化契约。

> 这些类型是 DDD 语义的核心，将在 1.x 中保持稳定。

---

## 2. Application / UoW 层

- ✅ `bento.application.ports.uow.UnitOfWork`（及其等价协议）
  - 应用层获取仓储、控制事务的标准入口。
  - my‑shop 中所有用例（UseCase）通过 UoW 获取 Repository。

> UoW 是串联 Application 与 Infrastructure 的关键端口，1.x 期间只会在实现细节上演进，不会随意改动接口语义。

---

## 3. Repository / Persistence 适配层

### 3.1 AR 层适配器

- ✅ `bento.infrastructure.repository.adapter.RepositoryAdapter[AR, PO, ID]`
  - 聚合根仓储的通用适配器：
    - 封装 AR ↔ PO 映射；
    - 面向 `IRepository` 暴露统一 API（`get`, `save`, `find_all`, `paginate`, `find_page` 等）。
- ✅ `bento.infrastructure.repository.simple_adapter.SimpleRepositoryAdapter[AR, ID]`
  - 适用于 AR=PO 的简单场景（无复杂映射），保留为简化版适配器。
- ✅ `bento.infrastructure.repository.inmemory.InMemoryRepository[AR]`
  - 内存仓储实现，主要用于测试和示例。

### 3.2 持久层基类

- ✅ `bento.persistence.repository.sqlalchemy.base.BaseRepository[PO, ID]`
  - SQLAlchemy 持久化层基类，面向基础设施开发者（通常不直接在应用层使用）。
  - 作为“技术稳定 API”：路径与核心方法在 1.x 中保持稳定，但不建议业务代码直接依赖。

---

## 4. Cache 子系统

这些类型为应用提供统一的缓存接口和配置方式。

- ✅ `bento.adapters.cache.CacheBackend`
  - 缓存后端枚举：`MEMORY` / `REDIS`。
- ✅ `bento.adapters.cache.SerializerType`
  - 序列化方式枚举：`JSON` / `PICKLE`。
- ✅ `bento.adapters.cache.CacheConfig`
  - 缓存配置对象，字段：`backend`, `prefix`, `ttl`, `max_size`, `redis_url`, `serializer`, `enable_stats`, `enable_breakdown_protection`。
  - 方法：
    - `from_env()`：从环境变量构造配置（已具备严格验证与清晰错误信息）。
    - `get_prefixed_key()`：统一处理 key 前缀。
- ✅ `bento.adapters.cache.MemoryCache`
  - 进程内缓存实现（LRU + TTL）。
- ✅ `bento.adapters.cache.RedisCache`
  - 基于 `redis.asyncio` 的分布式缓存实现。
- ✅ `bento.adapters.cache.CacheFactory` / `create_cache`
  - 根据 `CacheConfig` 创建适当的缓存实例（Memory / Redis）。
- ✅ `bento.adapters.cache.CacheSerializer`
  - 统一缓存序列化工具：
    - `make_serializable(value)`：将聚合根 / 列表 / 字典转换为 JSON 友好结构；
    - `serialize(value, serializer_type)`：序列化为 bytes；
    - `deserialize(data, serializer_type)`：反序列化为 Python 对象。

> 这些 API 是 Cache 子系统的对外入口，1.x 中会尽量保持签名与行为稳定。

---

## 5. Outbox / Projector 子系统

用于实现可靠事件发布和跨界限上下文集成。

- ✅ `bento.persistence.outbox.record.OutboxRecord`
  - Outbox 表对应的记录模型/结构，定义了事件持久化格式。
- ✅ `bento.persistence.outbox.listener.SqlAlchemyOutboxListener`（或当前对应实现）
  - 监听 SQLAlchemy 事务事件，将领域事件写入 Outbox。
- ✅ `bento.infrastructure.projection.projector.OutboxProjector`
  - 从 Outbox 表读取记录并投递到下游（消息中间件 / 其他 BC），为事件驱动集成提供基础。

> 这些组件为“事务 + 事件”提供基础设施，API 在 1.x 视为稳定，后续如扩展只会增加新实现，而非破坏现有接口。

---

## 6. Specification / 分页

- ✅ `bento.persistence.specification.core.types.Page[T]`
  - 通用分页结果类型，包含：`items`, `total`, `total_pages`, `has_next`, `has_prev`。
- ✅ `bento.persistence.specification.core.types.PageParams`
  - 分页参数：`page`, `size`, `offset`, `limit`，用于驱动仓储分页查询。
- ✅ `bento.persistence.specification.CompositeSpecification`
  - 组合查询条件的抽象，用于仓储查询。
- ✅ `bento.persistence.specification.EntitySpecificationBuilder`
  - Fluent API 风格的 Specification 构建器，用于 Application 层构造查询条件。

> 这些类型在分页与复杂查询中被广泛使用，已在文档和 my‑shop 示例中使用，计划作为 1.0 的稳定查询抽象。

---

## 7. 使用建议

- 应用和示例（如 my‑shop）在依赖 Bento 时，应优先依赖以上 Stable API。
- 如需使用未在本文件列出的内部模块，应在代码中显式标注为“内部实现依赖”，避免未来版本升级时造成大面积 break。
- 后续若新增稳定 API，将在本文件和 CHANGELOG 中进行补充说明。
