# 🚀 my-shop 快速开始

这是一个完整的 DDD 示例项目，展示如何使用 Bento 框架构建电商应用。

## 📋 前置条件

- Python 3.12+
- uv 包管理器（推荐）或 pip

## 🔧 安装依赖

```bash
# 使用 uv (推荐)
cd applications/my-shop
uv pip install -e ../../  # 安装 Bento 框架

# 或使用 pip
pip install -e ../../
```

## 🗄️ 初始化数据库

```bash
# 创建数据库表
python scripts/init_db.py

# 填充示例数据（可选）
python scripts/seed_data.py
```

## 🏃 启动服务

```bash
# 使用 Makefile (推荐)
make dev

# 或直接使用 uvicorn
uvicorn main:app --reload --port 8000
```

## 📖 访问 API 文档

打开浏览器访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🧪 测试 API

### 使用 curl

```bash
# 健康检查
curl http://localhost:8000/health

# API ping
curl http://localhost:8000/api/v1/ping

# 创建产品
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iPhone 15",
    "description": "最新款 iPhone",
    "price": 5999.00,
    "stock": 100
  }'

# 获取产品列表
curl http://localhost:8000/api/v1/products

# 获取单个产品
curl http://localhost:8000/api/v1/products/{product_id}

# 更新产品
curl -X PUT http://localhost:8000/api/v1/products/{product_id} \
  -H "Content-Type: application/json" \
  -d '{
    "price": 4999.00,
    "stock": 150
  }'

# 删除产品
curl -X DELETE http://localhost:8000/api/v1/products/{product_id}

# 创建订单
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "user-123",
    "items": [
      {"product_id": "prod-1", "quantity": 2, "unit_price": 5999.00},
      {"product_id": "prod-2", "quantity": 1, "unit_price": 1899.00}
    ]
  }'

# 获取订单列表
curl http://localhost:8000/api/v1/orders

# 支付订单
curl -X POST http://localhost:8000/api/v1/orders/{order_id}/pay

# 发货订单
curl -X POST http://localhost:8000/api/v1/orders/{order_id}/ship

# 取消订单
curl -X POST http://localhost:8000/api/v1/orders/{order_id}/cancel

# 创建用户
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "email": "zhangsan@example.com"
  }'

# 获取用户列表
curl http://localhost:8000/api/v1/users

# 获取单个用户
curl http://localhost:8000/api/v1/users/{user_id}

# 通过邮箱查找用户
curl http://localhost:8000/api/v1/users/by-email/zhangsan@example.com

# 更新用户
curl -X PUT http://localhost:8000/api/v1/users/{user_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三丰"
  }'

# 删除用户
curl -X DELETE http://localhost:8000/api/v1/users/{user_id}
```

### 使用 Python requests

```python
import requests

base_url = "http://localhost:8000/api/v1"

# 创建产品
response = requests.post(
    f"{base_url}/products",
    json={
        "name": "MacBook Pro",
        "description": "强大的专业笔记本",
        "price": 12999.00,
        "stock": 50
    }
)
product = response.json()
print(f"Created: {product}")

# 获取列表
response = requests.get(f"{base_url}/products")
products = response.json()
print(f"Total products: {products['total']}")
```

## 🏗️ 项目结构

```
my-shop/
├── api/                    # API 层
│   ├── deps.py            # 依赖注入 (使用 Bento UnitOfWork)
│   ├── router.py          # 主路由器
│   ├── products.py        # 产品 API endpoints
│   └── schemas/           # Pydantic DTOs
│       └── product.py
├── contexts/              # DDD 限界上下文
│   ├── catalog/          # 产品目录上下文
│   │   ├── domain/       # 领域层
│   │   ├── application/  # 应用层 (Use Cases)
│   │   └── infrastructure/ # 基础设施层
│   ├── ordering/         # 订单上下文
│   └── identity/         # 用户身份上下文
├── scripts/              # 脚本
│   └── init_db.py       # 数据库初始化
├── tests/                # 测试
├── config.py             # 配置 (集成 Bento DatabaseConfig)
├── main.py               # FastAPI 应用入口
└── Makefile              # 开发任务

```

## 🔑 关键特性

### ✅ 已实现

- **DDD 架构**: 3 个限界上下文 (Catalog, Ordering, Identity)
- **Bento 集成**: 使用框架的 UnitOfWork、Database、Outbox
- **RESTful API**: 完整的产品 CRUD endpoints
- **数据库**: SQLAlchemy + SQLite (可切换其他数据库)
- **API 文档**: 自动生成的 Swagger UI
- **类型安全**: Pydantic schemas 验证

### 🚧 待实现

- **订单 API**: 创建订单、支付、发货流程
- **用户 API**: 用户注册、认证
- **事件发布**: 领域事件通过 Outbox 发布
- **数据迁移**: Alembic 迁移脚本
- **测试**: E2E 测试示例
- **认证授权**: JWT tokens
- **缓存**: Redis 集成
- **搜索**: OpenSearch 集成

## 📚 学习资源

- **框架文档**: `/workspace/bento/docs/`
- **CLI 使用**: `/workspace/bento/src/bento/toolkit/CLI_USAGE_GUIDE.md`
- **DDD 指南**: `ORDER_AGGREGATE_GUIDE.md`
- **项目概览**: `PROJECT_OVERVIEW.md`

## 🐛 常见问题

### 数据库文件位置

SQLite 数据库文件在: `./my_shop.db`

### 重置数据库

```bash
rm my_shop.db
python scripts/init_db.py
```

### 端口被占用

修改 `.env` 文件或直接指定端口：

```bash
uvicorn main:app --port 8001
```

## 🎯 下一步

1. **添加订单 API** - 参照 `api/products.py` 创建订单 endpoints
2. **实现业务逻辑** - 在 domain 层添加聚合根方法
3. **发布领域事件** - 使用 Bento 的 Outbox 模式
4. **添加测试** - 参考 `tests/` 目录示例
5. **部署** - 使用 Docker 或 K8s (见 `/deploy/` 目录)

---

**Happy Coding! 🎉**
