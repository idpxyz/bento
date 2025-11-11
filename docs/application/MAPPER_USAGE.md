Mapper Usage Guide (AutoMapper)
================================

Overview
--------
AutoMapper provides zero/low‑config object mapping between Domain models and Persistence Objects (POs). It is type‑driven, with smart defaults and escape hatches for complex cases. This guide shows how to use it effectively in real projects.

Key capabilities
- Type‑driven inference (no fragile dir() reflection)
- ID/EntityId ↔ str, Enum ↔ str/int conversions
- Optional/Union and Annotated unwrapping
- Child entity mapping with parent key propagation
- Batch helpers for lists
- Overrides for special fields; alias/ignore/only controls
- Strict mode diagnostics and debug logging
- Custom construction via domain_factory/po_factory

When to use
- Mapping between domain aggregates/entities (dataclass or typed classes) and POs (ORM/Pydantic/dataclass)
- Translating external DTOs to domain types and back
- Reducing boilerplate and copy‑paste conversions

Getting started
---------------
Install and import:

```python
from bento.application.mapper import AutoMapper
from bento.application.mapper.base import MappingContext
from bento.core.ids import ID, EntityId
```

Define your domain and PO:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Annotated

class OrderStatus(Enum):
    NEW = "NEW"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    id: ID
    customer_id: EntityId | None
    status: OrderStatus
    annotated_id: Annotated[ID, "primary key"]

@dataclass
class OrderModel:
    id: str
    customer_id: str | None
    status: str
    annotated_id: str
```

Create a mapper:

```python
class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self, *, context: MappingContext | None = None):
        super().__init__(Order, OrderModel, context=context)
```

Usage:

```python
mapper = OrderMapper()
po = mapper.map(Order(id=ID("o-1"), customer_id=None, status=OrderStatus.NEW, annotated_id=ID("o-1")))
assert po.id == "o-1"
assert po.status == "NEW"

domain = mapper.map_reverse(po)
assert isinstance(domain.id, ID)
assert domain.status is OrderStatus.NEW
```

What is auto‑inferred
---------------------
- ID types (ID/EntityId) → str when mapping to PO; str → ID/EntityId on reverse
- Enums → str by default; also supports Enum ↔ int (value) when PO is int
- Optional[T] and Annotated[T, ...] unwrap to inner T automatically
- Simple types (str/int/float/bool/bytes/date/datetime/UUID/Decimal) copied as‑is

Aliases / ignore / only
-----------------------
```python
class ProductMapper(AutoMapper[Product, ProductModel]):
    def __init__(self):
        super().__init__(Product, ProductModel)
        self.alias_field("display_name", "name_text")
        self.ignore_fields("internal_notes")
        # Only map a subset (whitelist)
        # self.only_fields("id", "display_name", "price")
```

Overrides
---------
Use `override_field` to customize conversions for a field:

```python
self.override_field(
    "price",
    to_po=lambda p: str(p),            # Decimal → str
    from_po=lambda v: Decimal(v),      # str → Decimal
)
```

Child entities and parent keys
------------------------------
Register child mappers and optionally propagate parent keys (supports multi‑FK):

```python
class OrderItemMapper(AutoMapper[OrderItem, OrderItemModel]):
    def __init__(self):
        super().__init__(OrderItem, OrderItemModel)

class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self):
        super().__init__(Order, OrderModel)
        self.register_child("items", OrderItemMapper(), parent_keys=["tenant_id", "order_id"])
```

When you call `map(order)`, `items` are mapped automatically (if present). Parent keys are back‑filled onto child POs in a best‑effort manner (tenant_id from context, order_id from parent id, etc.).

Factories for complex construction
----------------------------------
For rich domain models or special PO constructors (Pydantic/ORM), provide factories:

```python
def build_domain(d: dict) -> Order:
    # enforce invariants, use factories, parse values, etc.
    return Order(**d)

