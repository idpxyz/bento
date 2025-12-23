下面我把“Bento 应具备的能力”进一步落到 **可冻结的规格**：能力分层、模块清单、强制规范（MUST）与可选规范（SHOULD）、以及你可以直接拿去做门禁与脚手架的“对照表”。我会按我们当前的工程现实（LOMS vNext、contracts-as-code、outbox/inbox/dlq、registry/wiring、multi-tenant）来写。

---

## A. Bento 能力分层模型

将 Bento 明确成三层产品，而不是一个脚手架：

### L0：规范层（Standards）

* 命名、目录、依赖方向、合约结构、错误结构、事件 envelope、状态机表达方式
* 目的：保证“写法一致、可被工具校验”

### L1：门禁层（Gates）

* 静态门禁：依赖规则、合约校验、breaking change、lint/typecheck/test
* 运行门禁：启动前检查配置完整性、合约版本一致性、关键依赖可达性
* 目的：保证“做错就过不了 CI / 起不来”

### L2：运行时与组件层（Runtime + Components）

* Outbox/Inbox/DLQ/Idempotency、log/metrics/tracing、config、module wiring
* 目的：保证“有能力跑、且可运维可诊断”

> 结论：Bento 的价值不在“生成目录”，而在“标准化 + 可验证 + 可运营”。

---

## B. Bento 的模块清单（建议冻结为产品规格）

我建议 Bento 的模块以 **“平台能力包（platform packs）”** 的方式提供，每个包都定义：接口（Ports）、默认实现（Adapters）、配置、指标、Runbook。

### 1) `platform.contracts`（Contracts-as-Code）

**必须具备：**

* OpenAPI 校验（schema + examples + error model + pagination + idempotency headers）
* Event schema 校验（envelope + payload schema + examples）
* Reason-codes 冻结（含 retryable 规则、HTTP 映射、业务拒绝语义）

**建议内建工具：**

* `bento contracts lint`
* `bento contracts diff`（breaking change 检测）
* `bento sdk gen`（生成 SDK / mock server）

### 2) `platform.reliability`（可靠性组件套件）

**必须具备“四件套”：**

* Outbox（事务内写、worker 投递、状态机、重试退避、投递指标）
* Inbox（入站去重、幂等消费、处理结果记录）
* DLQ（死信结构、重试上限、人工干预入口、回放工具）
* Idempotency（命令幂等键、结果缓存、冲突处理）

**建议内建：**

* 统一的 `event_id` 去重策略 + `command_id` 幂等策略
* “回放保护”：回放必须走 inbox 去重与业务前置条件检查

### 3) `platform.observability`（可观测性）

**必须具备：**

* 结构化日志：强制字段集（tenant/correlation/causation/trace/request/bc/module）
* Metrics：outbox backlog、投递成功率、DLQ 数、consumer lag、API latency 等
* Tracing：HTTP→Command→DB tx→Outbox→MQ→Consumer 全链路

**建议内建：**

* correlation/causation 自动注入（HTTP 入站生成、事件消费沿用）
* 默认 OpenTelemetry exporter 插拔（console/OTLP 等）

### 4) `platform.runtime` 或 `platform.bootstrap`（装配与启动一致性）

**必须具备：**

* Module Registry：模块声明、依赖关系、启动顺序、启停钩子
* Wiring：配置驱动选择 adapters（db/mq/cache）
* Loader：读取配置、加载 contracts、加载 feature gates
* Gates：启动前健康检查（配置项完整性、依赖可达性）

**建议内建：**

* “环境分层配置模型”（local/dev/staging/prod）
* “模块可观测性”：启动时打印装配图摘要（不泄露密钥）

### 5) `platform.persistence`（数据与持久化规范）

**必须具备：**

* Async SQLAlchemy v2 规范模板（Session/UoW/Repository 基类）
* Alembic 规范（迁移命名、依赖顺序、回滚策略）
* 多租户注入规范（tenant context → DB session）

### 6) `platform.security`（鉴权与租户上下文）

**必须具备（在 LOMS/Gatekeeper 体系下）：**

* 租户上下文（tenant_id / org_id / user_id）统一注入
* 权限校验作为 Adapter（不污染 Domain）
* 审计接口（至少接口定义 + 可选实现）

---

