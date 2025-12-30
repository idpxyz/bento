# Bento Security Module

**Provides mechanisms, NOT policies.**

This module provides authentication and authorization **mechanisms** for Bento applications.
It does NOT include concrete authentication implementations.

## Architecture Philosophy

```
┌─────────────────────────────────────────────────────────┐
│  Application Layer                                       │
│  - Chooses authentication strategy                      │
│  - Implements IAuthenticator/ITenantResolver            │
│  - Injects into Framework                               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Bento Framework (THIS MODULE)                          │
│                                                          │
│  ✅ Provides:                                            │
│     - Interfaces (IAuthenticator, IAuthorizer, etc.)    │
│     - Context (SecurityContext)                         │
│     - Middleware (add_security_middleware)              │
│     - Decorators (@require_auth, @require_permission)   │
│                                                          │
│  ❌ Does NOT provide:                                    │
│     - Concrete authenticators (JWT, OAuth, etc.)        │
│     - Authentication providers (Logto, Auth0, etc.)     │
│     - M2M authentication                                │
│     - Multi-framework support                           │
└─────────────────────────────────────────────────────────┘
```

## Design Principles

| Principle | Description |
|-----------|-------------|
| **Framework provides mechanisms** | Interfaces, context, middleware, decorators |
| **Application provides strategies** | Concrete implementations (JWT, OAuth, custom) |
| **Zero dependencies** | No external auth libraries (PyJWT, httpx, etc.) |
| **Pluggable** | Applications can use ANY authentication solution |
| **Framework purity** | No coupling to specific auth providers |

## Where to Get Concrete Implementations?

### Option 1: bento-security (Recommended for Enterprise)

Official extension with full-featured authentication providers:

```bash
pip install bento-security[fastapi]
```

```python
from bento_security.providers import LogtoAuthProvider
from bento.security import add_security_middleware

authenticator = LogtoAuthProvider(
    endpoint="https://your-app.logto.app",
    app_id="app-id",
    app_secret="app-secret",  # M2M support
)

add_security_middleware(app, authenticator)
```

**Features**:
- ✅ Logto, Auth0, Keycloak providers
- ✅ M2M authentication
- ✅ CQRS integration (@secured_command_handler)
- ✅ Multi-framework support (FastAPI, Django, Flask)

### Option 2: Custom Implementation (Recommended for Flexibility)

Implement `IAuthenticator` interface yourself:

```python
from bento.security import IAuthenticator, CurrentUser

class JWTAuthenticator:
    def __init__(self, jwks_url: str, audience: str):
        self.jwks_url = jwks_url
        self.audience = audience

    async def authenticate(self, request) -> CurrentUser | None:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]
        claims = await self._verify_token(token)

        return CurrentUser(
            id=claims["sub"],
            permissions=claims.get("permissions", []),
            roles=claims.get("roles", []),
            metadata=claims,
        )
```

### 2. Add Middleware

```python
from fastapi import FastAPI
from bento.security import add_security_middleware

app = FastAPI()

add_security_middleware(
    app,
    authenticator=JWTAuthenticator(jwks_url="...", audience="..."),
    require_auth=True,
    exclude_paths=["/health", "/docs", "/openapi.json"],
)
```

### 3. Use in Business Code

```python
from bento.security import SecurityContext

async def create_order(order_data):
    # Get authenticated user (raises UNAUTHORIZED if not authenticated)
    user = SecurityContext.require_user()

    # Check permissions
    if not user.has_permission("orders:write"):
        raise DomainException(reason_code="FORBIDDEN")

    # Use user info
    order = Order(
        user_id=user.id,
        ...
    )
```

## Components

### SecurityContext

Async-safe storage for current user using ContextVar.

```python
from bento.security import SecurityContext

# Check if authenticated
if SecurityContext.is_authenticated():
    user = SecurityContext.get_user()

# Require authentication (raises UNAUTHORIZED if not)
user = SecurityContext.require_user()

# Check permissions via context
if SecurityContext.has_permission("orders:read"):
    ...

# Check roles via context
if SecurityContext.has_role("admin"):
    ...
```

### CurrentUser

User model with permission and role utilities.

```python
from bento.security import CurrentUser

user = CurrentUser(
    id="user-123",
    permissions=["orders:read", "orders:write"],
    roles=["admin"],
    metadata={"email": "user@example.com"},
)

# Permission checks
user.has_permission("orders:read")  # True
user.has_any_permission(["orders:read", "products:read"])  # True
user.has_all_permissions(["orders:read", "orders:write"])  # True

# Role checks
user.has_role("admin")  # True
user.has_any_role(["admin", "superadmin"])  # True
```

