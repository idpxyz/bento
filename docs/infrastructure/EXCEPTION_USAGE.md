## Exception System Usage Guide

**Version**: 1.0 MVP  
**Last Updated**: 2025-11-04

---

## 📖 Overview

Bento框架提供了一套**轻量但完整**的异常处理系统，符合 DDD 分层架构原则。

### 核心特性

- ✅ **DDD 分层异常** - 按架构层次分类（Domain/Application/Infrastructure/Interface）
- ✅ **结构化错误码** - 统一的错误码定义（ErrorCode）
- ✅ **统一 API 响应** - 自动转换为 JSON 格式
- ✅ **异常链支持** - 保留原始异常（`__cause__`）
- ✅ **FastAPI 集成** - 开箱即用的异常处理器
- ✅ **类型安全** - 100% 类型注解
- ✅ **轻量实现** - 仅 3 个核心文件，~200 行代码

---

## 📦 Components

### 文件结构

```
src/core/
├── errors.py           # 异常基类和分类异常
├── error_codes.py      # 错误码定义
└── error_handler.py    # FastAPI 集成
```

---

## 🧱 Exception Hierarchy

### 异常分类

```
BentoException (基类)
├── DomainException          # 领域层异常
├── ApplicationException     # 应用层异常
├── InfrastructureException  # 基础设施层异常
└── InterfaceException       # 接口层异常
```

### 分类说明

| 异常类型 | 使用场景 | 示例 |
|---------|---------|------|
| **DomainException** | 业务规则违反 | 订单已支付、库存不足 |
| **ApplicationException** | 用例执行失败 | 参数验证、资源冲突 |
| **InfrastructureException** | 技术故障 | 数据库连接、缓存错误 |
| **InterfaceException** | API/验证错误 | 请求格式错误 |

---

## 🎯 Quick Start

### 1. 定义错误码

**框架级错误码**（已提供）:
```python
from core.error_codes import CommonErrors, RepositoryErrors

# 使用框架提供的通用错误
raise ApplicationException(
    error_code=CommonErrors.INVALID_PARAMS,
    details={"field": "email"}
)
```

**业务级错误码**（在业务模块定义）:
```python
# modules/order/errors.py
from core.errors import ErrorCode

class OrderErrors:
    ORDER_NOT_FOUND = ErrorCode(
        code="ORDER_001",
        message="Order not found",
        http_status=404
    )
    
    ORDER_ALREADY_PAID = ErrorCode(
        code="ORDER_003",
        message="Order is already paid",
        http_status=409
    )
```

### 2. 在 Domain 层抛出异常

```python
from core.errors import DomainException
from modules.order.errors import OrderErrors  # 从业务模块导入

class Order(AggregateRoot):
    def pay(self) -> None:
        """Pay for the order."""
        if self.status == OrderStatus.PAID:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID,
                details={"order_id": self.id.value}
            )
        
        self.status = OrderStatus.PAID
        self.add_event(OrderPaidEvent(order_id=self.id))
```

### 3. 在 Application 层使用

```python
from core.errors import ApplicationException
from core.error_codes import CommonErrors

class CreateOrderUseCase:
    async def execute(self, command: CreateOrderCommand) -> Order:
        # Validate
        if not command.items:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "items", "reason": "cannot be empty"}
            )
        
        # Business logic...
```

### 4. 在 Infrastructure 层使用

```python
from core.errors import InfrastructureException
from core.error_codes import CommonErrors

class OrderRepository:
    async def find_by_id(self, order_id: OrderId) -> Order:
        try:
            result = await self.session.execute(...)
        except SQLAlchemyError as e:
            raise InfrastructureException(
                error_code=CommonErrors.DATABASE_ERROR,
                details={"operation": "find_order"},
                cause=e  # 保留原始异常
            )
```

### 5. FastAPI 集成

```python
from fastapi import FastAPI
from core.error_handler import register_exception_handlers

app = FastAPI()

# 注册异常处理器（一行代码）
register_exception_handlers(app)

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    # 异常会自动转换为 JSON 响应
    order = await order_service.get_order(order_id)
    return order
```

---

## 🏗️ Framework vs Business Errors

### **重要原则：框架和业务分离**

#### ✅ Framework-Level Errors（框架提供）

位置：`src/core/error_codes.py`