## C. “MUST / SHOULD / MAY” 冻结规则（可直接写进 Bento Spec）

下面这些建议直接作为 Bento 的**强制门禁规则**。

### MUST（不满足即拒绝合并）

1. **Domain 层禁止依赖** Web 框架/ORM/消息中间件（依赖方向硬门禁）
2. 所有对外 API **必须有 OpenAPI + examples + error model**
3. 所有跨进程事件 **必须有 schema + examples + version**
4. 所有异步发布事件 **必须走 Outbox**（除非显式标记为“非一致性事件”，且在 spec 中声明）
5. 所有 consumer **必须实现 Inbox 去重**
6. 所有写操作接口 **必须支持 Idempotency-Key**
7. 必须打点：outbox backlog、DLQ count、consumer lag、p95/p99
8. 必须携带：correlation_id / causation_id（HTTP 入口生成，事件链路传递）

### SHOULD（强烈建议，允许阶段性豁免但要记录 ADR）

1. 关键聚合的状态机应显式表达（状态迁移表 + 命令前置条件 + 拒绝码）
2. 每个 BC 提供 runbook（DLQ 排障、回放步骤、常见问题）
3. 合约 breaking change 检测作为 release gate
4. Feature gates 支持租户级/环境级开关

### MAY（可选增强）

1. Saga/Process Manager 模板
2. 自动生成 Postman / Insomnia 集合
3. 自动生成事件路由矩阵报告

---

## D. Bento 交付物（你们最该“产品化”的东西）

如果你要把 Bento 做成“可复用资产”，交付物应当不仅是代码，还包括：

1. **Bento Spec（规范）**

* 目录与依赖规则、合约规范、事件规范、错误结构、reason-codes、版本策略

2. **Bento Gates（门禁）**

* CI pipeline 模板（lint/typecheck/test/arch/contracts/breaking-change）
* 本地一键 `bento check`

3. **Bento Packs（能力包实现）**

* reliability pack、observability pack、runtime/bootstrap pack、persistence pack、security pack

4. **Bento Skeleton Generators（脚手架生成器）**

* `bento new bc <name>`
* `bento new context <name>`
* `bento add pack reliability|observability|contracts ...`

5. **Reference BC（参考实现）**

* 至少 1 个“演示 BC”，覆盖：API + Outbox + Consumer + DLQ + tracing

---

## E. “能力—目录—门禁”对照表（可直接变成 checklist）

| 能力                | 目录落点（建议）                          | 门禁/检查项                             |
| ----------------- | --------------------------------- | ---------------------------------- |
| OpenAPI 合约        | `shared/contracts/openapi/*`      | schema+examples 校验、breaking change |
| Event schema      | `shared/contracts/events/*`       | envelope+payload+examples 校验       |
| reason-codes      | `shared/contracts/reason-codes/*` | retryable 规则校验、HTTP 映射             |
| Outbox            | `shared/infra/outbox/*`           | 事务内写、worker 投递、指标与重试               |
| Inbox             | `shared/infra/inbox/*`            | 去重表、消费幂等、回放复用                      |
| DLQ               | `shared/infra/dlq/*`              | 死信结构、上限策略、runbook                  |
| Idempotency       | `shared/infra/idempotency/*`      | header 支持、冲突语义、存储                  |
| Logging           | `shared/platform/log/*`           | 必填字段、脱敏                            |
| Metrics           | `shared/platform/metrics/*`       | outbox/DLQ/lag/p95                 |
| Tracing           | `shared/platform/tracing/*`       | correlation/causation 传递           |
| Runtime/Bootstrap | `bootstrap/*`                     | registry/wiring/entrypoints + 启动门禁 |

---

## F. 下一步我建议我们直接冻结两份“可执行规格”

为了让 Bento 真正进入 M0，我建议你让我继续输出以下两份文档（可直接放 repo）：

1. **Bento Spec v1（冻结版）**：MUST/SHOULD/MAY + 合约规范 + envelope + error model + versioning
2. **Bento Gates v1（可执行版）**：`bento check` 包含哪些检查、每条检查的失败示例、CI pipeline 模板

如果你同意，我可以在下一条消息里直接把 **Bento Spec v1** 用“可直接落盘”的结构写出来（包含目录树、字段定义、错误结构 JSON、event envelope JSON、reason-codes 示例、门禁命令清单）。