#### Wildcard Permission Support

Permissions support fnmatch wildcard patterns for flexible permission management:

```python
user = CurrentUser(
    id="user-123",
    permissions=["orders:*", "products:read", "*:admin"],
)

# Wildcard matching
user.has_permission("orders:read")      # True (matches "orders:*")
user.has_permission("orders:write")     # True (matches "orders:*")
user.has_permission("products:read")    # True (exact match)
user.has_permission("products:write")   # False
user.has_permission("users:admin")      # True (matches "*:admin")

# Supported patterns:
# - "orders:*"     → matches "orders:read", "orders:write", etc.
# - "*:read"       → matches "orders:read", "products:read", etc.
# - "*"            → matches all permissions
# - "order?"       → matches "orders" (single char wildcard)
# - "[op]rders:*"  → matches "orders:*" or "prders:*" (bracket pattern)
```

**Performance Note**: Exact matches are checked first (fast path), then wildcard patterns are evaluated.

### IAuthenticator

Protocol for authentication providers.

```python
from bento.security import IAuthenticator, CurrentUser

class MyAuthenticator(IAuthenticator):
    async def authenticate(self, request) -> CurrentUser | None:
        """
        Return CurrentUser if authenticated, None otherwise.
        """
        ...
```

### IAuthorizer

Protocol for custom authorization logic (optional).

```python
from bento.security import IAuthorizer, CurrentUser

class ResourceAuthorizer(IAuthorizer):
    async def authorize(
        self,
        user: CurrentUser,
        permission: str,
        resource=None,
    ) -> bool:
        """
        Check if user is authorized.
        Supports resource-based authorization.
        """
        # Check if user owns the resource
        if resource and hasattr(resource, 'owner_id'):
            if resource.owner_id == user.id:
                return True

        # Fall back to permission check
        return user.has_permission(permission)
```

### Middleware

```python
from bento.security import add_security_middleware

add_security_middleware(
    app,
    authenticator=authenticator,
    require_auth=True,       # Return 401 if not authenticated
    exclude_paths=["/health"], # Skip these paths
)
```

## Integration with Multi-Tenancy

Security and Multi-Tenancy work together:

```
Request
    │
    ▼
┌─────────────────────────┐
│ Security Middleware     │  ← First: Authenticate
│ - Authenticate user     │
│ - Set SecurityContext   │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Tenant Middleware       │  ← Second: Resolve tenant
│ - Get tenant from user  │
│ - Set TenantContext     │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ Business Logic          │
│ - Both contexts ready   │
└─────────────────────────┘
```

### Example: Token-based Tenant Resolution

```python
from bento.multitenancy import TokenTenantResolver, add_tenant_middleware

# TokenTenantResolver reads tenant from user's token/metadata
add_security_middleware(app, JWTAuthenticator())
add_tenant_middleware(
    app,
    resolver=TokenTenantResolver(claim_name="tenant_id"),
)
```

## Error Handling

### UNAUTHORIZED (401)

Raised when:
- `SecurityContext.require_user()` called without authenticated user
- `require_auth=True` and no valid authentication

```json
{
  "reason_code": "UNAUTHORIZED",
  "message": "Authentication required",
  "http_status": 401
}
```

### FORBIDDEN (403)

For authorization failures, use in your application:

```python
if not user.has_permission("orders:write"):
    raise DomainException(reason_code="FORBIDDEN")
```

## Common Authenticator Patterns

### JWT with JWKS

```python
class JWKSAuthenticator(IAuthenticator):
    def __init__(self, jwks_url: str, audience: str, issuer: str):
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer

    async def authenticate(self, request) -> CurrentUser | None:
        token = self._extract_token(request)
        if not token:
            return None

        claims = await self._verify_with_jwks(token)
        return CurrentUser(
            id=claims["sub"],
            permissions=claims.get("permissions", []),
            metadata=claims,
        )
```

### API Key

```python
class APIKeyAuthenticator(IAuthenticator):
    def __init__(self, api_keys: dict[str, str]):
        self.api_keys = api_keys  # key -> user_id

    async def authenticate(self, request) -> CurrentUser | None:
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in self.api_keys:
            return None

        return CurrentUser(
            id=self.api_keys[api_key],
            permissions=["api:access"],
        )
```

### Composite (Multiple Methods)

