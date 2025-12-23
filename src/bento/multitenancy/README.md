# Multi-Tenancy Module

This module provides multi-tenant support for Bento applications, enabling data isolation between tenants.

## Architecture

```
Request
    │
    ▼
┌─────────────────────────────────────┐
│  TenantMiddleware                   │
│  - Resolves tenant from request     │
│  - Sets TenantContext               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  TenantContext (ContextVar)         │
│  - Async-safe tenant storage        │
│  - Request-scoped                   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  TenantFilterMixin (Repository)     │
│  - Auto-filter queries by tenant    │
│  - Auto-inject tenant on save       │
└─────────────────────────────────────┘
```

## Quick Start

### 1. Add Middleware

```python
from fastapi import FastAPI
from bento.multitenancy import add_tenant_middleware, HeaderTenantResolver

app = FastAPI()

add_tenant_middleware(
    app,
    resolver=HeaderTenantResolver(),
    require_tenant=True,
    exclude_paths=["/health", "/docs"],
)
```

### 2. Enable Tenant Filtering in Repository

```python
from bento.infrastructure.repository import RepositoryAdapter

class ProductRepository(RepositoryAdapter[Product, ProductPO, ID]):
    tenant_enabled = True  # Enable tenant filtering
    tenant_field = "tenant_id"  # Field name (default)
```

### 3. Use Normally

```python
# All operations are now tenant-scoped automatically
products = await repo.find_all()  # Only current tenant's products
await repo.save(product)          # Auto-sets tenant_id
```

## Components

### TenantContext

Async-safe storage for current tenant ID using ContextVar.

```python
from bento.multitenancy import TenantContext

# Set (usually in middleware)
TenantContext.set("tenant-123")

# Get (may return None)
tenant_id = TenantContext.get()

# Require (raises TENANT_REQUIRED if not set)
tenant_id = TenantContext.require()

# Clear
TenantContext.clear()
```

### Tenant Resolvers

Strategies for extracting tenant ID from requests.

#### HeaderTenantResolver

```python
from bento.multitenancy import HeaderTenantResolver

resolver = HeaderTenantResolver(header_name="X-Tenant-ID")
# Request with "X-Tenant-ID: tenant-123" -> "tenant-123"
```

#### TokenTenantResolver

```python
from bento.multitenancy import TokenTenantResolver

resolver = TokenTenantResolver(claim_name="tenant_id")
# Reads from request.state.user.metadata or request.state.claims
```

#### SubdomainTenantResolver

```python
from bento.multitenancy import SubdomainTenantResolver

resolver = SubdomainTenantResolver()
# "acme.example.com" -> "acme"
```

#### CompositeTenantResolver

Try multiple resolvers in order.

```python
from bento.multitenancy import CompositeTenantResolver

resolver = CompositeTenantResolver([
    HeaderTenantResolver(),
    TokenTenantResolver(),
    SubdomainTenantResolver(),
])
```

### Middleware

```python
from bento.multitenancy import add_tenant_middleware

add_tenant_middleware(
    app,
    resolver=resolver,
    require_tenant=True,       # Return 400 if missing
    exclude_paths=["/health"], # Skip these paths
)
```

## Repository Integration

The `TenantFilterMixin` is built into `RepositoryAdapter` and `SimpleRepositoryAdapter`.

### Enable (Opt-in)

```python
class ProductRepository(RepositoryAdapter[Product, ProductPO, ID]):
    tenant_enabled = True
```

### Disable (Default)

```python
class GlobalConfigRepository(RepositoryAdapter[Config, ConfigPO, ID]):
    tenant_enabled = False  # Default, no filtering
```

### How It Works

When `tenant_enabled = True`:

| Operation | Behavior |
|-----------|----------|
| `find_all()` | Adds `WHERE tenant_id = ?` |
| `find_page()` | Adds `WHERE tenant_id = ?` |
| `paginate()` | Adds `WHERE tenant_id = ?` |
| `count()` | Adds `WHERE tenant_id = ?` |
| `get()` | Validates entity belongs to tenant |
| `save()` | Auto-sets `tenant_id` if not set |

## Entity Setup

Add `tenant_id` field to your entities:

### Aggregate Root

```python
@dataclass
class Product(AggregateRoot):
    id: ID
    name: str
    tenant_id: str  # Required for multi-tenant
```

### Persistence Object

```python
class ProductPO(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    name = Column(String)
    tenant_id = Column(String, index=True)  # Add index for performance
```

## Error Handling

### TENANT_REQUIRED

Raised when `TenantContext.require()` is called without a tenant set.

```json
{
  "reason_code": "TENANT_REQUIRED",
  "message": "Tenant ID is required for this operation",
  "http_status": 400
}
```

## Best Practices

1. **Always index `tenant_id`** - Critical for query performance
2. **Use HeaderTenantResolver for APIs** - Simple and explicit
3. **Use TokenTenantResolver for JWT-based auth** - Tenant in token
4. **Use SubdomainTenantResolver for SaaS** - `tenant.yourapp.com`
5. **Exclude health/docs paths** - No tenant needed for these
6. **Set tenant early in middleware chain** - Before auth if possible

## Comparison with Other Frameworks

| Framework | Approach | Bento |
|-----------|----------|-------|
| ABP Framework | `IMultiTenant` interface | `tenant_enabled = True` |
| Django Tenants | Schema-based | Row-based (TenantFilterMixin) |
| Spring | `@TenantScope` | `tenant_enabled = True` |

## Module Structure

```
bento/multitenancy/
├── __init__.py      # Public exports
├── context.py       # TenantContext
├── resolvers.py     # TenantResolver strategies
└── middleware.py    # FastAPI middleware
```
