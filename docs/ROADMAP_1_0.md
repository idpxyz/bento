# Bento 1.0 Roadmap

目标：发布一个对外可用的 **Python DDD + 六边形架构框架**，包含完整示例应用 my‑shop，并保证核心 API 稳定、文档清晰、测试可靠。

---

## M1. 核心框架 API 稳定化

**目标**：冻结核心公共 API，在 1.x 期间避免随意破坏性变更。

**范围（候选稳定 API 清单）**：

- **Domain 层**
  - [x] `bento.domain.aggregate.AggregateRoot`
  - [x] `bento.domain.entity.Entity`
  - [x] `bento.domain.domain_event.DomainEvent`
  - [x] `bento.domain.ports.repository.IRepository[AR, ID]`

- **Application / UoW 层**
  - [x] `bento.application.ports.uow.UnitOfWork` 协议（如有别名一并确认）

- **Repository / Persistence 适配层**
  - [x] `bento.infrastructure.repository.adapter.RepositoryAdapter[AR, PO, ID]`
  - [x] `bento.infrastructure.repository.simple_adapter.SimpleRepositoryAdapter[AR, ID]`
  - [x] `bento.infrastructure.repository.inmemory.InMemoryRepository[AR]`
  - [x] `bento.persistence.repository.sqlalchemy.base.BaseRepository[PO, ID]`（仅作为持久层基类，标注为“技术稳定 API”）

- **Cache 子系统**
  - [x] `bento.adapters.cache.CacheBackend`
  - [x] `bento.adapters.cache.SerializerType`
  - [x] `bento.adapters.cache.CacheConfig`（含 `from_env`、`get_prefixed_key`）
  - [x] `bento.adapters.cache.MemoryCache`
  - [x] `bento.adapters.cache.RedisCache`
  - [x] `bento.adapters.cache.CacheFactory` / `create_cache`
  - [x] `bento.adapters.cache.CacheSerializer`

- **Outbox / Projector 子系统**
  - [x] `bento.persistence.outbox.record.OutboxRecord`
  - [x] `bento.persistence.outbox.listener.SqlAlchemyOutboxListener`（或当前命名）
  - [x] `bento.infrastructure.projection.projector.OutboxProjector`（或当前命名）

- **Specification / 分页**
  - [x] `bento.persistence.specification.core.types.Page[T]`
  - [x] `bento.persistence.specification.core.types.PageParams`
  - [x] `bento.persistence.specification.CompositeSpecification`
  - [x] `bento.persistence.specification.EntitySpecificationBuilder`

> 以上为“候选稳定 API”，需要逐个确认：名称是否满意、是否已经在示例和文档中使用，再决定是否纳入 1.0 的稳定范围。

**TODO**：

- [ ] 在 `docs/architecture` 中生成一份独立的 **Stable API 列表**（例如 `STABLE_API_1_0.md`），按上面分组整理。
- [ ] 对这些 API 做一次命名与签名复查（避免 1.0 后马上想改名）。
- [ ] 在 README/文档中标注哪些模块已视为稳定，哪些仍是实验性。

---

## M2. 文档 & 架构说明

**目标**：让新用户在 15–30 分钟内理解 Bento 的核心思想，并能跑起 my‑shop。

**范围**：

- 顶层文档
  - [ ] 更新 `README.md`：
    - [ ] 框架定位：Python DDD + Hexagonal Application Framework
    - [ ] 快速开始（Quickstart）：安装 + 启动 my‑shop
    - [ ] 链接到架构文档、示例文档
- 架构文档
  - [ ] 整理并对外发布：
    - `docs/architecture/Bento 评估 - 1124.md`（可以视为架构白皮书）
    - `docs/architecture/ORDER_FLOW.md`（下单端到端调用链）
    - `docs/architecture/PAGINATION_GUIDE.md`（分页策略与 Repository API）
    - `docs/architecture/CACHE_SERIALIZATION.md`（聚合根缓存序列化机制）
    - `docs/infrastructure/cache/CACHE_CONFIGURATION_GUIDE.md`（缓存配置与拦截器）
  - [ ] 在这些文档中加上统一的“目录导航”，从 README 可以一跳进入。