```python
from core.error_codes import CommonErrors, RepositoryErrors

# CommonErrors - 通用错误
CommonErrors.UNKNOWN_ERROR
CommonErrors.INVALID_PARAMS
CommonErrors.RESOURCE_NOT_FOUND
CommonErrors.UNAUTHORIZED
CommonErrors.DATABASE_ERROR

# RepositoryErrors - 仓储错误
RepositoryErrors.ENTITY_NOT_FOUND
RepositoryErrors.DUPLICATE_ENTITY
RepositoryErrors.OPTIMISTIC_LOCK_FAILED
```

**使用场景**：
- ✅ 参数验证
- ✅ 权限检查
- ✅ 基础设施错误（DB、Cache、Messaging）

#### ✅ Business-Level Errors（业务定义）

位置：`modules/{domain}/errors.py`

```python
# modules/order/errors.py
from core.errors import ErrorCode

class OrderErrors:
    ORDER_NOT_FOUND = ErrorCode("ORDER_001", "Order not found", 404)
    ORDER_ALREADY_PAID = ErrorCode("ORDER_003", "Order already paid", 409)

# modules/product/errors.py
class ProductErrors:
    PRODUCT_NOT_FOUND = ErrorCode("PRODUCT_001", "Product not found", 404)
    OUT_OF_STOCK = ErrorCode("PRODUCT_003", "Out of stock", 409)
```

**使用场景**：
- ✅ 领域业务规则违反
- ✅ 特定于业务上下文的错误

**示例参考**：查看 `examples/error_codes/` 目录

---

## 📋 API Response Format

当异常被抛出时，FastAPI 会自动返回如下格式的 JSON：

```json
{
  "code": "ORDER_001",
  "message": "Order not found",
  "category": "domain",
  "details": {
    "order_id": "123"
  }
}
```

**字段说明**：

- `code` - 错误码（唯一标识）
- `message` - 错误消息（人类可读）
- `category` - 异常分类（domain/application/infrastructure/interface）
- `details` - 额外的上下文信息（可选）

---

## 🔧 Advanced Usage

### 异常链（Exception Chaining）

保留原始异常，用于调试和日志：

```python
try:
    await database.execute(query)
except SQLAlchemyError as e:
    raise InfrastructureException(
        error_code=CommonErrors.DATABASE_ERROR,
        details={"query": str(query)},
        cause=e  # 原始异常会被记录到日志
    )
```

### 定义业务错误码

**步骤 1**: 在业务模块创建 errors.py

```python
# modules/order/errors.py
from core.errors import ErrorCode


class OrderErrors:
    """Order domain error codes."""
    
    ORDER_NOT_FOUND = ErrorCode(
        code="ORDER_001",
        message="Order not found",
        http_status=404
    )
    
    ORDER_ALREADY_PAID = ErrorCode(
        code="ORDER_003",
        message="Order is already paid",
        http_status=409
    )
```

**步骤 2**: 在业务代码中使用

```python
# modules/order/domain/order.py
from core.errors import DomainException
from modules.order.errors import OrderErrors


class Order(AggregateRoot):
    def pay(self) -> None:
        if self.status == OrderStatus.PAID:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID,
                details={"order_id": self.id.value}
            )
```

**参考示例**: `examples/error_codes/` 包含完整的业务错误码示例

### OpenAPI 文档集成

为 API 端点添加错误响应文档：

```python
from core.error_handler import get_error_responses_schema

@app.get(
    "/orders/{order_id}",
    responses=get_error_responses_schema()  # 自动生成错误响应文档
)
async def get_order(order_id: str):
    ...
```

---

## 📊 Error Code Naming Convention

### 推荐格式

```
{MODULE}_{NUMBER}

例如:
ORDER_001    # 订单模块第 1 个错误
USER_003     # 用户模块第 3 个错误
PRODUCT_010  # 商品模块第 10 个错误
```

### 通用错误码

使用 `COMMON_xxx` 前缀表示跨模块的通用错误：

```python
COMMON_000  # 未知错误
COMMON_001  # 参数错误
COMMON_002  # 资源不存在
```

---

## 🎯 Best Practices

### 1. 选择正确的异常类型

| 场景 | 使用 | 示例 |
|------|------|------|
| 业务规则违反 | `DomainException` | 订单已支付、库存不足 |
| 输入验证失败 | `ApplicationException` | 缺少字段、格式错误 |
| 数据库错误 | `InfrastructureException` | 查询失败、连接超时 |
| API 格式错误 | `InterfaceException` | JSON 解析失败 |

