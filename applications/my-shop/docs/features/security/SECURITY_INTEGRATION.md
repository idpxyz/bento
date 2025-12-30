# My-Shop 安全集成指南

## 📋 概述

本文档说明如何在 my-shop 应用中集成 Bento Framework 的安全中间件。

## 🎯 集成方案

### 架构设计

```
my-shop Application
  ↓
bento.runtime.integrations.setup_security()  ← 统一入口
  ↓
bento.security.add_security_middleware()     ← 框架机制
  ↓
StubAuthenticator (应用实现)                 ← 应用策略
```

## 📁 文件结构

```
applications/my-shop/
├── shared/
│   └── auth/
│       ├── __init__.py
│       └── stub_authenticator.py          ✨ 认证器实现
│
└── runtime/
    └── bootstrap_v2.py                     ✨ 应用启动配置
```

## 🔧 实现步骤

### 步骤 1: 创建认证器

**文件**: `shared/auth/stub_authenticator.py`

```python
from bento.security import CurrentUser

class StubAuthenticator:
    """Stub authenticator for development/testing."""

    async def authenticate(self, request) -> CurrentUser | None:
        """Accept all requests as authenticated (P0 stub)."""
        return CurrentUser(
            id="demo-user",
            permissions=["*"],  # Full permissions
            roles=["admin"],
            metadata={"stub": True, "environment": "development"},
        )
```

### 步骤 2: 在应用启动时集成

**文件**: `runtime/bootstrap_v2.py`

```python
from bento.runtime.integrations import setup_security, setup_bento_openapi
from shared.auth import StubAuthenticator

def create_app() -> FastAPI:
    app = runtime.create_fastapi_app(...)

    # ========================================
    # Middleware Stack (Order Matters!)
    # ========================================

    # 1. Security - Authentication and Authorization ✨
    setup_security(
        app,
        authenticator=StubAuthenticator(),
        require_auth=False,  # P0: Development mode
        exclude_paths=["/health", "/ping", "/docs", "/openapi.json", "/redoc"],
    )

    # 2. Request ID
    app.add_middleware(RequestIDMiddleware, ...)

    # 3. Structured Logging
    app.add_middleware(StructuredLoggingMiddleware, ...)

    # 4. Rate Limiting
    app.add_middleware(RateLimitingMiddleware, ...)

    # 5. Idempotency
    app.add_middleware(IdempotencyMiddleware, ...)

    # 6. CORS
    app.add_middleware(CORSMiddleware, ...)

    return app
```

### 步骤 3: 在业务代码中使用

**示例**: 在 Command Handler 中使用

```python
# contexts/ordering/application/commands/create_order.py
from bento.application import CommandHandler
from bento.security import SecurityContext

class CreateOrderHandler(CommandHandler[CreateOrderCommand, str]):
    async def handle(self, command: CreateOrderCommand) -> str:
        # 获取当前用户
        user = SecurityContext.get_user()

        # 创建订单
        order = Order.create(
            customer_id=command.customer_id,
            items=command.items,
            created_by=user.id if user else "system",
        )

        repo = self.uow.repository(Order)
        await repo.save(order)

        return str(order.id)
```

## 🚀 中间件栈顺序

```
Request
  ↓
1. Security (Authentication/Authorization)     ← 最先执行
  ↓
2. Request ID (Tracing)
  ↓
3. Structured Logging
  ↓
4. Tenant Context (Optional)
  ↓
5. Rate Limiting
  ↓
6. Idempotency
  ↓
7. CORS
  ↓
Business Logic
```

**为什么 Security 在最前面？**
- 尽早识别用户身份
- 后续中间件可以使用 SecurityContext
- 日志中可以包含用户信息

## 🔄 升级路径

### P0: Stub 实现（当前）

```python
from shared.auth import StubAuthenticator

setup_security(
    app,
    authenticator=StubAuthenticator(),
    require_auth=False,  # 开发模式
)
```

**特点**:
- ✅ 快速开发
- ✅ 不需要外部认证服务
- ⚠️ 不能用于生产环境

### P1: JWT 认证（生产）

```python
# shared/auth/jwt_authenticator.py
class JWTAuthenticator:
    def __init__(self, jwks_url: str, audience: str):
        self.jwks_url = jwks_url
        self.audience = audience

    async def authenticate(self, request) -> CurrentUser | None:
        # 1. 提取 token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        # 2. 验证 token
        token = auth_header[7:]  # Remove "Bearer "
        claims = await self._verify_token(token)

        # 3. 返回用户
        return CurrentUser(
            id=claims["sub"],
            permissions=claims.get("permissions", []),
            roles=claims.get("roles", []),
            metadata=claims,
        )

# runtime/bootstrap_v2.py
from shared.auth import JWTAuthenticator

setup_security(
    app,
    authenticator=JWTAuthenticator(
        jwks_url="https://your-auth.com/.well-known/jwks.json",
        audience="my-shop-api",
    ),
    require_auth=True,  # 生产模式：强制认证
)
```

### P2: bento-security（企业级）

```bash
pip install bento-security[fastapi]
```

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

