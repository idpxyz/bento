# Cascade Operations Usage Guide

The Cascade system provides a powerful way to handle complex aggregate relationships with child entities, automatically managing the lifecycle of child entities when saving aggregate roots.

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [Migration Guide](#migration-guide)

---

## Overview

The Cascade system simplifies the management of complex aggregates with child entities by providing:

- **Automatic Child Management**: No need to manually delete and recreate child entities
- **Type Safety**: Configuration-based approach with compile-time checking
- **Consistent Auditing**: Child entities automatically inherit audit behavior
- **Reduced Boilerplate**: Eliminate repetitive cascade handling code
- **Framework Integration**: Seamless integration with existing Repository patterns

### Problem Statement

Without cascade helpers, managing child entities requires manual code:

```python
# ❌ Manual cascade handling (repetitive, error-prone)
async def save(self, order: Order) -> None:
    await super().save(order)  # Save parent

    # Delete old children
    await self.session.execute(
        delete(OrderItemPO).where(OrderItemPO.order_id == order.id)
    )

    # Create new children
    item_repo = BaseRepository(...)
    for item in order.items:
        item_po = self.item_mapper.map(item)
        await item_repo.create_po(item_po)
```

### Solution

With cascade helpers, this becomes:

```python
# ✅ Declarative cascade handling (simple, maintainable)
class OrderRepository(CascadeMixin, RepositoryAdapter):
    def __init__(self, ...):
        self.cascade_configs = {
            "items": CascadeConfig(
                child_po_type=OrderItemPO,
                child_mapper=self.item_mapper.map,
                foreign_key_field="order_id"
            )
        }

    async def save(self, order: Order) -> None:
        await self.save_with_cascade(order, self.cascade_configs)
```

### Architecture

```
┌─────────────────────────────────┐
│   Aggregate Root (Order)        │
├─────────────────────────────────┤
│  CascadeMixin                   │
│  ├─ save_with_cascade()         │
│  └─ get_cascade_helper()        │
└─────────────────────────────────┘
            ↓
┌─────────────────────────────────┐
│   CascadeHelper                 │
├─────────────────────────────────┤
│  ├─ replace_children()          │
│  │  ├─ Delete old entities      │
│  │  └─ Create new entities      │
│  └─ Uses BaseRepository         │
│     (Audit, Interceptors)       │
└─────────────────────────────────┘
            ↓
┌─────────────────────────────────┐
│   Child Entities (OrderItems)   │
└─────────────────────────────────┘
```

---

## Core Concepts

### Aggregate Cascade

In DDD, an **Aggregate** is a cluster of domain objects treated as a single unit. The **Aggregate Root** (e.g., Order) controls the lifecycle of child entities (e.g., OrderItems).

**Key Principles:**
- Child entities cannot exist without their parent
- Child entities are saved/deleted as part of the aggregate
- External references can only point to the aggregate root

### Cascade Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **delete_and_recreate** | Delete all old children, create new ones | Default, simple, works for most cases |
| **merge** (future) | Smart diff, only update changes | Performance optimization for large collections |

### Components

#### 1. CascadeHelper

Core utility class that performs cascade operations:

```python
helper = CascadeHelper(session, actor)
await helper.replace_children(
    parent_entity=order,
    child_entities=order.items,
    child_po_type=OrderItemPO,
    child_mapper=mapper.map,
    foreign_key_field="order_id"
)
```

#### 2. CascadeMixin

Mixin class that adds cascade support to repositories:

```python
class MyRepository(CascadeMixin, RepositoryAdapter):
    async def save(self, aggregate):
        await self.save_with_cascade(aggregate, self.cascade_configs)
```

#### 3. CascadeConfig

Type-safe configuration for cascade relationships:

```python
config = CascadeConfig(
    child_po_type=OrderItemPO,       # PO class for children
    child_mapper=mapper.map,          # Function to map Entity → PO
    foreign_key_field="order_id"      # FK field in child table
)
```

---

## Quick Start

### Step 1: Import Required Components

```python
from bento.infrastructure.repository import (
    RepositoryAdapter,
    CascadeMixin,
    CascadeConfig
)
```

### Step 2: Define Your Repository

```python
class OrderRepository(CascadeMixin, RepositoryAdapter[Order, OrderPO, ID]):
    """Order Repository with cascade support for OrderItems"""

    def __init__(self, session: AsyncSession, actor: str = "system"):
        # Initialize base repository
        base_repo = BaseRepository(
            session=session,
            po_type=OrderPO,
            actor=actor,
            interceptor_chain=create_default_chain(actor)
        )

        # Initialize mappers
        self.order_mapper = OrderMapper()
        self.item_mapper = OrderItemMapper()

        # Initialize RepositoryAdapter
        super().__init__(repository=base_repo, mapper=self.order_mapper)

        # Store session and actor for CascadeMixin
        self.session = session
        self.actor = actor

        # Configure cascade relationships
        self.cascade_configs = {
            "items": CascadeConfig(
                child_po_type=OrderItemPO,
                child_mapper=self.item_mapper.map,
                foreign_key_field="order_id"
            )
        }
```

### Step 3: Implement Save Method

```python
    async def save(self, order: Order) -> None:
        """Save order with automatic cascade to items"""
        await self.save_with_cascade(order, self.cascade_configs)
        await self.session.flush()
```

### Step 4: Use It

```python
# Application code remains simple
order = Order.create(customer_id="123")
order.add_item(product_id="p1", quantity=2, price=99.99)
order.add_item(product_id="p2", quantity=1, price=49.99)

await order_repository.save(order)  # ✅ Cascades automatically
```

---

## Configuration

### Single Child Collection

```python
self.cascade_configs = {
    "items": CascadeConfig(
        child_po_type=OrderItemPO,
        child_mapper=self.item_mapper.map,
        foreign_key_field="order_id"
    )
}
```

### Multiple Child Collections

```python
self.cascade_configs = {
    "line_items": CascadeConfig(
        child_po_type=LineItemPO,
        child_mapper=self.line_mapper.map,
        foreign_key_field="invoice_id"
    ),
    "attachments": CascadeConfig(
        child_po_type=AttachmentPO,
        child_mapper=self.attachment_mapper.map,
        foreign_key_field="invoice_id"
    )
}
```

### Custom Mapper Function

```python
# Use lambda for inline mapping
"items": CascadeConfig(
    child_po_type=OrderItemPO,
    child_mapper=lambda item: OrderItemPO(
        id=str(item.id),
        product_id=item.product_id,
        quantity=item.quantity,
        price=item.price
    ),
    foreign_key_field="order_id"
)
```

---

## API Reference

### CascadeHelper

```python
class CascadeHelper:
    def __init__(self, session: AsyncSession, actor: str = "system") -> None

    async def replace_children(
        self,
        parent_entity: Any,
        child_entities: List[Any],
        child_po_type: Type[Any],
        child_mapper: Callable[[Any], Any],
        foreign_key_field: str,
    ) -> None
```

### CascadeMixin

```python
class CascadeMixin:
    def get_cascade_helper(self) -> CascadeHelper

    async def save_with_cascade(
        self,
        aggregate: Any,
        cascade_configs: Dict[str, CascadeConfig] | None = None
    ) -> None
```

### CascadeConfig

```python
class CascadeConfig:
    def __init__(
        self,
        child_po_type: Type[Any],
        child_mapper: Callable[[Any], Any],
        foreign_key_field: str,
    ) -> None
```

---

## Best Practices

### 1. Use for Complex Aggregates Only

✅ **DO**: Use cascade helpers for aggregates with child entities
```python
# Order with OrderItems - perfect use case
class OrderRepository(CascadeMixin, RepositoryAdapter):
    cascade_configs = {"items": ...}
```

❌ **DON'T**: Use for simple entities without children
```python
# User entity - no need for cascade
class UserRepository(RepositoryAdapter):  # No mixin needed
    pass
```

### 2. Keep Aggregate Boundaries Small

✅ **DO**: Limit child entities to direct dependencies
```python
# Order → OrderItems (direct relationship)
cascade_configs = {"items": CascadeConfig(...)}
```

❌ **DON'T**: Include distant relationships
```python
# Order → OrderItems → Product (too deep)
# Products should be separate aggregates
```

### 3. Configure in __init__

✅ **DO**: Define cascade configs in constructor
```python
def __init__(self, ...):
    self.cascade_configs = {...}  # Clear, discoverable
```

❌ **DON'T**: Create configs inline
```python
async def save(self, order):
    configs = {...}  # Hard to find, not reusable
    await self.save_with_cascade(order, configs)
```

### 4. Use Type-Safe Mappers

✅ **DO**: Use dedicated mapper classes
```python
child_mapper=self.item_mapper.map  # Type-safe, testable
```

❌ **DON'T**: Use complex lambdas
```python
child_mapper=lambda x: {...}  # Hard to test, error-prone
```

### 5. Handle Transactions Properly

✅ **DO**: Flush after cascade
```python
async def save(self, order):
    await self.save_with_cascade(order, self.cascade_configs)
    await self.session.flush()  # Ensure DB sync
```

---

## Examples

### Example 1: Order with Items

```python
# Domain Models
@dataclass
class Order(AggregateRoot):
    id: ID
    customer_id: str
    items: List[OrderItem] = field(default_factory=list)

    def add_item(self, product_id: str, quantity: int, price: float):
        item = OrderItem(
            id=ID.generate(),
            product_id=product_id,
            quantity=quantity,
            price=price
        )
        self.items.append(item)

@dataclass
class OrderItem:
    id: ID
    product_id: str
    quantity: int
    price: float

# Repository with Cascade
class OrderRepository(CascadeMixin, RepositoryAdapter[Order, OrderPO, ID]):
    def __init__(self, session: AsyncSession, actor: str = "system"):
        # ... initialization ...

        self.cascade_configs = {
            "items": CascadeConfig(
                child_po_type=OrderItemPO,
                child_mapper=self.item_mapper.map,
                foreign_key_field="order_id"
            )
        }

    async def save(self, order: Order) -> None:
        await self.save_with_cascade(order, self.cascade_configs)
        await self.session.flush()

# Usage
async with uow:
    order = Order.create(customer_id="cust-123")
    order.add_item("prod-1", 2, 99.99)
    order.add_item("prod-2", 1, 49.99)

    await order_repo.save(order)
    await uow.commit()
```

### Example 2: Invoice with Line Items and Attachments

```python
class InvoiceRepository(CascadeMixin, RepositoryAdapter):
    def __init__(self, ...):
        self.cascade_configs = {
            "line_items": CascadeConfig(
                child_po_type=LineItemPO,
                child_mapper=self.line_mapper.map,
                foreign_key_field="invoice_id"
            ),
            "attachments": CascadeConfig(
                child_po_type=AttachmentPO,
                child_mapper=self.attachment_mapper.map,
                foreign_key_field="invoice_id"
            )
        }

    async def save(self, invoice: Invoice) -> None:
        await self.save_with_cascade(invoice, self.cascade_configs)
```

---

## Migration Guide

### Migrating Existing Repositories

#### Before (Manual Cascade)

```python
class OrderRepository(RepositoryAdapter[Order, OrderPO, ID]):
    async def save(self, order: Order) -> None:
        # 1. Save parent
        await super().save(order)

        # 2. Delete old children
        await self.session.execute(
            delete(OrderItemPO).where(OrderItemPO.order_id == str(order.id))
        )

        # 3. Create new children
        item_base_repo = BaseRepository(
            session=self.session,
            po_type=OrderItemPO,
            actor=self.actor,
            interceptor_chain=create_default_chain(self.actor),
        )

        for item in order.items:
            item_po = self.item_mapper.map(item)
            await item_base_repo.create_po(item_po)

        await self.session.flush()
```

#### After (With Cascade Helper)

```python
class OrderRepository(CascadeMixin, RepositoryAdapter[Order, OrderPO, ID]):
    def __init__(self, ...):
        # ... existing initialization ...

        # Add cascade configuration
        self.cascade_configs = {
            "items": CascadeConfig(
                child_po_type=OrderItemPO,
                child_mapper=self.item_mapper.map,
                foreign_key_field="order_id"
            )
        }

    async def save(self, order: Order) -> None:
        await self.save_with_cascade(order, self.cascade_configs)
        await self.session.flush()
```

#### Benefits

- **-60% code reduction**: From ~25 lines to ~10 lines
- **Type safety**: Configuration is validated at runtime
- **Consistency**: Framework guarantees correct audit behavior
- **Maintainability**: Configuration is easier to understand and modify

### Backward Compatibility

The cascade system is **completely backward compatible**:

- ✅ Existing repositories continue to work unchanged
- ✅ No breaking changes to existing APIs
- ✅ Optional feature - use only where needed
- ✅ Can be adopted incrementally

---

## Performance Considerations

### Delete and Recreate Strategy

**Pros:**
- Simple and reliable
- Works for all cases
- Easy to understand and debug

**Cons:**
- Not optimal for large collections (>100 items)
- Generates more DB operations

**Recommendation:** Use for most cases (items < 100)

### Future: Merge Strategy

For large collections, a future "merge" strategy will:
- Compare old vs new items
- Only update what changed
- More efficient for large collections

---

## Troubleshooting

### Issue: "CascadeMixin requires 'session' attribute"

**Cause:** Repository class doesn't have a `session` attribute.

**Solution:** Ensure your repository stores the session:
```python
def __init__(self, session, ...):
    super().__init__(...)
    self.session = session  # ← Required for CascadeMixin
```

### Issue: Child entities not saved

**Cause:** Cascade config field name doesn't match aggregate property.

**Solution:** Verify field names match:
```python
# Aggregate has 'items' property
class Order:
    items: List[OrderItem]

# Config must use same name
cascade_configs = {
    "items": CascadeConfig(...)  # ← Must match 'items'
}
```

### Issue: Foreign key constraint violation

**Cause:** Foreign key field name is incorrect.

**Solution:** Check your database schema:
```python
# If OrderItemPO table has 'order_id' column
CascadeConfig(
    foreign_key_field="order_id"  # ← Must match DB column
)
```

---

## See Also

- [Repository Pattern](../design/REPOSITORY_PATTERN.md)
- [Aggregate Design](../design/AGGREGATE_DESIGN.md)
- [Interceptor System](INTERCEPTOR_USAGE.md)
- [Unit of Work](../design/UNIT_OF_WORK.md)