```python
class CompositeAuthenticator(IAuthenticator):
    def __init__(self, authenticators: list[IAuthenticator]):
        self.authenticators = authenticators

    async def authenticate(self, request) -> CurrentUser | None:
        for auth in self.authenticators:
            user = await auth.authenticate(request)
            if user:
                return user
        return None

# Usage
authenticator = CompositeAuthenticator([
    JWTAuthenticator(...),
    APIKeyAuthenticator(...),
])
```

## Best Practices

1. **Always use `require_user()`** when authentication is required
2. **Check permissions early** in your handlers
3. **Use meaningful permission strings** like `orders:read`, `products:write`
4. **Keep authenticator stateless** for scalability
5. **Exclude health/docs paths** from authentication
6. **Log authentication failures** for security monitoring

## Decorators

Declarative security checks for cleaner code.

### @require_auth

```python
from bento.security import require_auth

@require_auth
async def protected_endpoint():
    user = SecurityContext.get_user()  # Guaranteed to exist
    ...
```

### @require_permission

```python
from bento.security import require_permission

@require_permission("orders:write")
async def create_order():
    ...
```

### @require_any_permission / @require_all_permissions

```python
from bento.security import require_any_permission, require_all_permissions

@require_any_permission("orders:read", "orders:admin")
async def view_order():
    ...

@require_all_permissions("orders:read", "orders:write")
async def manage_order():
    ...
```

### @require_role / @require_any_role / @require_all_roles

```python
from bento.security import require_role, require_any_role, require_all_roles

@require_role("admin")
async def admin_only():
    ...

@require_any_role("admin", "moderator")
async def moderation():
    ...

@require_all_roles("admin", "super_admin")
async def super_admin_action():
    ...
```

### @require_owner_or_role

Resource-based authorization for owner or admin access.

```python
from bento.security import require_owner_or_role

@require_owner_or_role("admin")
async def update_order(order: Order):
    # order.owner_id must match user.id, or user must be admin
    ...

# Custom owner getter
@require_owner_or_role("admin", owner_getter=lambda item: item.created_by)
async def delete_item(item: Item):
    ...
```

## FastAPI Depends

For FastAPI users who prefer dependency injection style:

```python
from fastapi import Depends
from bento.security import get_current_user, get_optional_user, CurrentUser

@app.get("/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return {"id": user.id, "roles": user.roles}

@app.get("/public")
async def public(user: CurrentUser | None = Depends(get_optional_user)):
    if user:
        return {"message": f"Hello, {user.id}"}
    return {"message": "Hello, guest"}
```

### Available Depends

| Depend | Description |
|--------|-------------|
| `get_current_user` | Returns user or raises UNAUTHORIZED |
| `get_optional_user` | Returns user or None |
| `require_permissions("a", "b")` | Requires all permissions |
| `require_roles("a", "b")` | Requires all roles |

### Factory Pattern

```python
from bento.security.depends import require_permissions, require_roles

@app.post("/orders")
async def create_order(
    user: CurrentUser = Depends(require_permissions("orders:write"))
):
    ...

@app.delete("/admin/users/{id}")
async def delete_user(
    id: str,
    admin: CurrentUser = Depends(require_roles("admin"))
):
    ...
```

## Built-in Providers

Pre-built authenticators for popular identity providers.

See [providers/README.md](providers/README.md) for details.

```python
from bento.security.providers import LogtoAuthenticator, Auth0Authenticator

# Logto
authenticator = LogtoAuthenticator(
    endpoint="https://your-app.logto.app",
    app_id="your-app-id",
)

# Auth0
authenticator = Auth0Authenticator(
    domain="your-tenant.auth0.com",
    audience="https://your-api.example.com",
)
```

### M2M Authentication

All providers support Machine-to-Machine authentication:

```python
authenticator = LogtoAuthenticator(
    endpoint="https://your-app.logto.app",
    app_id="your-app-id",
    # Enable M2M
    client_id="m2m-client-id",
    client_secret="m2m-client-secret",
)
```

## Module Structure

```
bento/security/
├── __init__.py      # Public exports
├── context.py       # SecurityContext
├── models.py        # CurrentUser
├── ports.py         # IAuthenticator, IAuthorizer
├── middleware.py    # FastAPI middleware
├── decorators.py    # Security decorators
├── depends.py       # FastAPI dependencies
└── providers/       # Built-in authenticators
    ├── base.py      # JWTAuthenticatorBase
    ├── m2m.py       # M2M support
    ├── logto.py     # Logto
    ├── auth0.py     # Auth0
    └── keycloak.py  # Keycloak
```

