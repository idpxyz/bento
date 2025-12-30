# 安全中间件集成指南

## 🎯 概述

Bento Framework 提供了一个科学的安全中间件集成方案，遵循"提供机制，不提供策略"的设计原则。

### 架构设计

```
应用层
  ↓
bento.runtime.integrations.setup_security()  ← 统一入口
  ↓
bento.security.add_security_middleware()     ← 框架机制
  ↓
IAuthenticator (应用实现)                    ← 应用策略
```

---

## 📦 集成方案

### 最佳方案：使用 `bento.runtime.integrations.setup_security()`

这是推荐的集成方式，提供了统一的集成入口。

#### 步骤 1: 实现认证器

```python
# applications/my-shop/shared/auth/jwt_authenticator.py
from bento.security import IAuthenticator, CurrentUser

class JWTAuthenticator:
    """JWT 认证器实现"""

    def __init__(self, jwks_url: str, audience: str):
        self.jwks_url = jwks_url
        self.audience = audience

    async def authenticate(self, request) -> CurrentUser | None:
        # 从 Authorization header 提取 token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]

        try:
            # 验证 token（实现省略）
            claims = await self._verify_token(token)

            return CurrentUser(
                id=claims["sub"],
                permissions=claims.get("permissions", []),
                roles=claims.get("roles", []),
                metadata=claims,
            )
        except Exception:
            return None

    async def _verify_token(self, token: str) -> dict:
        # 实现 JWT 验证逻辑
        pass
```

#### 步骤 2: 在应用启动时集成

```python
# applications/my-shop/runtime/bootstrap.py
from fastapi import FastAPI
from bento.runtime.integrations import setup_security, setup_bento_openapi
from bento.runtime.middleware import IdempotencyMiddleware
from my_shop.shared.auth import JWTAuthenticator

def create_app() -> FastAPI:
    app = FastAPI(title="My Shop API")

    # 1. 基础设施中间件
    app.add_middleware(IdempotencyMiddleware)

    # 2. 安全集成 ✨
    setup_security(
        app,
        authenticator=JWTAuthenticator(
            jwks_url="https://your-auth.com/.well-known/jwks.json",
            audience="my-shop-api",
        ),
        require_auth=True,
        exclude_paths=["/health", "/docs", "/openapi.json"],
    )

    # 3. OpenAPI 集成
    setup_bento_openapi(app)

    return app
```

#### 步骤 3: 在业务代码中使用

```python
# applications/my-shop/contexts/ordering/application/commands/create_order.py
from bento.application import CommandHandler
from bento.security import SecurityContext

class CreateOrderHandler(CommandHandler[CreateOrderCommand, str]):
    async def handle(self, command: CreateOrderCommand) -> str:
        # 获取当前用户
        user = SecurityContext.require_user()

        # 创建订单
        order = Order.create(
            customer_id=command.customer_id,
            items=command.items,
            created_by=user.id,
        )

        repo = self.uow.repository(Order)
        await repo.save(order)

        return str(order.id)
```

---

## 🔄 三种集成方式对比

### 方式 1: 使用 `bento.runtime.integrations.setup_security()` ✅ 推荐

**优点**:
- ✅ 统一的集成入口
- ✅ 职责清晰
- ✅ 易于扩展
- ✅ 符合架构原则

**使用**:
```python
from bento.runtime.integrations import setup_security

setup_security(app, authenticator=MyAuthenticator())
```

---

### 方式 2: 直接使用 `bento.security.add_security_middleware()` ⚠️ 可用但不推荐

**优点**:
- ✅ 直接控制
- ✅ 最小化

**缺点**:
- ❌ 没有统一入口
- ❌ 需要了解 bento.security 细节

**使用**:
```python
from bento.security import add_security_middleware

add_security_middleware(app, authenticator=MyAuthenticator())
```

---

### 方式 3: 自定义中间件 ❌ 不推荐

**缺点**:
- ❌ 重复代码
- ❌ 难以维护
- ❌ 违反 DRY 原则

**不要这样做**:
```python
# ❌ 不推荐
@app.middleware("http")
async def security_middleware(request, call_next):
    user = await authenticator.authenticate(request)
    SecurityContext.set_user(user)
    # ...
```

---

## 📋 完整示例

### 应用启动代码

```python
# applications/loms/runtime/bootstrap.py
from fastapi import FastAPI
from bento.runtime.integrations import setup_security, setup_bento_openapi
from bento.runtime.middleware import (
    IdempotencyMiddleware,
    RequestIDMiddleware,
    StructuredLoggingMiddleware,
)
from loms.shared.auth import StubAuthenticator

def create_app() -> FastAPI:
    """创建 LOMS FastAPI 应用"""
    app = FastAPI(
        title="LOMS API",
        description="Logistics Order Management System",
        version="1.0.0",
    )

    # 1. 基础设施中间件（按顺序添加）
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)

    # 2. 安全集成
    setup_security(
        app,
        authenticator=StubAuthenticator(),
        require_auth=False,  # P0: 开发阶段不强制
        exclude_paths=["/health", "/docs", "/openapi.json"],
    )

    # 3. OpenAPI 集成
    setup_bento_openapi(app)

    # 4. 注册路由
    from loms.api.v1 import orders, shipments
    app.include_router(orders.router, prefix="/api/v1/orders")
    app.include_router(shipments.router, prefix="/api/v1/shipments")

    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 业务代码示例

```python
# applications/loms/contexts/ordering/application/commands/create_order.py
from bento.application import CommandHandler
from bento.security import SecurityContext
from loms.contexts.ordering.domain.order import Order

