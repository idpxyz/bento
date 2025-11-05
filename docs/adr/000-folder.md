# Bento 框架目录结构说明

**版本**: 1.0
**最后更新**: 2025-11-05
**状态**: Living Document

---

## 📋 目录结构总览

```text
bento/
├─ .github/workflows/         # GitHub Actions CI/CD 流水线
├─ .pre-commit-config.yaml    # 代码质量钩子
├─ .editorconfig .gitignore
├─ LICENSE  Makefile  README.md  pyproject.toml  uv.lock
│
├─ docs/                      # 📚 文档与规范
│  ├─ adr/                    # 架构决策记录 (ADR)
│  │  ├─ 0001-architecture.md
│  │  └─ 003-database-infrastructure.md
│  ├─ architecture/           # 架构设计文档
│  │  └─ TARGET_STRUCTURE.md
│  ├─ conventions/            # 分层/命名/事务/事件约定
│  ├─ design/                 # 详细设计文档
│  │  ├─ ADAPTER_MAPPER_DESIGN.md
│  │  ├─ PROJECTION_EVALUATION.md
│  │  └─ DATABASE_INFRASTRUCTURE_DESIGN.md
│  ├─ diagrams/               # 架构/上下文/时序图
│  ├─ infrastructure/         # 基础设施使用指南
│  │  ├─ MESSAGING_USAGE.md
│  │  ├─ CACHE_ENHANCED_USAGE.md
│  │  ├─ PROJECTION_USAGE.md
│  │  └─ DATABASE_USAGE.md
│  └─ ports/                  # 端口接口说明
│
├─ deploy/                    # 🚀 部署与环境
│  ├─ docker/
│  │  └─ compose.dev.yaml     # 本地开发环境：Postgres/Redis/Pulsar
│  └─ k8s/                    # Kubernetes 部署模板
│     ├─ Chart.yaml
│     └─ templates/
│
├─ scripts/                   # 🔧 工程脚本
│  ├─ dev.sh                  # 本地开发
│  ├─ lint.sh                 # 代码检查
│  └─ test.sh                 # 测试运行
│
├─ src/bento/                 # ⭐ 框架核心（可发布包）
│  │
│  ├─ core/                   # 🎯 Shared Kernel：基础类型与通用工具
│  │  ├─ result.py            # Result/Ok/Err 函数式错误处理
│  │  ├─ ids.py               # ID 类型（UUID 封装）
│  │  ├─ guard.py             # 领域不变式守卫
│  │  ├─ clock.py             # 可注入时钟
│  │  └─ errors.py            # 错误分层：BentoException 层次结构
│  │
│  ├─ domain/                 # 🏛️ 纯领域基类与战术构件
│  │  ├─ entity.py            # Entity 基类
│  │  ├─ aggregate.py         # AggregateRoot 基类（支持事件）
│  │  ├─ value_object.py      # ValueObject 基类
│  │  ├─ domain_event.py      # DomainEvent 基类
│  │  ├─ event_registry.py    # 事件注册与反序列化
│  │  └─ specification.py     # 规约模式（组合 And/Or/Not）
│  │
│  ├─ application/            # 📋 应用层：用例/事务/幂等
│  │  ├─ ports/               # 端口接口定义
│  │  │  ├─ message_bus.py    # MessageBus 抽象
│  │  │  ├─ uow.py            # IUnitOfWork 抽象
│  │  │  └─ repository.py     # IRepository 抽象
│  │  ├─ dto.py               # 数据传输对象基类
│  │  └─ command.py           # Command 基类
│  │
│  ├─ messaging/              # 📨 消息与事件总线抽象
│  │  ├─ message_envelope.py  # 消息封装
│  │  └─ topics.py            # 主题命名规范
│  │
│  ├─ persistence/            # 💾 持久化与仓储基座
│  │  ├─ uow.py               # SQLAlchemyUnitOfWork 实现
│  │  ├─ repository/          # 仓储基类
│  │  │  ├─ base.py           # BaseRepository
│  │  │  └─ sqlalchemy/       # SQLAlchemy 仓储实现
│  │  ├─ specification/       # 规约模式实现
│  │  │  ├─ core/             # 核心规约类型
│  │  │  ├─ criteria/         # 查询条件构建
│  │  │  └─ builder/          # 规约构建器
│  │  └─ sqlalchemy/          # SQLAlchemy 集成
│  │     ├─ base.py           # Base 声明式映射
│  │     ├─ outbox_sql.py     # Outbox 表模型与实现
│  │     └─ outbox_listener.py # Outbox 事件监听器
│  │
│  ├─ infrastructure/         # 🔌 基础设施抽象与实现
│  │  ├─ database/            # ⭐ 数据库基础设施（新增）
│  │  │  ├─ __init__.py       # 公开 API
│  │  │  ├─ config.py         # 配置管理（Pydantic）
│  │  │  ├─ session.py        # 会话工厂
│  │  │  ├─ lifecycle.py      # 生命周期管理
│  │  │  ├─ draining.py       # 连接耗尽（优雅关闭）
│  │  │  ├─ engines/          # 引擎抽象
│  │  │  │  ├─ base.py        # DatabaseEngine 基类
│  │  │  │  ├─ postgres.py    # PostgreSQL 优化
│  │  │  │  └─ sqlite.py      # SQLite 优化
│  │  │  └─ resilience/       # 弹性处理
│  │  │     ├─ errors.py      # 错误分类
│  │  │     └─ retry.py       # 重试机制
│  │  ├─ projection/          # Outbox Projector（事件发布）
│  │  │  └─ projector.py      # OutboxProjector 实现
│  │  ├─ mapper/              # AR ↔ PO 映射器
│  │  │  ├─ base.py           # Mapper 基类
│  │  │  └─ simple.py         # SimpleMapper 实现
│  │  ├─ repository/          # 仓储适配器
│  │  │  └─ simple_adapter.py # SimpleRepositoryAdapter
│  │  ├─ cache.py             # Cache 抽象
│  │  ├─ locker.py            # 分布式锁抽象
│  │  ├─ storage.py           # 对象存储抽象
│  │  ├─ search.py            # 搜索引擎抽象
│  │  ├─ emailer.py           # 邮件服务抽象
│  │  └─ tx.py                # 事务抽象
│  │
│  ├─ interfaces/             # 🌐 外部接口基座
│  │  ├─ http.py              # HTTP 控制器基类
│  │  └─ scheduler.py         # 任务调度基类
│  │
│  ├─ security/               # 🔐 身份/授权/多租户
│  │  ├─ context.py           # RequestContext（Tenant/User）
│  │  ├─ auth.py              # 认证
│  │  └─ rbac.py              # 基于角色的访问控制
│  │
│  ├─ observability/          # 📊 可观测性
│  │  ├─ logging.py           # 日志
│  │  ├─ tracing.py           # 链路追踪
│  │  ├─ metrics.py           # 指标
│  │  └─ audit.py             # 审计
│  │
│  ├─ toolkit/                # 🛠️ 代码生成器
│  │  ├─ cli.py               # CLI 工具
│  │  └─ templates/           # 代码模板
│  │
│  └─ adapters/               # 🔌 框架内部适配器
│     ├─ cache/               # 缓存适配器
│     └─ repository/          # 仓储适配器
│
├─ adapters/                  # 🔌 官方参考适配器（外部依赖）
│  ├─ cache/
│  │  └─ redis_cache.py       # Redis Cache 实现
│  ├─ messaging/
│  │  ├─ pulsar_bus.py        # Pulsar EventBus
│  │  └─ kafka_bus.py         # Kafka EventBus
│  ├─ storage/
│  │  └─ minio_store.py       # MinIO 对象存储
│  └─ search/
│     └─ opensearch_engine.py # OpenSearch 搜索引擎
│
├─ runtime/                   # ⚙️ 运行时装配（组合根）
│  ├─ bootstrap.py            # 应用启动入口
│  ├─ composition.py          # 依赖注入组装
│  └─ jobs.py                 # 后台任务入口
│
├─ applications/              # 📦 示例应用（不进入发行包）
│  └─ ecommerce/              # 电商应用示例
│     ├─ docs/                # 应用文档
│     │  ├─ ARCHITECTURE.md   # 应用架构说明
│     │  └─ DIRECTORY_STRUCTURE.md
│     ├─ modules/             # 业务模块
│     │  └─ order/            # 订单模块
│     │     ├─ domain/        # 领域层
│     │     │  ├─ order.py    # Order 聚合根
│     │     │  └─ events.py   # 订单事件
│     │     ├─ application/   # 应用层
│     │     │  └─ commands/   # 命令处理
│     │     ├─ adapters/      # 适配器层
│     │     │  └─ order_repository.py
│     │     └─ interfaces/    # 接口层
│     │        └─ order_api.py
│     ├─ persistence/         # 持久化模型
│     │  └─ models.py         # SQLAlchemy 模型
│     ├─ runtime/             # 运行时配置
│     │  └─ composition.py    # DI 组装
│     └─ tests/               # 应用测试
│
├─ examples/                  # 📖 可运行示例
│  ├─ minimal_app/            # 最小化应用
│  ├─ messaging/              # 消息系统示例
│  ├─ cache/                  # 缓存系统示例
│  └─ error_codes/            # 错误码示例
│
└─ tests/                     # 🧪 测试套件
   ├─ unit/                   # 单元测试
   │  ├─ core/                # 核心模块测试
   │  ├─ domain/              # 领域层测试
   │  ├─ application/         # 应用层测试
   │  └─ persistence/         # 持久化测试
   ├─ integration/            # 集成测试
   │  ├─ persistence/         # 持久化集成测试
   │  ├─ messaging/           # 消息系统集成测试
   │  └─ cache/               # 缓存集成测试
   ├─ e2e/                    # 端到端测试
   └─ performance/            # 性能测试
```