- 新手路线
  - [ ] 在 README 或单独文档中写一条“学习路线”：
    1. 跑起 my‑shop
    2. 看 `ORDER_FLOW.md` 理解端到端
    3. 看某一个 UseCase & Repository 实现

---

## M3. 示例应用 my‑shop 1.0

**目标**：保证 my‑shop 是推荐实践的示例，而不是临时 Demo。

**范围**：

- 业务功能（核心路径）
  - [x] 下单流程（创建订单、支付前状态）端到端跑通，并有 API 测试覆盖。
  - [x] 商品 / 分类 / 库存等查询与基本维护功能可用。
- 结构与配置
  - [ ] `applications/my-shop/README.md`：
    - [ ] 如何运行（依赖、命令、默认端口）
    - [ ] 配置说明：`.env` 与 `config/` 目录介绍
    - [ ] 关键架构点：UoW、RepositoryAdapter、Cache、Outbox
  - [ ] `.env` 与 `config/.env.example` 一致且与文档对齐（包括 `CACHE_*` 示例）。
- 测试
  - [x] 关键 API（例如 Product/Category/Order 若干接口）有 pytest 测试用例。
  - [x] 至少 1–2 条“业务场景”测试（例如完整下单流程）。

---

## M4. 测试与质量门槛

**目标**：为 1.0 设定一个最低质量线，避免“只靠感觉”。

**建议标准（可调整）**：

- 覆盖率
  - [ ] 核心模块（domain、repository、uow、cache、outbox）具有单元测试覆盖。
  - [ ] 总体测试覆盖率达到一个可接受的阈值（例如 >= 70%），并在 `TEST_RESULTS_SUMMARY.md` 中记录一次基准值。
- 回归保护
  - [ ] 所有新增的关键功能（如 `CacheConfig.from_env`, `CacheSerializer`, 新的 paginate API 等）配有针对性单测。
  - [ ] `uv run pytest` 在 CI 中固定跑一套（即使只是框架自身的测试）。

**交付物**：

- [ ] 更新 `TEST_RESULTS_SUMMARY.md` 或在 README 中添加一节“Testing & Quality”。
- [ ] 确定 1.0 发布前需要通过的测试命令（例如 `uv run pytest`）。

---

## M5. 对外发布准备

**目标**：为在 GitHub / PyPI 上公开发布做准备，让外部开发者易于理解和参与。

**范围**：

- 开源基础
  - [ ] 选择并添加 LICENSE（MIT / Apache-2.0 等）。
  - [ ] `CONTRIBUTING.md`：
    - [ ] 如何运行测试
    - [ ] 提交 PR 的基本要求
    - [ ] 代码风格说明（例如使用 uv + pytest + flake8 等）
- 包元数据
  - [ ] 检查并完善 `pyproject.toml`：
    - [ ] 项目名称、描述、作者、主页、Python 版本
    - [ ] 将核心包 `bento` 标记为可发布
- Roadmap / 版本策略
  - [ ] 在 README 或单独文档中简要描述：
    - 1.0 的范围（本文件）
    - 1.x 可能演进方向（如 OTel 集成、更丰富的示例、更多 Adapter）

---

## 总结

完成以上 M1–M5 后，Bento 可以自信地发布为 **1.0.0**：

- 作为一个结构清晰的 Python DDD + 六边形框架；
- 拥有完整示例 my‑shop 作为最佳实践；
- 拥有清晰的文档、合理的测试与基本的开源治理文件。

后续 1.x 版本可以在不破坏核心 API 的前提下，迭代：

- 更丰富的 Adapter 与集成（如 OTel、更多消息中间件）；
- 更多上下文的示例应用；
- 更强的 DX 工具（CLI、Codegen 等）。
