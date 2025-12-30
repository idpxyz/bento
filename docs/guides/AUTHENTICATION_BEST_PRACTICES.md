# Bento Framework 认证和鉴权最佳实践

## 核心原则：提供机制，不提供策略

Bento Framework 作为一个 DDD 框架，**不实现具体的认证和鉴权逻辑**，而是提供：

1. **接口定义** - `IAuthenticator`, `IAuthorizer`, `ITenantResolver`
2. **上下文管理** - `SecurityContext` (async-safe)
3. **基础机制** - Middleware, Decorators
4. **集成助手** - 便捷的集成函数

应用层根据需求选择具体实现：
- P0: Stub 实现（快速开发）
- P1: 自定义 JWT/OAuth（生产环境）
- P2: bento-security（企业级功能）

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│  Application Layer (my-shop, loms, etc.)                │
│  - 选择具体的认证实现                                    │
│  - 实现 IAuthenticator/ITenantResolver                  │
│  - 注入到 Framework                                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Bento Framework (src/bento/security)                   │
│                                                          │
│  ✅ 接口定义                                             │
│     - IAuthenticator: 认证接口                          │
│     - IAuthorizer: 授权接口                             │
│     - ITenantResolver: 租户解析接口                     │
│                                                          │
│  ✅ 上下文管理                                           │
│     - SecurityContext: 存储当前用户和租户               │
│     - CurrentUser: 用户模型                             │
│                                                          │
│  ✅ 基础机制                                             │
│     - add_security_middleware(): 中间件集成             │
│     - @require_auth: 装饰器                             │
│     - @require_permission: 权限检查                     │
│                                                          │
│  ❌ 不包含                                               │
│     - 具体的认证实现 (JWT, OAuth, etc.)                 │
│     - M2M 认证                                           │
│     - CQRS 集成                                          │
│     - 多框架支持                                         │
└─────────────────────────────────────────────────────────┘
```

## Framework 层接口

### 1. IAuthenticator - 认证接口

```python
from bento.security import IAuthenticator, CurrentUser

class IAuthenticator(Protocol):
    """认证提供器接口

    应用层实现此接口来提供认证逻辑。
    Framework 会在每个请求时调用 authenticate()。
    """

    async def authenticate(self, request: Any) -> CurrentUser | None:
        """认证请求并返回当前用户

        Args:
            request: 请求对象 (e.g., FastAPI Request)

        Returns:
            CurrentUser 如果认证成功，None 如果未认证
        """
        ...
```

### 2. ITenantResolver - 租户解析接口

```python
from bento.security import ITenantResolver

class ITenantResolver(Protocol):
    """租户解析器接口

    应用层实现此接口来提取租户信息。
    支持多租户应用的数据隔离。
    """

    async def resolve_tenant(self, request: Any) -> str | None:
        """从请求中解析租户 ID

        Args:
            request: 请求对象

        Returns:
            租户 ID，如果找到的话
        """
        ...
```

### 3. SecurityContext - 上下文管理

```python
from bento.security import SecurityContext, CurrentUser

# 设置用户和租户 (通常在 middleware 中)
SecurityContext.set_user(user)
SecurityContext.set_tenant(tenant_id)

# 获取用户和租户 (在业务代码中)
user = SecurityContext.get_user()  # 可能为 None
tenant_id = SecurityContext.get_tenant()  # 可能为 None

# 强制要求 (未设置会抛异常)
user = SecurityContext.require_user()  # 抛 UNAUTHORIZED
tenant_id = SecurityContext.require_tenant()  # 抛 TENANT_REQUIRED

# 检查权限
if SecurityContext.has_permission("orders:create"):
    # 有权限
    ...

# 检查角色
if SecurityContext.has_role("admin"):
    # 是管理员
    ...
```

## 应用层实现

### 方案 1: Stub 实现 (P0 - 快速开发)

**适用场景**: 开发/测试阶段，快速验证业务逻辑

```python
# applications/my-shop/shared/auth/stub_authenticator.py
from bento.security import CurrentUser

class StubAuthenticator:
    """开发用的 Stub 认证器"""

    async def authenticate(self, request) -> CurrentUser | None:
        # 接受所有请求为已认证
        return CurrentUser(
            id="demo-user",
            permissions=["*"],  # 全权限
            roles=["admin"],
            metadata={"stub": True},
        )

class StubTenantResolver:
    """开发用的 Stub 租户解析器"""

    async def resolve_tenant(self, request) -> str | None:
        # 从 header 提取，或使用默认值
        return request.headers.get("X-Tenant-ID", "demo-tenant")