---

## 📚 各目录职责详解

### 🏗️ 顶层工程文件

| 文件 | 职责 | 说明 |
|------|------|------|
| `pyproject.toml` | 项目配置 | 包管理、依赖、构建配置 |
| `uv.lock` | 依赖锁定 | uv 包管理器锁定文件 |
| `Makefile` | 快捷命令 | `make fmt \| lint \| test \| dev` |
| `.pre-commit-config.yaml` | 提交钩子 | 代码质量门禁 |
| `.github/workflows/` | CI/CD | 自动化流水线 |

### 📚 docs/ - 文档规范

#### adr/ - 架构决策记录

记录所有关键架构决策，包括：
- `0001-architecture.md`: 整体架构决策
- `003-database-infrastructure.md`: 数据库基础设施决策

**原则**: 每个重要架构决策都应有对应的 ADR。

#### design/ - 详细设计文档

包含具体功能模块的设计文档：
- `ADAPTER_MAPPER_DESIGN.md`: 适配器和映射器设计
- `PROJECTION_EVALUATION.md`: Projector 实现评估
- `DATABASE_INFRASTRUCTURE_DESIGN.md`: 数据库基础设施设计

#### infrastructure/ - 使用指南

面向开发者的使用文档：
- `DATABASE_USAGE.md`: 数据库使用指南（1240 行）
- `MESSAGING_USAGE.md`: 消息系统使用指南
- `CACHE_ENHANCED_USAGE.md`: 缓存增强使用指南
- `PROJECTION_USAGE.md`: Projector 使用指南