### 可用装饰器

| 装饰器 | 用途 |
|--------|------|
| `@require_auth` | 要求认证 |
| `@require_permission("x")` | 要求特定权限 |
| `@require_any_permission("a", "b")` | 要求任意权限 |
| `@require_all_permissions("a", "b")` | 要求所有权限 |
| `@require_role("admin")` | 要求特定角色 |
| `@require_any_role("a", "b")` | 要求任意角色 |
| `@require_all_roles("a", "b")` | 要求所有角色 |
| `@require_owner_or_role("admin")` | 资源所有者或角色 |

### 使用示例

```python
from bento.security import require_permission, require_owner_or_role

@require_permission("orders:write")
async def create_order():
    ...

@require_owner_or_role("admin")
async def update_order(order: Order):
    # order.owner_id == user.id OR user has 'admin' role
    ...
```

很好的问题！让我详细解释 `get_current_user` 能获取到用户的完整原理。

让我查看 `get_current_user` 的实现，以及 `SecurityContext` 的工作原理：

现在让我查看 `SecurityContext` 的实现，这是关键：

现在让我查看安全中间件的实现，了解用户是如何被设置到 [SecurityContext](cci:2://file:///workspace/bento/src/bento/security/context.py:29:0-173:42) 中的：

完美！现在我可以给你详细解释 [get_current_user](cci:1://file:///workspace/bento/src/bento/security/depends.py:32:0-51:15) 能获取到用户的完整原理。

## 🔍 完整的用户获取原理

### 📊 整个流程图

```
请求到达
  ↓
安全中间件 (middleware.py)
  ├─ 检查路径是否排除
  ├─ 调用 authenticator.authenticate(request)
  ├─ 设置 SecurityContext.set_user(user)  ← 关键！
  └─ 继续处理请求
  ↓
FastAPI 依赖注入 (depends.py)
  ├─ get_current_user() 调用
  ├─ 从 SecurityContext.get_user() 获取用户
  └─ 返回给 Handler
  ↓
业务代码获得用户
```

### 🔑 三个关键组件

#### 1️⃣ **SecurityContext** - 请求作用域存储

```python
# context.py
class SecurityContext:
    # 使用 ContextVar 存储用户（async-safe）
    _current_user: ContextVar["CurrentUser | None"] = ContextVar(
        'current_user', default=None
    )

    @classmethod
    def set_user(cls, user: "CurrentUser | None") -> None:
        """设置当前用户"""
        cls._current_user.set(user)  # ← 存储到 ContextVar

    @classmethod
    def get_user(cls) -> "CurrentUser | None":
        """获取当前用户"""
        return cls._current_user.get()  # ← 从 ContextVar 读取
```

**关键特性**：
- ✅ **ContextVar** - Python 的上下文变量，每个异步任务有独立的值
- ✅ **请求隔离** - 不同请求的用户不会相互干扰
- ✅ **Async-safe** - 安全用于异步代码

#### 2️⃣ **安全中间件** - 设置用户

```python
# middleware.py
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path

    # 1. 检查是否排除
    if any(path.startswith(ep) for ep in exclude_paths):
        return await call_next(request)

    # 2. 调用认证器
    user = await authenticator.authenticate(request)  # ← 获取用户

    # 3. 检查是否需要认证
    if require_auth and not user:
        return JSONResponse(status_code=401, ...)

    # 4. 设置 SecurityContext ← 关键！
    SecurityContext.set_user(user)

    try:
        response = await call_next(request)
        return response
    finally:
        # 5. 清理上下文
        SecurityContext.clear()
```

**执行顺序**：
1. 中间件拦截请求
2. 调用 [authenticator.authenticate()](cci:1://file:///workspace/bento/applications/my-shop/shared/auth/stub_authenticator.py:29:4-54:9) 获取用户
3. 将用户存储到 [SecurityContext](cci:2://file:///workspace/bento/src/bento/security/context.py:29:0-173:42)
4. 继续处理请求（此时用户已在上下文中）
5. 请求完成后清理上下文

#### 3️⃣ **FastAPI 依赖注入** - 获取用户

```python
# depends.py
async def get_current_user() -> "CurrentUser":
    """FastAPI 依赖"""
    user = SecurityContext.get_user()  # ← 从上下文读取
    if not user:
        raise DomainException(reason_code="UNAUTHORIZED")
    return user
```

**使用方式**：
```python
@app.get("/api/v1/auth/me")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user)  # ← 依赖注入
):
    return current_user
```

### 🔄 完整的执行流程

```
1. 请求: GET /api/v1/auth/me
   ↓
2. 安全中间件拦截
   ├─ 路径不在排除列表中
   ├─ 调用 StubAuthenticator.authenticate(request)
   │  └─ 返回 CurrentUser(id="demo-user", permissions=["*"], ...)
   ├─ 调用 SecurityContext.set_user(user)
   │  └─ 将用户存储到 ContextVar 中
   └─ 继续处理请求
   ↓
3. FastAPI 路由处理
   ├─ 识别到 current_user: CurrentUser = Depends(get_current_user)
   ├─ 调用 get_current_user() 依赖
   │  └─ 调用 SecurityContext.get_user()
   │     └─ 从 ContextVar 读取用户（之前由中间件设置）
   └─ 将用户注入到 Handler
   ↓
4. Handler 执行
   ├─ 接收到 current_user 参数
   ├─ 返回用户信息
   └─ 响应 200 OK
   ↓
5. 中间件清理
   └─ SecurityContext.clear() 清理上下文
```

### 💡 为什么这样设计？

#### ✅ **ContextVar 的优势**

```python
# 问题：全局变量不安全
_current_user = None  # ❌ 多个请求会相互干扰

# 解决：ContextVar 隔离每个请求
_current_user: ContextVar = ContextVar('current_user', default=None)  # ✅
```

#### ✅ **中间件 + 依赖注入的优势**

```
中间件负责：设置用户（一次）
  ↓
依赖注入负责：获取用户（多次）

这样分离关注点：
- 中间件：认证逻辑（一次性）
- 业务代码：使用用户（多次）
```

### 📋 三种获取用户的方式

#### 方式 1: FastAPI 依赖注入（推荐）

```python
@app.get("/api/v1/auth/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return user
```

**优点**：
- ✅ FastAPI 自动注入
- ✅ 类型检查
- ✅ OpenAPI 文档自动生成

#### 方式 2: 直接从 SecurityContext 获取

```python
from bento.security import SecurityContext

class CreateOrderHandler(CommandHandler):
    async def handle(self, command):
        user = SecurityContext.get_user()  # 直接获取
        if user:
            # 使用用户信息
            pass
```

**优点**：
- ✅ 在任何地方都能用
- ✅ 不需要依赖注入

#### 方式 3: 可选用户

```python
@app.get("/public")
async def public_endpoint(
    user: CurrentUser | None = Depends(get_optional_user)
):
    if user:
        return {"message": f"Hello, {user.id}"}
    return {"message": "Hello, guest"}
```

### 🎯 当前 my-shop 的实现

```python
# shared/api/auth_routes.py
@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_endpoint(
    current_user: CurrentUser | None = Depends(get_current_user),
):
    # 1. FastAPI 调用 get_current_user()
    # 2. get_current_user() 从 SecurityContext.get_user() 读取
    # 3. SecurityContext 返回之前由中间件设置的用户
    # 4. 返回给客户端
    return CurrentUserResponse(...)
```

### 🔐 安全性保证

```
请求 A                          请求 B
  ↓                              ↓
ContextVar 隔离                ContextVar 隔离
  ├─ user_A                      ├─ user_B
  └─ 互不干扰                     └─ 互不干扰
```

**即使在并发请求中**：
- ✅ 请求 A 的用户不会泄露给请求 B
- ✅ 每个请求都有独立的 ContextVar 副本
- ✅ 完全线程安全和异步安全

### 📊 总结

| 组件 | 职责 | 时机 |
|------|------|------|
| **SecurityContext** | 存储用户（ContextVar） | 全程 |
| **安全中间件** | 设置用户 | 请求开始 |
| **FastAPI 依赖** | 获取用户 | 路由处理 |
| **业务代码** | 使用用户 | 任何时候 |

**核心原理**：
1. 中间件拦截请求，调用认证器获取用户
2. 中间件将用户存储到 [SecurityContext](cci:2://file:///workspace/bento/src/bento/security/context.py:29:0-173:42)（ContextVar）
3. 依赖注入从 [SecurityContext](cci:2://file:///workspace/bento/src/bento/security/context.py:29:0-173:42) 读取用户
4. 业务代码接收到用户对象
5. 请求完成后清理上下文

这就是为什么 [get_current_user](cci:1://file:///workspace/bento/src/bento/security/depends.py:32:0-51:15) 能获取到用户的完整原理！🎉
