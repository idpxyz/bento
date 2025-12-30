# LOMS Authentication & Authorization

## 架构设计

遵循 **Bento Framework 的最佳实践**：提供机制，不提供策略。

```
┌─────────────────────────────────────────────────────────┐
│  LOMS Application (应用层)                              │
│  - 选择具体的认证/授权实现                               │
│  - 注入到 Bento Framework                               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Bento Framework (框架层)                               │
│  - 定义接口 (IAuthenticator, ITenantResolver)           │
│  - 提供机制 (SecurityContext, Middleware)               │
│  - 不依赖具体实现                                        │
└─────────────────────────────────────────────────────────┘
```

## 当前实现 (P0 Stub)

### 1. StubAuthenticator

**位置**: `stub_authenticator.py`

**职责**:
- 开发/测试阶段的临时认证
- 接受所有请求为已认证
- 返回 demo 用户（全权限）

**使用**:
```python
from loms.shared.platform.auth import StubAuthenticator

authenticator = StubAuthenticator()
user = await authenticator.authenticate(request)
# user.id = "demo-user"
# user.permissions = ["*"]
```

### 2. StubTenantResolver

**位置**: `stub_tenant_resolver.py`

**职责**:
- 从 `X-Tenant-ID` header 提取租户 ID
- 如果没有提供，使用 "demo-tenant"

**使用**:
```python
from loms.shared.platform.auth import StubTenantResolver

resolver = StubTenantResolver()
tenant_id = await resolver.resolve_tenant(request)
# tenant_id = "demo-tenant" or header value
```

## 集成到应用

### 方式 1: 使用 Bento Security Middleware (推荐)

```python
# loms/runtime/bootstrap.py
from fastapi import FastAPI
from bento.security import add_security_middleware, SecurityContext
from loms.shared.platform.auth import StubAuthenticator, StubTenantResolver

def create_app():
    app = FastAPI()

    # 1. 添加 Security Middleware
    add_security_middleware(
        app,
        authenticator=StubAuthenticator(),
        tenant_resolver=StubTenantResolver(),  # 可选
        require_auth=False,  # P0: 不强制认证
        exclude_paths=["/health", "/docs"],
    )

    return app

# 在业务代码中使用
from bento.security import SecurityContext

async def create_order(order_data):
    # 自动从 context 获取
    user = SecurityContext.get_user()  # 可能为 None
    tenant_id = SecurityContext.get_tenant()  # 可能为 None

    # 或者强制要求
    user = SecurityContext.require_user()  # 如果未认证会抛异常
    tenant_id = SecurityContext.require_tenant()  # 如果无租户会抛异常
```

### 方式 2: 自定义 Middleware (当前方式)

```python
# loms/shared/platform/auth/tenant_context.py
from fastapi import Request
from bento.security import SecurityContext
from loms.shared.platform.auth import StubAuthenticator, StubTenantResolver

async def security_middleware(request: Request, call_next):
    # 1. 认证
    authenticator = StubAuthenticator()
    user = await authenticator.authenticate(request)
    SecurityContext.set_user(user)

    # 2. 租户解析
    resolver = StubTenantResolver()
    tenant_id = await resolver.resolve_tenant(request)
    SecurityContext.set_tenant(tenant_id)

    # 3. 设置到 request.state (向后兼容)
    request.state.tenant_id = tenant_id

    response = await call_next(request)

    # 4. 清理 context
    SecurityContext.clear()

    return response
```

## 未来升级路径

### 升级到 bento-security (企业级)

```bash
pip install bento-security[fastapi]
```

```python
# 只需替换 Authenticator，其他代码不变！
from bento_security.providers import LogtoAuthProvider

authenticator = LogtoAuthProvider(
    endpoint="https://your-app.logto.app",
    app_id="app-id",
    app_secret="app-secret",  # M2M 支持
)

add_security_middleware(app, authenticator)
```

### 升级到自定义 JWT 认证

```python
from loms.shared.platform.auth import JWTAuthenticator

authenticator = JWTAuthenticator(
    jwks_url="https://your-auth.com/.well-known/jwks.json",
    audience="loms-api",
)

add_security_middleware(app, authenticator)
```