#### conventions/ - 团队约定

团队开发规范（命名、分层依赖矩阵等）

### 🚀 deploy/ - 部署

#### docker/
- `compose.dev.yaml`: 本地开发环境（Postgres/Redis/Pulsar）

#### k8s/
- Helm 模板：生产环境部署配置

### ⭐ src/bento/ - 框架核心

#### 1️⃣ core/ - Shared Kernel

**职责**: 通用基础设施，纯 Python，零外部依赖

**包含**:
- `result.py`: 函数式错误处理（Result/Ok/Err）
- `ids.py`: ID 类型封装
- `guard.py`: 领域守卫
- `clock.py`: 可注入时钟
- `errors.py`: 异常层次结构

**原则**: ✅ 零外部依赖，✅ 高度可复用

#### 2️⃣ domain/ - 领域层

**职责**: 纯领域基类，战术 DDD 构件

**包含**:
- `entity.py`: Entity 基类
- `aggregate.py`: AggregateRoot 基类（支持事件）
- `value_object.py`: ValueObject 基类
- `domain_event.py`: DomainEvent 基类
- `event_registry.py`: 事件注册与反序列化
- `specification.py`: 规约模式

**原则**:
- ✅ 不依赖外部 I/O
- ✅ 不依赖 adapters
- ✅ 纯业务逻辑

