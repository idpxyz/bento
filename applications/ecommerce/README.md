# E-commerce Application

一个基于 Bento 框架构建的电商系统，展示了如何使用 DDD、CQRS、Event-Driven Architecture 等模式构建实际应用。

## 📋 **目录**

- [特性](#特性)
- [架构](#架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 文档](#api-文档)
- [示例](#示例)

## ✨ **特性**

### 业务功能
- ✅ 订单创建
- ✅ 订单支付
- ✅ 订单取消
- ✅ 订单查询

### 技术特性
- ✅ **DDD (Domain-Driven Design)**: 使用聚合、实体、值对象等战术模式
- ✅ **Hexagonal Architecture**: 清晰的分层架构
- ✅ **CQRS**: 命令和查询分离（含优化的查询服务）
- ✅ **Event-Driven**: 领域事件驱动（含事件处理器）
- ✅ **Transactional Outbox**: 保证事件可靠发布
- ✅ **Input Validation**: Guard Clauses和输入验证
- ✅ **Exception Handling**: 统一的异常处理和错误码
- ✅ **RESTful API**: 基于 FastAPI 的高性能 API
- ✅ **Comprehensive Tests**: 112个测试覆盖核心功能

## 🏗️ **架构**

### Hexagonal Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Interfaces Layer                        │
│                 (FastAPI Routes, API)                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Application Layer                         │
│           (Use Cases, Commands, Queries)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                     Domain Layer                            │
│       (Aggregates, Entities, Value Objects, Events)         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Adapters Layer                           │
│              (Repositories, Mappers)                        │
└─────────────────────────────────────────────────────────────┘
```

### Order 聚合生命周期

```
PENDING → PAID → SHIPPED → DELIVERED
   ↓                          ↓
CANCELLED                 REFUNDED
```

## 📁 **项目结构**

```
applications/ecommerce/
├── modules/                      # 业务模块 (Bounded Contexts)
│   └── order/                   # 订单模块
│       ├── errors.py            # 错误码定义
│       ├── domain/              # 领域层
│       │   ├── order.py         # Order 聚合根
│       │   ├── order_status.py  # OrderStatus 值对象
│       │   └── events.py        # 领域事件
│       ├── application/         # 应用层
│       │   ├── commands/        # 命令 (写操作)
│       │   │   ├── create_order.py
│       │   │   ├── pay_order.py
│       │   │   └── cancel_order.py
│       │   └── queries/         # 查询 (读操作)
│       │       └── get_order.py
│       ├── adapters/            # 适配器层
│       │   └── order_repository.py
│       └── interfaces/          # 接口层
│           └── order_api.py     # FastAPI 路由
├── runtime/                     # 运行时配置
│   ├── composition.py           # 依赖注入配置
│   └── bootstrap.py             # 应用启动
├── main.py                      # 应用入口
└── README.md                    # 本文档
```

## 🚀 **快速开始**

### 方式一：使用启动脚本（推荐）

```bash
# 从项目根目录
cd /workspace/bento
./start-ecommerce.sh
```

### 方式二：使用 uv run（最简单）

```bash
# 从项目根目录
cd /workspace/bento
uv run uvicorn applications.ecommerce.main:app --reload
```

### 方式三：手动启动

```bash
# 1. 确保已安装依赖
uv sync

# 2. 从项目根目录启动
cd /workspace/bento
uvicorn applications.ecommerce.main:app --reload --port 8000
```

### 访问应用

服务启动后，打开浏览器访问：
- 🏠 **健康检查**: http://localhost:8000/health
- 📚 **API 文档** (Swagger): http://localhost:8000/docs
- 📖 **API 文档** (ReDoc): http://localhost:8000/redoc
- 🔍 **OpenAPI Schema**: http://localhost:8000/openapi.json

### 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 创建订单
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-123",
    "items": [
      {
        "product_id": "product-1",
        "product_name": "iPhone 15 Pro",
        "quantity": 2,
        "unit_price": 999.99
      }
    ]
  }'

# 查询订单
curl http://localhost:8000/api/orders/{order_id}

# 支付订单
curl -X POST http://localhost:8000/api/orders/{order_id}/pay \
  -H "Content-Type: application/json" \
  -d '{}'

# 取消订单
curl -X POST http://localhost:8000/api/orders/{order_id}/cancel \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer request"}'
```

## 📖 **API 文档**

### 创建订单

**POST** `/api/orders`

```json
{
  "customer_id": "customer-123",
  "items": [
    {
      "product_id": "product-1",
      "product_name": "iPhone 15 Pro",
      "quantity": 2,
      "unit_price": 999.99
    }
  ]
}
```

**响应:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "customer-123",
  "status": "pending",
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "product_id": "product-1",
      "product_name": "iPhone 15 Pro",
      "quantity": 2,
      "unit_price": 999.99,
      "subtotal": 1999.98
    }
  ],
  "items_count": 1,
  "total_amount": 1999.98,
  "created_at": "2025-11-04T10:00:00",
  "paid_at": null,
  "cancelled_at": null
}
```

### 查询订单

**GET** `/api/orders/{order_id}`

**响应:** 同创建订单响应

### 支付订单

**POST** `/api/orders/{order_id}/pay`

**请求体:** `{}`

**响应:** 订单数据 (status 变为 "paid")

### 取消订单

**POST** `/api/orders/{order_id}/cancel`

```json
{
  "reason": "Customer request"
}
```

**响应:** 订单数据 (status 变为 "cancelled")

### 错误响应

所有错误都遵循统一格式：

```json
{
  "code": "ORDER_001",
  "message": "Order not found",
  "category": "application",
  "details": {
    "order_id": "invalid-id"
  }
}
```

## 💡 **示例**

### Python 客户端示例

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 1. 创建订单
        response = await client.post(
            "/api/orders",
            json={
                "customer_id": "customer-123",
                "items": [
                    {
                        "product_id": "product-1",
                        "product_name": "iPhone 15 Pro",
                        "quantity": 2,
                        "unit_price": 999.99
                    }
                ]
            }
        )
        order = response.json()
        order_id = order["id"]
        print(f"✅ Order created: {order_id}")

        # 2. 查询订单
        response = await client.get(f"/api/orders/{order_id}")
        order = response.json()
        print(f"📦 Order status: {order['status']}")
        print(f"💰 Total amount: ${order['total_amount']}")

        # 3. 支付订单
        response = await client.post(f"/api/orders/{order_id}/pay", json={})
        order = response.json()
        print(f"✅ Order paid: {order['status']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 集成测试示例

```python
import pytest
from httpx import AsyncClient
from applications.ecommerce.main import app

