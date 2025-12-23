# Bento Runtime Module

Application bootstrap, module system, and dependency injection for Bento applications.

## Overview

The runtime module combines the best of both worlds:
- **LOMS-style**: Module registry with dependency management
- **my-shop-style**: FastAPI lifespan integration with Bento components

## Quick Start

```python
from bento.runtime import BentoRuntime, BentoModule

# 1. Define modules
class InfraModule(BentoModule):
    name = "infra"

    async def on_register(self, container):
        container.set("db.session_factory", create_session_factory())
        container.set("cache", await create_cache())

class CatalogModule(BentoModule):
    name = "catalog"
    requires = ["infra"]

    async def on_register(self, container):
        session_factory = container.get("db.session_factory")
        container.set("catalog.repo", CategoryRepository(session_factory))

    def get_routers(self):
        from contexts.catalog.interfaces.http import router
        return [router]

# 2. Build runtime
runtime = (
    BentoRuntime()
    .with_config(service_name="my-shop", environment="local")
    .with_contracts("./contracts")
    .with_modules(
        InfraModule(),
        CatalogModule(),
    )
)

# 3. Create FastAPI app
app = runtime.create_fastapi_app(title="My Shop API")
```

## Components

### BentoModule

Base class for application modules.

```python
class BentoModule(ABC):
    name: str = ""           # Module name (auto-derived from class name)
    requires: Sequence[str] = ()  # Dependencies

    async def on_register(self, container): ...   # Register services
    async def on_startup(self, container): ...    # Startup hook
    async def on_shutdown(self, container): ...   # Shutdown hook
    def get_routers(self) -> list[APIRouter]: ... # FastAPI routers
```

### BentoContainer

Simple dependency injection container.

```python
container = BentoContainer()

# Register
container.set("cache", redis_cache)
container.set_factory("db.session", session_factory)  # Lazy

# Retrieve
cache = container.get("cache")
session = container.get("db.session")
```

### ModuleRegistry

Module registry with topological sorting.

```python
registry = ModuleRegistry()
registry.register(InfraModule())
registry.register(CatalogModule())

# Get modules in dependency order
modules = registry.resolve_order()  # [InfraModule, CatalogModule]
```

### BentoRuntime

Main orchestrator combining all components.

```python
runtime = (
    BentoRuntime()
    .with_config(service_name="my-shop")
    .with_contracts("./contracts")
    .with_modules(InfraModule(), CatalogModule())
    .with_service("custom.service", MyService())
)

app = runtime.create_fastapi_app(title="My API")
```

## Features

### ✅ Dependency Management

Modules declare dependencies, automatically sorted:

```python
class OrderingModule(BentoModule):
    name = "ordering"
    requires = ["infra", "catalog"]  # Will be registered after both
```

### ✅ Contract Validation

Startup gates validate contracts before running:

```python
runtime = (
    BentoRuntime()
    .with_contracts("./contracts", require=True)
    ...
)
```

### ✅ Lifecycle Hooks

Full control over startup and shutdown:

```python
class CacheModule(BentoModule):
    async def on_startup(self, container):
        cache = container.get("cache")
        await cache.warmup()

    async def on_shutdown(self, container):
        cache = container.get("cache")
        await cache.close()
```

### ✅ FastAPI Integration

Automatic router collection and lifespan management:

```python
class CatalogModule(BentoModule):
    def get_routers(self):
        return [categories_router, products_router]

# All routers automatically included in app
app = runtime.create_fastapi_app(title="My API")
```

### ✅ Testing Support

Easily mock modules for testing:

```python
class MockInfraModule(BentoModule):
    name = "infra"

    async def on_register(self, container):
        container.set("db.session_factory", mock_session_factory)

runtime = BentoRuntime().with_modules(MockInfraModule(), CatalogModule())
```

## Architecture

```
Application Startup Flow:
┌─────────────────────────────────────────────────────┐
│  1. BentoRuntime.build_async()                      │
│     ├── Run startup gates (contract validation)     │
│     └── Register modules in dependency order        │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  2. FastAPI lifespan (on startup)                   │
│     ├── Run on_startup() for each module            │
│     └── Store runtime in app.state                  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  3. Application running                             │
│     └── Container available via app.state.container │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  4. FastAPI lifespan (on shutdown)                  │
│     └── Run on_shutdown() for each module (reverse) │
└─────────────────────────────────────────────────────┘
```

## Comparison

| Feature | LOMS | my-shop | Bento Runtime |
|---------|------|---------|---------------|
| Module System | ✅ | ❌ | ✅ |
| Dependency Sorting | ✅ | ❌ | ✅ |
| Contract Gates | ✅ | ❌ | ✅ |
| FastAPI Lifespan | ❌ | ✅ | ✅ |
| Bento Components | ❌ | ✅ | ✅ |
| Router Auto-collect | ❌ | ❌ | ✅ |
| Testing Support | ⚠️ | ⚠️ | ✅ |

## Module Structure

```
bento/runtime/
├── __init__.py     # Public exports
├── module.py       # BentoModule base class
├── container.py    # BentoContainer DI
├── registry.py     # ModuleRegistry
└── bootstrap.py    # BentoRuntime orchestrator
```