#### 3️⃣ application/ - 应用层

**职责**: 用例编排，定义端口接口

**包含**:
- `ports/`: 端口接口定义
  - `message_bus.py`: MessageBus 抽象
  - `uow.py`: IUnitOfWork 抽象
  - `repository.py`: IRepository 抽象
- `dto.py`: 数据传输对象
- `command.py`: Command 基类

**原则**:
- ✅ 只编排，不做 I/O
- ✅ 依赖抽象（Ports）
- ✅ 不依赖具体实现

#### 4️⃣ persistence/ - 持久化层

**职责**: 仓储实现，UoW 实现，规约模式

**包含**:
- `uow.py`: SQLAlchemyUnitOfWork 实现
  - 事务管理
  - 聚合跟踪
  - 事件收集
  - Outbox 集成
- `repository/`: 仓储基类和实现
- `specification/`: 规约模式实现
  - 查询条件构建
  - 规约组合（And/Or/Not）
- `sqlalchemy/`: SQLAlchemy 集成
  - `outbox_sql.py`: Outbox 表模型
  - `outbox_listener.py`: Outbox 事件监听器

**原则**:
- ✅ 实现 Application 层定义的端口
- ✅ 与具体数据库技术隔离

#### 5️⃣ infrastructure/ - 基础设施层

**职责**: 基础设施抽象与实现

##### 🌟 database/ - 数据库基础设施（新增）

**P0+P1 已完成，生产就绪**

```
database/
├── config.py           # 配置管理（Pydantic）
├── session.py          # 会话工厂
├── lifecycle.py        # 生命周期管理
├── draining.py         # 连接耗尽（优雅关闭）
├── engines/            # 引擎抽象
│   ├── base.py         # DatabaseEngine 基类
│   ├── postgres.py     # PostgreSQL 优化
│   └── sqlite.py       # SQLite 优化
└── resilience/         # 弹性处理
    ├── errors.py       # 智能错误分类（30+ 模式）
    └── retry.py        # 重试机制（指数退避+抖动）
```

**功能**:
- ✅ 环境变量配置
- ✅ 数据库特定优化（PostgreSQL JSONB、SQLite NullPool）
- ✅ 智能错误分类和重试
- ✅ 三种连接耗尽模式
- ✅ Kubernetes/Docker 友好
- ✅ 生产级别可靠性

**文档**:
- 使用指南: `docs/infrastructure/DATABASE_USAGE.md` (1240 行)
- 设计文档: `docs/design/DATABASE_INFRASTRUCTURE_DESIGN.md` (1076 行)
- ADR: `docs/adr/003-database-infrastructure.md` (731 行)

##### projection/ - Outbox Projector

- `projector.py`: OutboxProjector 实现
  - 轮询 Outbox 表
  - 发布事件到消息总线
  - 状态管理（NEW → SENT/ERR）
  - 批量处理和自适应休眠

##### mapper/ - 映射器

- `base.py`: Mapper 基类（AR ↔ PO）
- `simple.py`: SimpleMapper 实现

##### repository/ - 仓储适配器

- `simple_adapter.py`: SimpleRepositoryAdapter
  - 连接 Domain Repository 和 Infrastructure

##### 其他基础设施抽象

- `cache.py`: Cache 抽象（支持 Redis）
- `locker.py`: 分布式锁
- `storage.py`: 对象存储（支持 MinIO）
- `search.py`: 搜索引擎（支持 OpenSearch）
- `emailer.py`: 邮件服务
- `tx.py`: 事务抽象