### 升级到 OAuth2

```python
from loms.shared.platform.auth import OAuth2Authenticator

authenticator = OAuth2Authenticator(
    authorization_url="https://auth.com/oauth/authorize",
    token_url="https://auth.com/oauth/token",
    client_id="loms-client",
    client_secret="secret",
)

add_security_middleware(app, authenticator)
```

## 关键优势

### 1. 符合 Bento Framework 设计原则

✅ **依赖抽象，不依赖具体实现**
- 应用层依赖 `IAuthenticator` 接口
- 不依赖 `StubAuthenticator` 具体类
- 可随时替换实现

✅ **提供机制，不提供策略**
- Framework 提供 `SecurityContext`、`Middleware`
- 应用提供 `StubAuthenticator`、`JWTAuthenticator`
- 清晰的职责分离

✅ **渐进式增强**
- P0: Stub 实现（快速开发）
- P1: JWT 认证（生产就绪）
- P2: bento-security（企业级）

### 2. 易于测试

```python
# 测试时注入 Mock
from bento.security import SecurityContext, CurrentUser

async def test_create_order():
    # 设置测试用户
    test_user = CurrentUser(
        id="test-user",
        permissions=["orders:create"],
    )
    SecurityContext.set_user(test_user)
    SecurityContext.set_tenant("test-tenant")

    # 测试业务逻辑
    result = await create_order(order_data)

    assert result is not None
```

### 3. 统一的 API

无论使用哪种认证方式，业务代码都一样：

```python
# 业务代码永远不变
user = SecurityContext.require_user()
tenant_id = SecurityContext.require_tenant()

# 只需替换 Authenticator 实现
# StubAuthenticator → JWTAuthenticator → LogtoAuthProvider
```

## 最佳实践

### 1. 使用 SecurityContext 而不是 request.state

```python
# ❌ 不推荐：直接访问 request.state
tenant_id = request.state.tenant_id

# ✅ 推荐：使用 SecurityContext
from bento.security import SecurityContext
tenant_id = SecurityContext.get_tenant()
```

**原因**:
- `SecurityContext` 是 async-safe 的 (ContextVar)
- 不依赖 request 对象（可在任何地方使用）
- 统一的 API，易于测试

### 2. 在 Handler 中使用，不在 API 层

```python
# ✅ 推荐：在 Handler 中使用
class CreateOrderHandler(CommandHandler):
    async def handle(self, command):
        user = SecurityContext.require_user()
        tenant_id = SecurityContext.require_tenant()

        order = Order.create(
            customer_id=command.customer_id,
            created_by=user.id,
            tenant_id=tenant_id,
        )
        ...

# ❌ 不推荐：在 API 层传递
@router.post("/orders")
async def create_order(
    request: Request,
    command: CreateOrderCommand,
):
    # 不要在这里访问 SecurityContext
    # 让 Handler 自己处理
    ...
```

### 3. 使用 require_* 方法明确要求

```python
# ✅ 明确要求认证
user = SecurityContext.require_user()  # 未认证会抛异常

# ✅ 明确要求租户
tenant_id = SecurityContext.require_tenant()  # 无租户会抛异常

# ⚠️ 可选的认证
user = SecurityContext.get_user()  # 可能为 None
if user:
    # 已认证的逻辑
else:
    # 未认证的逻辑
```

## 总结

**LOMS 的认证/授权实现完全符合 Bento Framework 的最佳实践**：

1. ✅ **依赖抽象** - 使用 `IAuthenticator`/`ITenantResolver` 接口
2. ✅ **提供机制** - Framework 提供 `SecurityContext`
3. ✅ **应用策略** - LOMS 提供 `StubAuthenticator`
4. ✅ **易于替换** - 可随时升级到真实认证
5. ✅ **统一 API** - 业务代码不需要改变
6. ✅ **易于测试** - Mock-friendly 设计

**这就是 Framework 设计的精髓：提供机制，不提供策略！** 🎉
