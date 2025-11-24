# {{project_name}}

{{description}}

> 由 [Bento Framework](https://github.com/bentoml/bento) 生成 - Domain-Driven Design + Modular Monolith 架构

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 复制环境配置
cp .env.example .env

# 安装依赖（包含开发工具）
uv pip install -e ".[dev]"
```

### 2. 生成第一个模块

```bash
# 在指定上下文中生成模块
bento gen module Product \
  --context catalog \
  --fields "name:str,price:float,stock:int"
```

### 3. 运行测试

```bash
# 运行所有测试
uv run pytest -v

# 带覆盖率
uv run pytest --cov
```

### 4. 启动应用

```bash
# 开发模式（自动重载）
uvicorn main:app --reload

# 访问 API 文档
open http://localhost:8000/docs
```

---

## 📁 项目结构（Modular Monolith）

```
{{project_slug}}/
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
