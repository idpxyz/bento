# Security Module

This module provides authentication and authorization utilities for Bento applications.

## Architecture

```
Request
    │
    ▼
┌─────────────────────────────────────┐
│  SecurityMiddleware                 │
│  - Calls IAuthenticator             │
│  - Sets SecurityContext             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  SecurityContext (ContextVar)       │
│  - Async-safe user storage          │
│  - Request-scoped                   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Business Logic                     │
│  - SecurityContext.require_user()   │
│  - SecurityContext.has_permission() │
└─────────────────────────────────────┘
```

## Design Principles

| Principle | Description |
|-----------|-------------|
| **Framework provides mechanisms** | Interfaces, context, utilities |
| **Application provides strategies** | JWT, OAuth, specific implementations |
| **Zero dependencies** | No dependency on specific auth providers |
| **Pluggable** | Applications can replace any component |

## Quick Start

### 1. Implement Authenticator

```python
from bento.security import IAuthenticator, CurrentUser

class JWTAuthenticator(IAuthenticator):
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

### @require_role / @require_any_role

```python
from bento.security import require_role, require_any_role

@require_role("admin")
async def admin_only():
    ...

@require_any_role("admin", "moderator")
async def moderation():
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

## Module Structure

```
bento/security/
├── __init__.py      # Public exports
├── context.py       # SecurityContext
├── models.py        # CurrentUser
├── ports.py         # IAuthenticator, IAuthorizer
├── middleware.py    # FastAPI middleware
└── decorators.py    # Security decorators
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