```

**集成**:
```python
# applications/my-shop/runtime/bootstrap.py
from bento.security import add_security_middleware
from my_shop.shared.auth import StubAuthenticator, StubTenantResolver

def create_app():
    app = FastAPI()

    add_security_middleware(
        app,
        authenticator=StubAuthenticator(),
        tenant_resolver=StubTenantResolver(),
        require_auth=False,  # P0: 不强制认证
    )

    return app
```

### 方案 2: JWT 认证 (P1 - 生产环境)

**适用场景**: 生产环境，使用 JWT 令牌认证

```python
# applications/my-shop/shared/auth/jwt_authenticator.py
import jwt
from jwt import PyJWKClient
from bento.security import CurrentUser

class JWTAuthenticator:
    """JWT 认证器"""

    def __init__(self, jwks_url: str, audience: str):
        self.jwks_client = PyJWKClient(jwks_url)
        self.audience = audience

    async def authenticate(self, request) -> CurrentUser | None:
        # 1. 提取 token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]

        try:
            # 2. 验证 token
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
            )

            # 3. 创建用户
            return CurrentUser(
                id=claims["sub"],
                permissions=claims.get("permissions", []),
                roles=claims.get("roles", []),
                metadata=claims,
            )
        except Exception:
            return None

class JWTTenantResolver:
    """从 JWT 提取租户"""

    def __init__(self, jwks_url: str):
        self.jwks_client = PyJWKClient(jwks_url)

    async def resolve_tenant(self, request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        token = auth_header[7:]

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(token, signing_key.key, algorithms=["RS256"])
            return claims.get("tenant_id") or claims.get("org_id")
        except Exception:
            return None
```

**集成**:
```python
from my_shop.shared.auth import JWTAuthenticator, JWTTenantResolver

authenticator = JWTAuthenticator(
    jwks_url="https://your-auth.com/.well-known/jwks.json",
    audience="my-shop-api",
)

tenant_resolver = JWTTenantResolver(
    jwks_url="https://your-auth.com/.well-known/jwks.json",
)

add_security_middleware(app, authenticator, tenant_resolver)
```

### 方案 3: bento-security (P2 - 企业级)

**适用场景**: 需要 M2M、多框架、CQRS 集成等企业级功能

```bash
pip install bento-security[fastapi]
```

```python
from bento_security.providers import LogtoAuthProvider
from bento_security import secured_command_handler

# 1. 使用完整的认证提供器
authenticator = LogtoAuthProvider(
    endpoint="https://your-app.logto.app",
    app_id="app-id",
    app_secret="app-secret",  # M2M 支持
)

add_security_middleware(app, authenticator)

# 2. CQRS 集成
@secured_command_handler(
    permissions=["orders:create"],
    audit=True,
)
class CreateOrderHandler(CommandHandler):
    async def handle(self, command):
        # 自动认证和授权
        user = SecurityContext.current_user()
        ...
```

## 业务代码使用

### 在 Command Handler 中使用

```python
from bento.application import CommandHandler
from bento.security import SecurityContext

class CreateOrderHandler(CommandHandler[CreateOrderCommand, str]):
    async def handle(self, command: CreateOrderCommand) -> str:
        # 1. 获取当前用户
        user = SecurityContext.require_user()  # 未认证会抛异常

        # 2. 获取租户 (多租户应用)
        tenant_id = SecurityContext.require_tenant()

        # 3. 检查权限 (可选)
        if not user.has_permission("orders:create"):
            raise DomainException(reason_code="FORBIDDEN")

        # 4. 业务逻辑
        order = Order.create(
            customer_id=command.customer_id,
            items=command.items,
            created_by=user.id,
            tenant_id=tenant_id,
        )

        repo = self.uow.repository(Order)
        await repo.save(order)

        return str(order.id)
```

### 在 Query Handler 中使用

```python
from bento.application import QueryHandler
from bento.security import SecurityContext

class ListOrdersHandler(QueryHandler[ListOrdersQuery, list[OrderDTO]]):
    async def handle(self, query: ListOrdersQuery) -> list[OrderDTO]:
        # 1. 获取租户 (多租户数据隔离)
        tenant_id = SecurityContext.require_tenant()

        # 2. 构建查询条件
        spec = (
            EntitySpecificationBuilder()
            .where("tenant_id", "=", tenant_id)  # 租户隔离
            .order_by("created_at", desc=True)
            .build()
        )

        # 3. 查询数据
        repo = self.uow.repository(Order)
        orders = await repo.find_all(spec)

        # 4. 转换为 DTO
        return [OrderDTO.from_domain(order) for order in orders]
```

### 在 API 层使用 (可选)

```python
from fastapi import APIRouter, Depends
from bento.security import get_current_user, CurrentUser

router = APIRouter()

@router.get("/profile")
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user)
):
    """获取当前用户信息

    FastAPI 会自动注入当前用户
    """
    return {
        "id": current_user.id,
        "permissions": current_user.permissions,
        "roles": current_user.roles,
    }