## 💡 最佳实践

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
async def create_order(request: Request):
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

### 4. 排除健康检查和文档路径

```python
setup_security(
    app,
    authenticator=MyAuthenticator(),
    exclude_paths=[
        "/health",
        "/ping",
        "/docs",
        "/openapi.json",
        "/redoc",
    ],
)
```

## 🧪 测试

### 单元测试

```python
from bento.security import SecurityContext, CurrentUser

async def test_create_order():
    # 设置测试用户
    test_user = CurrentUser(
        id="test-user",
        permissions=["orders:create"],
    )
    SecurityContext.set_user(test_user)

    # 执行测试
    handler = CreateOrderHandler(mock_uow)
    result = await handler.execute(command)

    assert result is not None

    # 清理
    SecurityContext.clear()
```

### 集成测试

```python
from fastapi.testclient import TestClient

def test_create_order_api():
    client = TestClient(app)

    # 不需要 token（P0 stub 模式）
    response = client.post(
        "/api/v1/orders",
        json={"customer_id": "123", "items": [...]},
    )

    assert response.status_code == 201
```

## 📊 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| **认证器** | ✅ StubAuthenticator | P0 开发模式 |
| **集成方式** | ✅ setup_security() | 统一入口 |
| **强制认证** | ❌ require_auth=False | 开发模式 |
| **排除路径** | ✅ 已配置 | /health, /docs 等 |
| **业务代码** | ✅ 可用 | SecurityContext.get_user() |

## 🎯 下一步

1. **P0 → P1**: 实现 JWTAuthenticator
2. **启用强制认证**: `require_auth=True`
3. **添加权限检查**: 在 Handler 中使用 `user.has_permission()`
4. **集成 bento-security**: 企业级功能

## ✅ 总结

**my-shop 已成功集成安全中间件！**

- ✅ 使用 `setup_security()` 统一入口
- ✅ 实现 `StubAuthenticator` 用于开发
- ✅ 在中间件栈最前面执行
- ✅ 业务代码可以使用 `SecurityContext`
- ✅ 易于升级到生产环境

**一行代码集成安全**:
```python
setup_security(app, authenticator=StubAuthenticator())
```

---

## 🏢 多租户集成（可选）

### 概述

my-shop 支持多租户功能，通过 `X-Tenant-ID` HTTP header 识别租户。

### 架构设计

```
Request with X-Tenant-ID header
  ↓
bento.multitenancy.add_tenant_middleware()
  ├─ HeaderTenantResolver 解析 header
  ├─ TenantContext.set(tenant_id)
  └─ 继续处理请求
  ↓
bind_security_tenant 中间件
  ├─ 从 TenantContext.get() 读取
  ├─ 同步到 SecurityContext.set_tenant()
  └─ 继续处理请求
  ↓
业务代码可以使用 SecurityContext.get_tenant()
```

### 配置说明

**文件**: `runtime/bootstrap_v2.py`

```python
from bento.multitenancy import add_tenant_middleware, HeaderTenantResolver, TenantContext
from bento.security import SecurityContext

# 1. 添加租户中间件
add_tenant_middleware(
    app,
    resolver=HeaderTenantResolver(header_name="X-Tenant-ID"),
    require_tenant=False,  # 开发模式：不强制要求租户
    exclude_paths=["/health", "/ping", "/docs", "/openapi.json", "/redoc"],
)

# 2. 同步租户到 SecurityContext
@app.middleware("http")
async def bind_security_tenant(request: Request, call_next):
    """Propagate TenantContext -> SecurityContext."""
    tenant_id = TenantContext.get()
    SecurityContext.set_tenant(tenant_id)
    try:
        return await call_next(request)
    finally:
        SecurityContext.set_tenant(None)
```

### 使用方式

#### 1. 在 API 请求中传递租户

##### 获取当前用户信息（`GET /api/v1/auth/me`）

```bash
# 不带租户
curl http://localhost:8000/api/v1/auth/me

# 带租户
curl -H "X-Tenant-ID: tenant-a" http://localhost:8000/api/v1/auth/me
```

**响应示例**:
```json
{
  "id": "demo-user",
  "permissions": ["*"],
  "roles": ["admin"],
  "tenant_id": "tenant-a",
  "metadata": {
    "stub": true,
    "environment": "development",
    "username": "demo"
  }
}
```

##### 获取安全上下文（调试用，`GET /api/v1/auth/me/context`）

```bash
# 不带租户
curl http://localhost:8000/api/v1/auth/me/context

# 带租户
curl -H "X-Tenant-ID: tenant-a" http://localhost:8000/api/v1/auth/me/context
```

**响应示例**:
```json
{
  "authenticated": true,
  "user": {
    "id": "demo-user",
    "permissions": ["*"],
    "roles": ["admin"],
    "metadata": {
      "stub": true,
      "environment": "development",
      "username": "demo"
    }
  },
  "tenant_id": "tenant-a",
  "has_permission_check": {
    "admin": false,
    "user": false
  }
}
```

#### 2. 在业务代码中使用租户

