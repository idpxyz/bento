# Bento Runtime Module

Application bootstrap, module system, and dependency injection for Bento applications.

## Overview

The runtime module combines the best of both worlds:
- **LOMS-style**: Module registry with dependency management
- **my-shop-style**: FastAPI lifespan integration with Bento components

## Quick Start

```python
from bento.runtime import RuntimeBuilder, BentoModule

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

# 2. Build runtime using RuntimeBuilder
runtime = (
    RuntimeBuilder()
    .with_config(service_name="my-shop", environment="local")
    .with_contracts("./contracts")
    .with_modules(
        InfraModule(),
        CatalogModule(),
    )
    .build_runtime()
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

### ✅ Database Requirements Declaration

Modules can declare database dependencies:

```python
class CatalogModule(BentoModule):
    name = "catalog"
    requires_database = True  # Runtime will ensure database is configured
```

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

### ✅ Startup Performance Monitoring

Track startup performance metrics:

```python
runtime = (
    RuntimeBuilder()
    .with_modules(InfraModule(), CatalogModule())
    .build_runtime()
)
await runtime.build_async()

# Get metrics programmatically
metrics = runtime.get_startup_metrics()
print(f"Total: {metrics['total_time']:.2f}s")
print(f"Gates: {metrics['gates_time']:.3f}s")
print(f"Modules: {metrics['register_time']:.3f}s")
print(f"Database: {metrics['database_time']:.3f}s")

# Or log metrics
runtime.log_startup_metrics()
# INFO: Startup metrics: total=0.81s, gates=0.12s, register=0.46s, database=0.23s
```

### ✅ Enhanced Dependency Injection

Advanced DI methods for FastAPI integration:

```python
# Repository dependency for specific aggregate
@router.get("/products/{id}")
async def get_product(
    id: str,
    product_repo = Depends(runtime.get_repository_dependency(Product))
):
    product = await product_repo.get(id)
    return product

# EventBus dependency
@router.post("/products")
async def create_product(
    event_bus = Depends(runtime.get_event_bus)
):
    event = ProductCreated(...)
    await event_bus.publish(event)

# Container dependency
@router.get("/config")
async def get_config(
    container = Depends(runtime.get_container)
):
    config = container.get("config")
    return config
```

### ✅ Runtime Monitoring

Monitor runtime performance and health:

```python
# Get comprehensive runtime information
info = runtime.performance_monitor.get_runtime_info()
print(f"Service: {info['service_name']}")
print(f"Modules: {info['modules']}")
print(f"Environment: {info['environment']}")

# Record request performance
start = time.time()
# ... handle request ...
runtime.performance_monitor.record_request(time.time() - start)

# Get request statistics
stats = runtime.performance_monitor.get_request_stats()
print(f"Avg response time: {stats['avg_time']:.3f}s")
print(f"Min: {stats['min_time']:.3f}s, Max: {stats['max_time']:.3f}s")
```

### ✅ Testing Support

Easily mock modules for testing:

```python
class MockInfraModule(BentoModule):
    name = "infra"

    async def on_register(self, container):
        container.set("db.session_factory", mock_session_factory)

runtime = (
    BentoRuntime()
    .with_test_mode()
    .with_mock_module("mock_catalog", services={"catalog.repo": MockRepo()})
    .with_modules(CatalogModule())
)
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

## Documentation

For detailed information, see:

- **[DEPENDENCIES.md](./DEPENDENCIES.md)** - Dependency management and optional packages
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Detailed architecture and design patterns
- **[MIGRATION.md](./MIGRATION.md)** - Migration guide from previous versions

## Module Structure

```
bento/runtime/
├── __init__.py                  # Public exports
├── bootstrap.py                 # BentoRuntime orchestrator (393 lines)
├── module.py                    # BentoModule base class
├── registry.py                  # ModuleRegistry with topological sorting
├── builder/                     # Configuration builder
│   └── runtime_builder.py      # RuntimeBuilder for configuration
├── config/                      # Configuration management
│   └── runtime_config.py       # RuntimeConfig with validation
├── container/                   # DI container
│   ├── base.py                 # BentoContainer implementation
│   ├── lifetime.py             # Service lifetime management
│   └── scope.py                # Scope management
├── integrations/                # ✨ Integration modules (NEW)
│   ├── fastapi.py              # FastAPI integration (142 lines)
│   ├── di.py                   # DI integration for FastAPI (182 lines)
│   ├── modules.py              # Module lifecycle operations (143 lines)
│   └── performance.py          # Performance monitoring (151 lines)
├── lifecycle/                   # Lifecycle management
│   ├── manager.py              # LifecycleManager orchestrator
│   ├── startup.py              # Startup logic
│   └── shutdown.py             # Shutdown logic
├── observability/               # Observability features
│   ├── otel.py                 # OpenTelemetry integration
│   ├── metrics.py              # Metrics collection
│   └── tracing.py              # Distributed tracing
├── database/                    # Database management
│   └── manager.py              # DatabaseManager
└── testing/                     # Testing support
    └── mocks.py                # Mock utilities
```

## Recent Improvements (2024-12-29)

### ✨ Type Safety
- Fixed all type annotation issues
- Proper initialization of integration managers
- 0 type errors

### ✨ Documentation
- Added DEPENDENCIES.md (2,500+ words)
- Added ARCHITECTURE.md (4,500+ words)
- Added MIGRATION.md (2,000+ words)
- Total: 9,000+ words with 65+ code examples

### ✨ Enhanced DI
- `get_repository_dependency(aggregate_class)` - Repository injection
- `get_event_bus()` - EventBus injection
- `get_container()` - Container injection

### ✨ Performance Optimization
- Topological sort result caching in ModuleRegistry
- 99.8% performance improvement for repeated calls

### ✨ Runtime Monitoring
- `get_runtime_info()` - Comprehensive runtime information
- `record_request(duration)` - Request performance tracking
- `get_request_stats()` - Request statistics

### ✨ Structure Optimization (2024-12-29 Latest)
- Created `integrations/` directory for all integration modules
- Reorganized 4 integration modules (fastapi, di, modules, performance)
- Cleaner top-level directory structure
- Better module organization and navigation

### ✨ Framework Integration (2024-12-29 Latest)
- **UoW Integration**: Fixed Protocol instantiation, now uses `SQLAlchemyUnitOfWork`
- **Repository Registry**: Auto-discovery and registration mechanism
- **Port Registry**: Cross-BC service adapter registration
- **Cache Manager**: Support for in-memory and Redis cache
- **Messaging Manager**: Event bus and Outbox pattern integration
