# Repository Adapters

This module provides repository adapters that bridge the Domain layer (Aggregate Roots) and the Persistence layer (Persistence Objects).

## Architecture

```
Domain Layer
  └── IRepository Protocol (domain/ports/repository.py)
        ▲
        │ implements
        │
Infrastructure Layer
  ├── RepositoryAdapter     (AR ↔ PO mapping)
  ├── SimpleRepositoryAdapter (AR = PO, no mapping)
  └── InMemoryRepository    (testing)
        ▲
        │ delegates to
        │
Persistence Layer
  └── BaseRepository (PO operations)
```

## Available Adapters

### RepositoryAdapter

Full-featured adapter with AR ↔ PO mapping via Mapper.

```python
from bento.infrastructure.repository import RepositoryAdapter

class ProductRepository(RepositoryAdapter[Product, ProductPO, ID]):
    def __init__(self, session: AsyncSession, actor: str = "system"):
        mapper = ProductMapper()
        base_repo = BaseRepository(session, ProductPO, actor)
        super().__init__(repository=base_repo, mapper=mapper)
```

### SimpleRepositoryAdapter

Simplified adapter for cases where AR = PO (no mapping needed).

```python
from bento.infrastructure.repository import SimpleRepositoryAdapter

class ConfigRepository(SimpleRepositoryAdapter[Config, ID]):
    def __init__(self, session: AsyncSession, actor: str = "system"):
        base_repo = BaseRepository(session, Config, actor)
        super().__init__(repository=base_repo)
```

### InMemoryRepository

In-memory implementation for testing and prototyping.

```python
from bento.infrastructure.repository import InMemoryRepository

class TestProductRepository(InMemoryRepository[Product]):
    pass
```

## Built-in Mixins

Both adapters include powerful mixins for enhanced functionality:

| Mixin | Description |
|-------|-------------|
| `BatchOperationsMixin` | Batch ID operations |
| `UniquenessChecksMixin` | Uniqueness validation |
| `AggregateQueryMixin` | Sum, avg, min, max |
| `SortingLimitingMixin` | Sorting and pagination |
| `ConditionalUpdateMixin` | Bulk update/delete |
| `GroupByQueryMixin` | Group by and aggregation |
| `SoftDeleteEnhancedMixin` | Soft delete queries |
| `RandomSamplingMixin` | Random sampling |
| `TenantFilterMixin` | Multi-tenant support |

## Multi-Tenant Support

Built-in tenant isolation via `TenantFilterMixin` (opt-in).

### Enable Tenant Filtering

```python
class ProductRepository(RepositoryAdapter[Product, ProductPO, ID]):
    tenant_enabled = True  # Enable tenant filtering
    tenant_field = "tenant_id"  # Field name (default)
```

### How It Works

When `tenant_enabled = True`:

1. **Queries**: Automatically add `tenant_id` filter
2. **Save**: Automatically inject `tenant_id` from context
3. **Get**: Validate entity belongs to current tenant

### Usage

```python
from bento.security import TenantContext

# Set tenant context (usually in middleware)
TenantContext.set("tenant-123")

# All operations are now tenant-scoped
products = await repo.find_all()  # Only tenant-123's products
await repo.save(product)          # Auto-sets tenant_id
```

### Disable (Default)

```python
class GlobalConfigRepository(RepositoryAdapter[Config, ConfigPO, ID]):
    tenant_enabled = False  # Default, no filtering
```

## Cascade Support

For complex aggregates with child entities:

```python
from bento.infrastructure.repository import CascadeHelper, CascadeMixin, CascadeConfig

class OrderRepository(CascadeMixin, RepositoryAdapter[Order, OrderPO, ID]):
    cascade_configs = [
        CascadeConfig(
            child_type=OrderItemPO,
            parent_fk="order_id",
            child_attr="items",
        )
    ]
```

## Common Operations

### Basic CRUD

```python
# Get by ID
product = await repo.get(product_id)

# Save (create or update)
await repo.save(product)

# Delete
await repo.delete(product_id)
```

### Queries with Specification

```python
from bento.persistence.specification import EntitySpecificationBuilder

# Build specification
spec = (
    EntitySpecificationBuilder()
    .where("category_id", "=", category_id)
    .where("is_active", "=", True)
    .order_by("name")
    .build()
)

# Query
products = await repo.find_all(spec)
```

### Pagination

```python
# Simple pagination
page = await repo.paginate(spec, page=1, size=20)

# Access results
items = page.items
total = page.total
has_next = page.has_next
```

### Aggregate Queries

```python
# Sum
total = await repo.sum("price", spec)

# Average
avg = await repo.avg("price", spec)

# Count
count = await repo.count(spec)
```

## Best Practices

1. **Use RepositoryAdapter** for complex domain models with separate PO
2. **Use SimpleRepositoryAdapter** for simple entities or MVPs
3. **Enable tenant filtering explicitly** when building multi-tenant apps
4. **Use Specification pattern** for complex queries
5. **Prefer paginate()** over find_all() for large datasets