#### 6️⃣ interfaces/ - 接口层

**职责**: 外部接口基座（协议无关）

- `http.py`: HTTP 控制器基类
- `scheduler.py`: 任务调度基类

#### 7️⃣ security/ - 安全层

**职责**: 身份、授权、多租户

- `context.py`: RequestContext（Tenant/User/Scopes）
- `auth.py`: 认证
- `rbac.py`: 基于角色的访问控制

#### 8️⃣ observability/ - 可观测性

**职责**: 日志、追踪、指标、审计

- `logging.py`: 统一日志
- `tracing.py`: 分布式追踪
- `metrics.py`: 性能指标
- `audit.py`: 审计日志

### 🔌 adapters/ - 官方适配器

**职责**: 外部依赖的官方实现

| 适配器 | 技术 | 状态 |
|--------|------|------|
| `cache/redis_cache.py` | Redis | ✅ 已实现 |
| `messaging/pulsar_bus.py` | Pulsar | ✅ 已实现 |
| `messaging/kafka_bus.py` | Kafka | ⚠️ 部分实现 |
| `storage/minio_store.py` | MinIO | ✅ 已实现 |
| `search/opensearch_engine.py` | OpenSearch | ✅ 已实现 |

**特点**:
- 按需安装（不强制依赖）
- 在 `runtime/composition.py` 中装配

### ⚙️ runtime/ - 运行时组合根

**职责**: 依赖注入，应用启动

- `bootstrap.py`: FastAPI 应用创建，路由注册
- `composition.py`: 依赖注入装配（db/mq/cache/search）
- `jobs.py`: 后台任务入口（Outbox Publisher、消费者）

**原则**:
- ✅ 所有依赖在此装配
- ✅ 生产/开发环境切换在此配置

### 📦 applications/ - 示例应用

#### ecommerce/ - 电商应用

**架构**: 六边形架构 + DDD + CQRS + Event-Driven

**结构**:
```
ecommerce/
├─ modules/order/          # 订单模块
│  ├─ domain/              # 领域层（Order 聚合根）
│  ├─ application/         # 应用层（Use Cases）
│  ├─ adapters/            # 适配器层（Repository）
│  └─ interfaces/          # 接口层（API）
├─ runtime/composition.py  # DI 组装
└─ docs/ARCHITECTURE.md    # 架构文档
```

**特点**:
- ✅ 完整的 DDD 实现
- ✅ 自动事件收集和发布
- ✅ 使用数据库基础设施
- ✅ 符合 Bento 架构原则

### 📖 examples/ - 可运行示例

- `minimal_app/`: 最小化 FastAPI 应用
- `messaging/`: 消息系统示例
- `cache/`: 缓存系统示例
- `error_codes/`: 错误码示例

### 🧪 tests/ - 测试套件

#### unit/ - 单元测试

- `core/`: 核心模块（Result、Guard、Errors）
- `domain/`: 领域层（Entity、Aggregate、ValueObject）
- `application/`: 应用层
- `persistence/`: 持久化（UoW、Repository）

#### integration/ - 集成测试

- `persistence/`: 数据库集成测试
  - **10/10 Outbox Pattern 测试通过** ✅
- `messaging/`: 消息系统集成测试
- `cache/`: 缓存集成测试

#### e2e/ - 端到端测试

完整业务流程测试

#### performance/ - 性能测试

性能基准测试

---

## 🎯 开发规范与约定

### 1. 依赖方向规则

```
core (零依赖)
  ↓
domain (只依赖 core)
  ↓
application (只依赖 domain + core)
  ↓
infrastructure (实现 application 端口)
  ↓
interfaces (使用 application + infrastructure)
```

**禁止**:
- ❌ domain 依赖 infrastructure
- ❌ application 依赖具体实现
- ❌ core 依赖任何外部模块

### 2. 新增限界上下文

在 `applications/<app>/modules/<bc>/` 下按四层组织：

