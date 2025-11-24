# Architecture Documentation

## 📂 Directory Structure

```
my-shop/
├── main.py                    # Application entry point
├── config.py                  # Configuration
│
├── shared/                    # Shared Kernel (cross-context)
│   ├── api/
│   │   └── router_registry.py # Context route registration
│   ├── infrastructure/
│   │   └── dependencies.py    # DI (UoW, Session)
│   └── exceptions/
│       └── handlers.py        # Global exception handling
│
└── contexts/                  # Bounded Contexts
    ├── catalog/              # Product catalog context
    │   ├── domain/
    │   ├── application/
    │   ├── infrastructure/
    │   └── interfaces/
    │       └── __init__.py    # register_routes()
    │
    ├── ordering/             # Order management context
    │   ├── domain/
    │   ├── application/
    │   ├── infrastructure/
    │   └── interfaces/
    │       └── __init__.py    # register_routes()
    │
    └── identity/             # User identity context
        ├── domain/
        ├── application/
        ├── infrastructure/
        └── interfaces/
            └── __init__.py    # register_routes()
```

## 🎯 Design Principles

### Domain-Driven Design (DDD)
- **Bounded Contexts**: Each context is self-contained
- **Ubiquitous Language**: Consistent terminology within each context
- **Aggregates**: Order, Product, User as aggregate roots
- **Domain Events**: OrderCreated, OrderPaid, etc.

### Hexagonal Architecture (Ports & Adapters)
- **Domain Layer**: Pure business logic
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: Technical implementations
- **Interfaces Layer**: Adapters (REST API, CLI, etc.)

## 🔌 Adding a New Context

### Example: Adding a "Shipping" Context

1. **Create context structure**:
```bash
mkdir -p contexts/shipping/{domain,application,infrastructure,interfaces}
```

2. **Implement the context** (domain, application, infrastructure layers)

3. **Create interfaces/__init__.py**:
```python
from fastapi import APIRouter

def register_routes(parent_router: APIRouter) -> None:
    """Register shipping routes."""
    from contexts.shipping.interfaces.shipping_api import router
    parent_router.include_router(router, prefix="/shipping", tags=["shipping"])
```

4. **Register in router registry**:
```python
# shared/api/router_registry.py
REGISTERED_CONTEXTS = [
    "catalog",
    "ordering",
    "identity",
    "shipping",  # ← Add this line
]
```

**That's it!** ✅ No other files need to be modified.

## 📊 Scalability

This architecture is designed to scale:
- ✅ **10+ Contexts**: Configuration-based registration
- ✅ **Multiple Teams**: Each team owns a bounded context
- ✅ **Independent Deployment**: Contexts can evolve separately
- ✅ **Git-Friendly**: Minimal merge conflicts

## 🧪 Testing Strategy

### Unit Tests
- Test domain logic in isolation
- Mock infrastructure dependencies

### Integration Tests
- Test use cases with real database
- Test API endpoints

### End-to-End Tests
- Test complete workflows (create order → pay → ship)

## 🚀 Deployment

Current setup supports:
- **Development**: `uvicorn main:app --reload`
- **Production**: Deploy as single monolith (start here)
- **Future**: Extract contexts as microservices if needed

## 📝 References

- **DDD**: Eric Evans - "Domain-Driven Design"
- **IDDD**: Vaughn Vernon - "Implementing Domain-Driven Design"
- **Hexagonal**: Alistair Cockburn - "Hexagonal Architecture"
- **Bento Framework**: [Documentation](link-to-bento-docs)