```python
from bento.security import SecurityContext

class CreateOrderHandler(CommandHandler):
    async def handle(self, command: CreateOrderCommand):
        # 获取当前用户
        user = SecurityContext.require_user()

        # 获取当前租户
        tenant_id = SecurityContext.get_tenant()  # 可能为 None
        # 或者强制要求租户
        tenant_id = SecurityContext.require_tenant()  # 无租户时抛异常

        # 创建订单（租户隔离）
        order = Order.create(
            tenant_id=tenant_id,
            customer_id=user.id,
            items=command.items,
        )

        await self.order_repo.save(order)
```

#### 3. 在 Repository 中实现租户隔离

```python
class OrderRepositoryImpl(RepositoryAdapter[Order]):
    async def find_by_customer(self, customer_id: str) -> list[Order]:
        """查询订单（自动租户隔离）"""
        tenant_id = SecurityContext.get_tenant()

        spec = (
            EntitySpecificationBuilder()
            .where("customer_id", "=", customer_id)
            .where("tenant_id", "=", tenant_id)  # 租户隔离
            .build()
        )

        return await self.find_all(spec)
```

### 配置选项

| 参数 | 说明 | 默认值 | 推荐值 |
|------|------|--------|--------|
| `header_name` | HTTP header 名称 | `X-Tenant-ID` | 保持默认 |
| `require_tenant` | 是否强制要求租户 | `False` | 开发：`False`<br>生产：`True` |
| `exclude_paths` | 排除路径列表 | `[]` | `["/health", "/docs"]` |

### 生产环境配置

```python
# 生产环境：强制要求租户
add_tenant_middleware(
    app,
    resolver=HeaderTenantResolver(header_name="X-Tenant-ID"),
    require_tenant=True,  # 强制要求
    exclude_paths=["/health", "/ping"],
)
```

**效果**：
- ✅ 有 `X-Tenant-ID` header → 正常处理
- ❌ 无 `X-Tenant-ID` header → 返回 400 Bad Request

### 测试验证

运行集成测试：
```bash
cd applications/my-shop
uv run python test_tenant_integration.py
```

**测试覆盖**：
- ✅ 无租户 header 的请求
- ✅ 带租户 header 的请求
- ✅ 不同租户的隔离
- ✅ 用户和租户共存
- ✅ 排除路径的行为

### 最佳实践

#### 1. 租户隔离策略

```python
# ✅ 推荐：在 Repository 层自动添加租户过滤
class BaseMultiTenantRepository(RepositoryAdapter[AR]):
    def _add_tenant_filter(self, spec: Specification) -> Specification:
        """自动添加租户过滤"""
        tenant_id = SecurityContext.get_tenant()
        if tenant_id:
            return spec.and_(
                EntitySpecificationBuilder()
                .where("tenant_id", "=", tenant_id)
                .build()
            )
        return spec
```

#### 2. 租户验证

```python
# ✅ 推荐：在关键操作前验证租户
class DeleteOrderHandler(CommandHandler):
    async def handle(self, command: DeleteOrderCommand):
        tenant_id = SecurityContext.require_tenant()  # 强制要求
        order = await self.order_repo.get(command.order_id)

        # 验证订单属于当前租户
        if order.tenant_id != tenant_id:
            raise DomainException(reason_code="FORBIDDEN")

        await self.order_repo.delete(order)
```

#### 3. 租户元数据

```python
# ✅ 推荐：在聚合根中存储租户信息
class Order(AggregateRoot):
    def __init__(
        self,
        id: ID,
        tenant_id: str,  # 租户 ID
        customer_id: str,
        items: list[OrderItem],
    ):
        super().__init__(id)
        self.tenant_id = tenant_id
        self.customer_id = customer_id
        self.items = items
```

### 常见问题

#### Q: 租户和用户的关系？
A: 租户是组织级别的隔离，用户属于某个租户。一个请求同时包含用户和租户信息。

#### Q: 如何切换租户？
A: 通过更改 `X-Tenant-ID` header 的值。前端应用需要管理当前租户上下文。

#### Q: 租户信息存储在哪里？
A:
- 请求期间：`TenantContext` 和 `SecurityContext`（ContextVar）
- 持久化：聚合根的 `tenant_id` 字段

#### Q: 如何支持用户跨租户？
A: 在用户的元数据中存储所属租户列表，前端允许切换租户。

### 升级路径

**P0 (当前)**:
- ✅ `HeaderTenantResolver` - 从 HTTP header 解析
- ✅ `require_tenant=False` - 不强制要求

**P1 (生产)**:
- 🔄 `require_tenant=True` - 强制要求租户
- 🔄 在所有 Repository 中实现租户隔离

**P2 (企业级)**:
- 🔄 `TokenTenantResolver` - 从 JWT token 解析
- 🔄 `SubdomainTenantResolver` - 从子域名解析
- 🔄 租户级别的配额和限流

---

## 📚 相关文档

- [Bento Security 模块](../../../src/bento/security/README.md)
- [Bento Multi-Tenancy 模块](../../../src/bento/multitenancy/README.md)
- [SecurityContext API](../../../src/bento/security/context.py)
- [TenantContext API](../../../src/bento/multitenancy/context.py)