```
modules/<bounded_context>/
├─ domain/              # 领域层（聚合、实体、值对象、事件）
├─ application/         # 应用层（用例、命令、查询）
├─ adapters/            # 适配器层（仓储实现、映射器）
└─ interfaces/          # 接口层（API 路由）
```

### 3. 事件驱动架构

**推荐流程**:
1. 领域层使用 `add_event()` 注册事件
2. UoW 自动收集事件
3. `commit()` 时写入 Outbox（同事务）
4. OutboxProjector 轮询发布到消息总线

**幂等性**: 使用 `event_id` + `Idempotency-Key`

### 4. 依赖注入

**原则**:
- ✅ Application 依赖抽象（IUnitOfWork、IRepository）
- ✅ Infrastructure 提供实现
- ✅ 在 `runtime/composition.py` 中装配
- ✅ 使用 FastAPI Depends 注入

**示例**:
```python
# Use Case
class CreateOrderUseCase:
    def __init__(self, uow: IUnitOfWork):  # 依赖抽象
        self.uow = uow

# Composition Root
async def get_unit_of_work() -> IUnitOfWork:
    return SQLAlchemyUnitOfWork(...)  # 注入实现

# API
@router.post("/orders")
async def create_order(
    use_case: CreateOrderUseCase = Depends(get_create_order_use_case),
):
    ...
```

### 5. 数据库使用

**配置**:
```bash
# .env
DB_URL="postgresql+asyncpg://localhost/mydb"
DB_POOL_SIZE=20
DB_ECHO=false
```

**初始化**:
```python
from bento.infrastructure.database import (
    DatabaseConfig,
    create_async_engine_from_config,
    init_database,
    drain_connections,
)

config = DatabaseConfig()
engine = create_async_engine_from_config(config)
await init_database(engine, Base)

# 应用关闭
await drain_connections(engine, timeout=30.0)
```

**使用重试**:
```python
from bento.infrastructure.database.resilience import retry_on_db_error

result = await retry_on_db_error(database_operation)
```

---

## 📊 关键指标

### 代码统计

| 模块 | 行数 | 说明 |
|------|------|------|
| 框架核心（src/bento） | ~8000 | 可发布包 |
| 数据库基础设施 | ~1620 | P0+P1 已完成 |
| 文档 | ~5000+ | 使用指南 + 设计文档 + ADR |
| 测试 | ~3000+ | 单元 + 集成 + E2E |
| 示例应用（ecommerce） | ~2000 | 教学示例 |

### 测试覆盖

| 类型 | 数量 | 状态 |
|------|------|------|
| 单元测试 | 50+ | ✅ 通过 |
| 集成测试 | 30+ | ✅ 通过 |
| E2E 测试 | 5+ | ✅ 通过 |
| 总覆盖率 | ~15% | ⏳ 持续提升 |

### 文档覆盖

| 类型 | 数量 | 说明 |
|------|------|------|
| ADR | 2 | 架构决策记录 |
| 设计文档 | 6 | 详细设计 |
| 使用指南 | 4 | 开发者指南 |
| API 文档 | 100% | 代码注释 + 示例 |

---

## 🚀 快速开始

### 安装

```bash
# 1. 克隆仓库
git clone <repo-url>
cd bento

# 2. 安装依赖（使用 uv）
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .[dev]

# 3. 启动本地环境
docker-compose -f deploy/docker/compose.dev.yaml up -d
```

### 运行示例

```bash
# 运行 ecommerce 应用
cd applications/ecommerce
uv run python -m runtime.bootstrap

# 访问 API
curl http://localhost:8000/api/orders
```

### 运行测试

```bash
# 单元测试
uv run pytest tests/unit -v

# 集成测试
uv run pytest tests/integration -v

# 所有测试
uv run pytest -v
```

---

## 📚 相关文档

- [架构决策记录](./adr/)
- [详细设计文档](../design/)
- [使用指南](../infrastructure/)
- [ecommerce 架构](../../applications/ecommerce/docs/ARCHITECTURE.md)

---

## 🔄 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2025-11-05 | 初始版本，反映当前 Bento 实现 |

---

**注**: 本文档为 Living Document，随着 Bento 框架的演进持续更新。