def build_po(d: dict) -> OrderModel:
    # Pydantic: OrderModel.model_construct(**d)
    return OrderModel(**d)

class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self):
        super().__init__(Order, OrderModel, domain_factory=build_domain, po_factory=build_po)
```

If factories raise, AutoMapper wraps with contextual TypeError including the target type and provided keys to aid troubleshooting.

Strict mode and debug logging
-----------------------------
- `strict=True`: raise when fields are unmapped or conversions ambiguous (especially after `only_fields`).
- `debug=True`: log mapping decisions (domain_field/type → po_field/type) and child mapping failures.

```python
mapper = OrderMapper()
mapper = OrderMapper()  # or pass flags in subclass __init__
strict_mapper = AutoMapper(Order, OrderModel, strict=True, debug=True)
```

Batch helpers
-------------
```python
pos = mapper.map_list([o1, o2, o3])
domains = mapper.map_reverse_list(pos)          # clears events by default
domains_keep = mapper.map_reverse_list(pos, with_events=False)
```

Error messages and diagnostics
------------------------------
Examples of improved messages you may see in strict/debug modes:
- Unmapped field suggestions: `title -> candidates: name, display_name`
- Type mismatch hints: `status (Enum) → po.status (int). Enable enum_int or override the field`
- Enum value errors: `Invalid OrderStatus: 'PAI'. Allowed values: ['NEW','PAID','CANCELLED']; names: [NEW, PAID, CANCELLED]`
- Factory/constructor failures include target type and provided keys.

Polymorphism tips (patterns)
----------------------------
AutoMapper doesn’t hard‑code polymorphism, but common options are:
1) Discriminator + factory
   - Use `domain_factory/po_factory` to branch on a discriminator (e.g., `kind`) and instantiate the right subtype/PO.
2) Field override per subtype
   - Register a dedicated mapper for each subtype; choose at call‑site.
3) Delegate to child mappers for nested polymorphic parts.

Testing recipes
---------------
Typical assertions:
```python
po = mapper.map(order)
assert po.id == "order-123"
assert po.status == "PAID"
assert po.customer_id is None

domain = mapper.map_reverse(po)
assert isinstance(domain.id, ID)
assert domain.status is OrderStatus.PAID
```

Use `strict=True` in unit tests of new mappings to catch missing fields early. Add `debug=True` temporarily during development to trace mapping decisions.

FAQ
---
Q: My PO needs a non‑standard constructor (e.g., Pydantic).
A: Provide `po_factory` to construct it; AutoMapper fills a dict of values for you.

Q: Some domain objects enforce invariants in factories.
A: Provide `domain_factory` to ensure proper construction; avoid bypassing invariants.

Q: How do I see why a field didn’t map?
A: Set `debug=True`. For stricter enforcement, set `strict=True` and optional `only_fields(...)` whitelist.

Q: Enum is an int in database.
A: If PO field is `int`, AutoMapper uses `enum_int` conversion automatically; otherwise add an override.

Q: A child needs both tenant_id and order_id as parent keys.
A: Register with `parent_keys=["tenant_id","order_id"]`. Tenant/org can also come from `MappingContext`.

Reference
---------
Primary classes:
- `AutoMapper[Domain, PO]`
- `MappingContext` (propagate tenant_id/org_id/actor_id/extra)

Customization APIs:
- `alias_field(domain_field, po_field)`
- `ignore_fields(*names)`
- `only_fields(*names)` (use with `strict=True` to enforce whitelist)
- `override_field(field_name, to_po, from_po)`
- `register_child(field_name, child_mapper, parent_keys=...)`
- `rebuild_mappings()` to re‑analyze after changes

Constructor flags:
- `include_none`, `strict`, `debug`, `map_children_auto`
- `default_id_type`, `id_factory`
- `domain_factory`, `po_factory`
- `context: MappingContext`

That’s it—you now have a robust, type‑aware mapper with safe defaults and powerful escape hatches for the hard cases.