```

## 测试

### 单元测试

```python
from bento.security import SecurityContext, CurrentUser

async def test_create_order():
    # 1. 设置测试用户
    test_user = CurrentUser(
        id="test-user",
        permissions=["orders:create"],
        roles=["user"],
    )
    SecurityContext.set_user(test_user)
    SecurityContext.set_tenant("test-tenant")

    # 2. 执行测试
    handler = CreateOrderHandler(mock_uow)
    result = await handler.execute(command)

    # 3. 验证
    assert result is not None

    # 4. 清理
    SecurityContext.clear()
```

### 集成测试

```python
from fastapi.testclient import TestClient

def test_create_order_api():
    client = TestClient(app)

    # 使用测试 token
    response = client.post(
        "/api/v1/orders",
        json={"customer_id": "123", "items": [...]},
        headers={
            "Authorization": "Bearer test-token",
            "X-Tenant-ID": "test-tenant",
        }
    )

    assert response.status_code == 201
```

## 最佳实践

### 1. 使用 SecurityContext，不使用 request.state

```python
# ❌ 不推荐
tenant_id = request.state.tenant_id

# ✅ 推荐
from bento.security import SecurityContext
tenant_id = SecurityContext.get_tenant()
```

**原因**:
- `SecurityContext` 是 async-safe 的 (ContextVar)
- 不依赖 request 对象
- 统一的 API，易于测试

### 2. 在 Handler 中使用，不在 API 层

```python
# ✅ 推荐：在 Handler 中
class CreateOrderHandler(CommandHandler):
    async def handle(self, command):
        user = SecurityContext.require_user()
        # 业务逻辑
        ...

# ❌ 不推荐：在 API 层传递
@router.post("/orders")
async def create_order(request: Request, command: CreateOrderCommand):
    user_id = request.state.user_id  # 不要这样做
    ...
```

### 3. 使用 require_* 明确要求

```python
# ✅ 明确要求认证
user = SecurityContext.require_user()  # 未认证会抛异常

# ✅ 明确要求租户
tenant_id = SecurityContext.require_tenant()  # 无租户会抛异常

# ⚠️ 可选的认证
user = SecurityContext.get_user()  # 可能为 None
if user:
    # 已认证
else:
    # 未认证
```

### 4. 租户隔离在 Repository 层

```python
# ✅ 推荐：在查询时添加租户过滤
class ListOrdersHandler(QueryHandler):
    async def handle(self, query):
        tenant_id = SecurityContext.require_tenant()

        spec = (
            EntitySpecificationBuilder()
            .where("tenant_id", "=", tenant_id)  # 租户隔离
            .build()
        )

        return await repo.find_all(spec)
```

### 5. 渐进式升级

```python
# P0: Stub (开发)
authenticator = StubAuthenticator()

# P1: JWT (生产)
authenticator = JWTAuthenticator(jwks_url="...", audience="...")

# P2: bento-security (企业级)
from bento_security.providers import LogtoAuthProvider
authenticator = LogtoAuthProvider(endpoint="...", app_id="...")

# 业务代码不需要改变！
add_security_middleware(app, authenticator)
```

## 总结

### Bento Framework 的设计哲学

**提供机制，不提供策略**

| 层级 | 职责 | 内容 |
|------|------|------|
| **Framework** | 提供机制 | 接口、上下文、装饰器 |
| **Application** | 提供策略 | 具体的认证/授权实现 |
| **Business** | 使用机制 | SecurityContext.require_user() |

### 关键优势

1. ✅ **灵活性** - 应用可选择任何认证方案
2. ✅ **可测试性** - Mock-friendly 设计
3. ✅ **渐进式** - 从 Stub 到生产的平滑升级
4. ✅ **统一 API** - 业务代码不依赖具体实现
5. ✅ **类型安全** - 完整的类型注解
6. ✅ **框架纯粹** - 不依赖外部认证库

### 升级路径

```
P0: Stub 实现
  ↓ (业务代码不变)
P1: JWT/OAuth 认证
  ↓ (业务代码不变)
P2: bento-security (企业级)
  ↓ (业务代码不变)
P3: 自定义方案
```

**这就是 Framework 设计的精髓：提供机制，让应用选择策略！** 🎉