class CreateOrderHandler(CommandHandler[CreateOrderCommand, str]):
    """创建订单"""

    async def validate(self, command: CreateOrderCommand) -> None:
        """验证命令"""
        if not command.customer_id:
            raise ValueError("customer_id required")
        if not command.items:
            raise ValueError("items required")

    async def handle(self, command: CreateOrderCommand) -> str:
        """处理命令"""
        # 获取当前用户
        user = SecurityContext.get_user()

        # 创建订单
        order = Order.create(
            customer_id=command.customer_id,
            items=command.items,
            created_by=user.id if user else "system",
        )

        # 保存到数据库
        repo = self.uow.repository(Order)
        await repo.save(order)

        return str(order.id)
```

### API 路由示例

```python
# applications/loms/api/v1/orders.py
from fastapi import APIRouter, Depends
from bento.security import get_current_user, CurrentUser
from loms.contexts.ordering.application.commands import CreateOrderCommand
from loms.contexts.ordering.application.commands.create_order import CreateOrderHandler

router = APIRouter()

@router.post("/", status_code=201)
async def create_order(
    command: CreateOrderCommand,
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建订单

    可选：如果需要在 API 层访问当前用户，可以使用 Depends(get_current_user)
    """
    handler = CreateOrderHandler(uow)
    order_id = await handler.execute(command)
    return {"id": order_id}
```

---

## 🔄 升级路径

### P0: Stub 实现（当前）

```python
from loms.shared.auth import StubAuthenticator

setup_security(app, authenticator=StubAuthenticator())
```

### P1: JWT 认证（生产）

```python
from loms.shared.auth import JWTAuthenticator

setup_security(
    app,
    authenticator=JWTAuthenticator(
        jwks_url="https://your-auth.com/.well-known/jwks.json",
        audience="loms-api",
    ),
    require_auth=True,
)
```

### P2: bento-security（企业级）

```python
from bento_security.providers import LogtoAuthProvider

setup_security(
    app,
    authenticator=LogtoAuthProvider(
        endpoint="https://your-app.logto.app",
        app_id="app-id",
        app_secret="app-secret",
    ),
    require_auth=True,
)
```

**关键点**: 业务代码完全不需要改变！

---

## 🎯 最佳实践

### 1. 使用 SecurityContext，不使用 request.state

```python
# ✅ 推荐
from bento.security import SecurityContext
user = SecurityContext.get_user()

# ❌ 不推荐
user = request.state.user
```

### 2. 在 Handler 中使用，不在 API 层

```python
# ✅ 推荐：在 Handler 中
class CreateOrderHandler(CommandHandler):
    async def handle(self, command):
        user = SecurityContext.require_user()
        # 业务逻辑

# ❌ 不推荐：在 API 层传递
@router.post("/")
async def create_order(request: Request, command: CreateOrderCommand):
    user_id = request.state.user_id  # 不要这样做
```

### 3. 使用 require_* 明确要求

```python
# ✅ 明确要求认证
user = SecurityContext.require_user()  # 未认证会抛异常

# ⚠️ 可选的认证
user = SecurityContext.get_user()  # 可能为 None
if user:
    # 已认证的逻辑
else:
    # 未认证的逻辑
```

### 4. 多租户应用使用租户解析

```python
from bento.security import ITenantResolver

class HeaderTenantResolver:
    async def resolve_tenant(self, request) -> str | None:
        return request.headers.get("X-Tenant-ID")

setup_security(
    app,
    authenticator=MyAuthenticator(),
    tenant_resolver=HeaderTenantResolver(),
)
```

---

## 📊 架构总结

### 职责分离

| 模块 | 职责 | 内容 |
|------|------|------|
| `bento.security` | 安全机制 | 接口、上下文、装饰器、工具 |
| `bento.runtime.middleware` | 基础设施中间件 | 请求去重、追踪、日志、速率限制 |
| `bento.runtime.integrations` | 集成助手 | 便捷的设置函数 |
| 应用层 | 认证策略 | 具体的认证实现 |

### 导入路径

```python
# 基础设施中间件
from bento.runtime.middleware import IdempotencyMiddleware

# 集成助手
from bento.runtime.integrations import setup_security, setup_bento_openapi

# 安全机制
from bento.security import SecurityContext, IAuthenticator
```

---

## ✅ 总结

**最佳的集成方案是：使用 `bento.runtime.integrations.setup_security()`**

这个方案：
- ✅ 提供统一的集成入口
- ✅ 保持职责清晰
- ✅ 遵循架构原则
- ✅ 易于应用层使用
- ✅ 易于未来扩展

**一行代码集成安全**:
```python
from bento.runtime.integrations import setup_security
setup_security(app, authenticator=MyAuthenticator())
```