### 2. 提供有用的 details

```python
# ✅ Good - 提供上下文信息
raise DomainException(
    error_code=OrderErrors.ORDER_NOT_FOUND,
    details={
        "order_id": order_id,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
)

# ❌ Bad - 没有额外信息
raise DomainException(
    error_code=OrderErrors.ORDER_NOT_FOUND
)
```

### 3. 使用异常链保留上下文

```python
# ✅ Good - 保留原始异常
try:
    result = await db.execute(...)
except SQLAlchemyError as e:
    raise InfrastructureException(
        error_code=CommonErrors.DATABASE_ERROR,
        cause=e  # 原始异常会被日志记录
    )

# ❌ Bad - 丢失原始异常信息
except SQLAlchemyError:
    raise InfrastructureException(
        error_code=CommonErrors.DATABASE_ERROR
    )
```

### 4. HTTP 状态码映射

| HTTP Status | 使用场景 | 示例错误码 |
|-------------|---------|-----------|
| 400 Bad Request | 参数错误 | INVALID_PARAMS |
| 401 Unauthorized | 未认证 | UNAUTHORIZED |
| 403 Forbidden | 无权限 | FORBIDDEN |
| 404 Not Found | 资源不存在 | ORDER_NOT_FOUND |
| 409 Conflict | 资源冲突 | ORDER_ALREADY_PAID |
| 500 Internal Error | 服务器错误 | DATABASE_ERROR |

---

## 🔍 Logging

异常处理器会自动记录日志，级别根据异常类型：

```
INFO  - DomainException, InterfaceException (预期的业务错误)
WARN  - ApplicationException (应用层错误)
ERROR - InfrastructureException (基础设施故障)
```

日志格式：

```
2025-11-04 10:30:45 [ERROR] bento.exception: [INFRASTRUCTURE] COMMON_006: Database operation failed
  Category: infrastructure
  Code: COMMON_006
  Details: {'operation': 'find_order', 'order_id': '123'}
  Path: /orders/123
  Method: GET
  Caused by: OperationalError: (pymysql.err.OperationalError) ...
```

---

## 📝 Examples

### 完整示例

查看以下示例文件：

1. **基础用法**: `examples/exceptions/basic_example.py`
   - Domain/Application/Infrastructure 层异常示例
   - 异常链示例
   - 转换为字典示例

2. **FastAPI 集成**: `examples/exceptions/fastapi_example.py`
   - 完整的 REST API 示例
   - 自动异常处理
   - OpenAPI 文档集成

### 运行示例

```bash
# 基础示例
python examples/exceptions/basic_example.py

# FastAPI 示例
uvicorn examples.exceptions.fastapi_example:app --reload
# 访问 http://localhost:8000/docs
```

---

## 🆚 与 Old 系统对比

| 功能 | Old System | MVP System | 说明 |
|------|-----------|-----------|------|
| 分类异常 | ✅ | ✅ | 4 种分类异常 |
| ErrorCode | ✅ | ✅ | 结构化定义 |
| FastAPI 集成 | ✅ | ✅ | 自动处理 |
| 异常链 | ✅ | ✅ | __cause__ 支持 |
| Sentry 集成 | ✅ | ⏸️ 可选 | 实战后决定 |
| Trace ID | ✅ | ⏸️ 可选 | 实战后决定 |
| Rich 日志 | ✅ | ❌ | 使用标准 logging |
| 配置系统 | ✅ | ❌ | 简化 |
| 代码行数 | ~2000 | ~200 | 10x 简化 |

**MVP 系统**：覆盖 80% 的需求，仅 10% 的复杂度！

---

## 🚀 Next Steps

MVP 系统已经可以满足大部分需求。如果实战中需要更多功能：

### 可选扩展

1. **Trace ID 中间件** - 链路追踪
2. **Sentry 集成** - 错误监控
3. **国际化** - 多语言错误消息
4. **错误码文档生成** - 自动生成文档

### 何时扩展

- ✅ 先用 MVP 构建实战项目
- ✅ 发现真实需求时再扩展
- ✅ 避免过度设计

---

## 📚 Related Documentation

- `src/core/errors.py` - 异常系统源码
- `src/core/error_codes.py` - 错误码定义
- `src/core/error_handler.py` - FastAPI 集成
- `examples/exceptions/` - 完整示例

---

**创建时间**: 2025-11-04  
**状态**: ✅ MVP 完成并可生产使用