@pytest.mark.asyncio
async def test_order_lifecycle():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create order
        response = await client.post(
            "/api/orders",
            json={
                "customer_id": "customer-123",
                "items": [
                    {
                        "product_id": "product-1",
                        "product_name": "Test Product",
                        "quantity": 1,
                        "unit_price": 99.99
                    }
                ]
            }
        )
        assert response.status_code == 200
        order = response.json()
        order_id = order["id"]

        # Pay order
        response = await client.post(f"/api/orders/{order_id}/pay", json={})
        assert response.status_code == 200
        assert response.json()["status"] == "paid"
```

## 🎯 **核心概念**

### 1. 聚合根 (Aggregate Root)

`Order` 是聚合根，管理 `OrderItem` 实体：

```python
# 创建订单
order = Order(order_id=ID.generate(), customer_id=customer_id)

# 添加商品
order.add_item(
    product_id=product_id,
    product_name="iPhone 15 Pro",
    quantity=2,
    unit_price=999.99
)

# 支付订单（领域逻辑）
order.pay()  # 会发布 OrderPaid 事件
```

### 2. 领域事件

领域事件在聚合根状态变化时自动发布：

```python
class Order(AggregateRoot):
    def pay(self):
        # 业务规则检查
        if self.status == OrderStatus.PAID:
            raise DomainException(OrderErrors.ORDER_ALREADY_PAID)

        # 状态变更
        self.status = OrderStatus.PAID
        self.paid_at = datetime.now()

        # 发布事件
        self.add_event(OrderPaid(
            order_id=self.id,
            customer_id=self.customer_id,
            total_amount=self.total_amount,
        ))
