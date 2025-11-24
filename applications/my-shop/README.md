# 🛍️ my-shop

**完整 DDD 电商示例项目** - Bento Framework 参考实现

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Framework](https://img.shields.io/badge/Framework-Bento-green.svg)](https://github.com/idpxyz/bento)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-teal.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 基于 Bento Framework 构建的 DDD + Hexagonal / Modular Monolith 示例应用

---

## 🚀 快速开始（在 Bento 仓库中运行 my-shop）

### 1. 在仓库根目录安装依赖

```bash
cd /workspace/bento
uv venv && . .venv/bin/activate
uv pip install -e .[dev]
```

### 2. 准备 my-shop 环境配置

仓库中已经提供了一个默认的 `applications/my-shop/.env`，可以根据需要修改：

- 应用配置：`APP_NAME`, `APP_ENV`, `DEBUG`
- 数据库：`DATABASE_URL`（默认使用 SQLite，本地即可运行）
- API：`API_HOST`, `API_PORT`, `API_RELOAD`
- 安全：`SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- CORS：`CORS_ORIGINS`
- 日志：`LOG_LEVEL`
- 缓存（可选覆盖）：`CACHE_BACKEND`, `CACHE_PREFIX`, `CACHE_TTL`, `CACHE_MAX_SIZE`, `CACHE_SERIALIZER`, `CACHE_ENABLE_STATS`, `CACHE_ENABLE_BREAKDOWN_PROTECTION`

另外，`applications/my-shop/config/.env.example` 提供了邮件、支付宝、短信、Redis 等适配器的扩展配置模板（可选）。

### 3. 启动 my-shop API

```bash
cd applications/my-shop

# 使用 uv 运行 FastAPI 应用（开发模式自动重载）
uv run uvicorn main:app --reload

# 访问 API 文档
# http://localhost:8000/docs
```

### 4. 运行测试

```bash
cd applications/my-shop

# 运行 my-shop 相关测试
uv run pytest -v

# 带覆盖率
uv run pytest --cov
```

---

> 下文为最初模板生成的通用说明，仍然对理解项目结构和开发流程有参考价值。

---

## 🧱 关键架构点（基于 Bento Framework）

### 1. 分层与依赖方向

- 每个上下文内部遵循 DDD 分层：`domain` → `application` → `infrastructure`。
- 依赖方向：
  - `infrastructure` 依赖 `application` + `domain`
  - `application` 依赖 `domain`
  - `domain` 不依赖任何技术栈（仅依赖端口/抽象）。

### 2. UnitOfWork（工作单元）

- Application 层用例通过 `UnitOfWork` 获取仓储并控制事务：
  - `uow.repository(AggregateRootType)` 返回对应聚合根的仓储（`IRepository[AR, ID]`）。
  - my-shop 中 `shared/infrastructure/dependencies.py` 负责注入 `SQLAlchemyUnitOfWork`。
- 所有写操作（下单、修改商品等）都在 UoW 控制下完成，保证**一次用例 = 一次事务**。

### 3. RepositoryAdapter（仓储适配器）

- 领域层只依赖 `IRepository[AR, ID]` 端口，不依赖具体 ORM。
- 基础设施层通过 `RepositoryAdapter[AR, PO, ID]` 将：
  - 聚合根（AR） ↔ 持久化对象（PO）
  - 应用层查询条件（Specification） ↔ SQLAlchemy 查询
- 具体仓储实现（例如 `CategoryRepository`, `OrderRepository`）继承 `RepositoryAdapter`，实现领域特定扩展方法。

### 4. Cache & Warmup（缓存与预热）

- Cache 使用统一的配置与实现：
  - `CacheConfig`（含 `from_env`、`get_prefixed_key`）
  - `MemoryCache` / `RedisCache`（通过 `CacheFactory` 创建）
  - `CacheSerializer` + `AggregateRoot.to_cache_dict()` 负责 AR → JSON 友好结构的转换。
- 应用层的 Warmup 策略（如 catalog 中的 Product/Category 预热）：
  - 直接返回聚合根或聚合根列表；
  - Framework 自动调用 `to_cache_dict()` 进行序列化，应用层无需手写重复转换。

### 5. Outbox 模式（事务性事件）

- my-shop 通过 Bento 的 Outbox 子系统，将领域事件以事务方式写入 Outbox 表：
  - 领域层产生 `DomainEvent`；
  - UoW 提交事务时，Outbox Listener 负责把事件持久化到 Outbox 表；
  - 独立的 Projector 从 Outbox 读取事件，推送到下游（消息总线 / 其他上下文）。
- 这保证了：
  - **数据写入与事件发布在同一事务中**；
  - 可以安全地做异步集成，而不会出现“数据成功写库但事件丢失”的情况。

这一节是 my-shop 作为 Bento 参考实现的核心精华：在阅读具体代码（UseCase、Repository、Warmup 等）时，可以对照这些关键点理解它们在整体架构中的角色。

---

## 📁 项目结构（Modular Monolith）

```
my_shop/
├── contexts/                  # 边界上下文（Bounded Contexts）
│   ├── <context-name>/       # 单个上下文
│   │   ├── domain/           # 领域层
│   │   │   ├── <aggregate>.py
│   │   │   └── events/
│   │   ├── application/      # 应用层
│   │   │   └── usecases/
│   │   └── infrastructure/   # 基础设施层
│   │       ├── models/       # 持久化对象 (PO)
│   │       ├── mappers/      # 映射器
│   │       └── repositories/ # 仓储
│   └── shared/               # 共享内核
│       ├── domain/           # 共享值对象
│       └── events/           # 集成事件
│
├── api/                       # API 层
│   ├── deps.py               # 依赖注入
│   └── router.py             # 路由聚合
│
├── tests/                     # 测试（按上下文组织）
│   ├── <context>/
│   │   ├── unit/
│   │   │   ├── domain/
│   │   │   └── application/
│   │   └── integration/
│   └── conftest.py
│
├── main.py                    # FastAPI 应用入口
├── config.py                  # 配置管理
├── pyproject.toml            # 项目配置
└── .env                       # 环境变量
```

---

## 🛠️ 开发指南

### 生成新模块

```bash
# 在现有上下文中生成模块
bento gen module Category \
  --context catalog \
  --fields "name:str,parent_id:str"

# 在新上下文中生成模块
bento gen module Order \
  --context ordering \
  --fields "customer_id:str,total:float,status:str"
```

每个模块生成 **9 个文件**：
- 1 个聚合根 + 1 个领域事件
- 1 个 PO + 1 个映射器 + 1 个仓储
- 1 个用例
- 3 个测试文件

### 运行测试

```bash
# 所有测试
uv run pytest -v

# 特定上下文
uv run pytest tests/<context>/ -v

# 单元测试
uv run pytest tests/<context>/unit/ -v

# 集成测试
uv run pytest tests/<context>/integration/ -v

# 覆盖率报告
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

### 代码质量

```bash
# 格式化代码
uv run ruff format .

# 代码检查
uv run ruff check .

# 类型检查
uv run mypy contexts/
```

### 数据库迁移

```bash
# 生成迁移
alembic revision --autogenerate -m "Add Product table"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

---

## 🎯 开发流程

### 1. 实现领域逻辑

编辑 `contexts/<context>/domain/<aggregate>.py`：

```python
class Product(AggregateRoot):
    def decrease_stock(self, quantity: int):
        """减少库存"""
        if self.stock < quantity:
            raise ValueError("库存不足")

        self.stock -= quantity
        self.add_event(ProductStockDecreasedEvent(
            product_id=self.id,
            quantity=quantity
        ))
```

### 2. 实现用例

编辑 `contexts/<context>/application/usecases/<usecase>.py`

### 3. 编写测试

完善生成的测试骨架

### 4. 实现仓储

根据生成的 Protocol 接口实现具体仓储

### 5. 添加 API 路由

在 `api/router.py` 中添加路由

---

## 🏗️ 架构说明

### Modular Monolith

本项目采用 **Modular Monolith** 架构：

- **按业务能力组织**：每个 `context` 代表一个边界上下文
- **独立演化**：不同上下文可独立开发和测试
- **清晰边界**：上下文间通过接口和事件通信
- **易于拆分**：未来可轻松拆分为微服务

### DDD 分层

每个上下文内部遵循 DDD 分层：

```
contexts/<context>/
├── domain/         # 核心业务逻辑（无依赖）
├── application/    # 用例编排（依赖 domain）
└── infrastructure/ # 技术实现（依赖 domain + application）
```

依赖方向：`infrastructure → application → domain`

---

## 📚 更多资源

### Bento 文档

- [CLI 使用指南](https://github.com/bentoml/bento)
- [测试指南](https://github.com/bentoml/bento)
- [架构说明](https://github.com/bentoml/bento)

### 外部资源

- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Modular Monolith](https://www.kamilgrzybek.com/design/modular-monolith-primer/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)

---

## 📝 许可证

MIT License