```

### 3. Use Case 模式

每个业务操作都是一个独立的 Use Case：

```python
class CreateOrderUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    async def execute(self, command: CreateOrderCommand):
        # 1. 创建聚合
        order = Order(...)

        # 2. 持久化
        async with self.uow:
            await self.uow.repository(Order).add(order)
            await self.uow.commit()  # 自动发布事件

        return order.to_dict()
```

### 4. Transactional Outbox

事件通过 Outbox 模式可靠发布：

1. 业务数据和事件在同一事务中保存
2. 后台任务轮询 Outbox 表
3. 发布事件到消息总线
4. 标记为已发布

## 🔧 **配置**

### 数据库配置

编辑 `runtime/composition.py`:

```python
# SQLite (开发环境，默认)
DATABASE_URL = "sqlite+aiosqlite:///./ecommerce.db"

# PostgreSQL (生产环境)
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/ecommerce"
```

### 日志配置

编辑 `runtime/bootstrap.py`:

```python
logging.basicConfig(
    level=logging.INFO,  # DEBUG, INFO, WARNING, ERROR
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
```

### 环境要求

- **Python**: 3.12+ (项目使用 `requires-python = ">=3.12,<3.13"`)
- **包管理器**: uv (推荐) 或 pip
- **数据库**: SQLite (开发) / PostgreSQL (生产)

### 安装 uv

```bash
# Ubuntu/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装后重新加载 shell
source ~/.bashrc  # 或 ~/.zshrc
```

## 🛠️ **开发工具**

### 代码格式化

```bash
# 从项目根目录
cd /workspace/bento
make fmt
```

### 代码检查

```bash
make lint
```

### 启动脚本

项目根目录提供了 `start-ecommerce.sh` 启动脚本：

```bash
#!/bin/bash
cd "$(dirname "$0")"
uv run uvicorn applications.ecommerce.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000
```

## 📚 **参考文档**

### 本项目文档
- **[最佳实践展示](./FINAL_SUMMARY.md)** - 完整的架构和实现总结 ⭐
- **[改进总结](./IMPROVEMENTS_SUMMARY.md)** - 新增功能详解
- **[架构文档](./docs/ARCHITECTURE.md)** - 六边形架构说明

### Bento框架文档
- [Bento Framework Documentation](../../docs/README.md)
- [Exception System Guide](../../docs/infrastructure/EXCEPTION_USAGE.md)
- [Database Infrastructure](../../docs/infrastructure/DATABASE_USAGE.md)
- [Persistence Guide](../../docs/infrastructure/PROJECTION_USAGE.md)
- [Domain Modeling Guide](../../docs/conventions/domain-modeling-guide.md)

## 🧪 **测试**

### 运行所有测试

```bash
# 从项目根目录
cd /workspace/bento
uv run pytest applications/ecommerce/tests/
```

### 运行特定测试

```bash
# 领域逻辑测试
uv run pytest applications/ecommerce/tests/test_order_domain.py

# 特定测试函数
uv run pytest applications/ecommerce/tests/test_order_domain.py::test_create_order

# 详细输出
uv run pytest applications/ecommerce/tests/ -v

# 带覆盖率
uv run pytest applications/ecommerce/tests/ --cov=applications.ecommerce
```

### 测试标记

```bash
# 只运行单元测试
uv run pytest -m unit

# 只运行集成测试
uv run pytest -m integration
```

### 测试结构

```
applications/ecommerce/tests/
├── __init__.py
├── conftest.py              # Pytest 配置和 fixtures
├── test_order_api.py        # API 集成测试
└── test_order_domain.py     # 领域逻辑单元测试
```

### 测试覆盖

- ✅ **112个测试全部通过**
- ✅ 10个领域逻辑单元测试
- ✅ 36个验证器测试
- ✅ 9个事件处理器测试
- ✅ 57个数据库基础设施测试
- ✅ 订单创建、支付、取消完整流程
- ✅ 业务规则验证（空订单、重复支付等）
- ✅ 输入验证（Guard Clauses、边界测试）
- ✅ 事件驱动架构测试

**查看详细总结**: [FINAL_SUMMARY.md](./FINAL_SUMMARY.md)

## 🤝 **贡献**

欢迎贡献！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 **许可证**

本项目采用 MIT 许可证 - 详见 [LICENSE](../../LICENSE) 文件

