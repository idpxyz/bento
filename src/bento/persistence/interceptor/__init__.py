"""Interceptor pattern implementation for cross-cutting concerns.

This module provides a comprehensive interceptor system for handling cross-cutting
concerns in persistence operations, such as:
- Auditing (automatic timestamps and user tracking)
- Soft deletion (logical vs physical deletion)
- Optimistic locking (concurrency control)
- Caching
- Logging
- Transaction management
- Outbox pattern

## Architecture

The interceptor system follows the Chain of Responsibility pattern with these components:

### Core Components
- **Interceptor**: Base class for all interceptors
- **InterceptorChain**: Manages execution of multiple interceptors
- **InterceptorContext**: Execution context with operation details
- **EntityMetadataRegistry**: Entity-specific configuration

### Standard Implementations
- **AuditInterceptor**: Automatic timestamp and user tracking
- **SoftDeleteInterceptor**: Logical deletion
- **OptimisticLockInterceptor**: Version-based concurrency control

### Factory
- **InterceptorFactory**: Creates and configures interceptor chains
- **InterceptorConfig**: Configuration for standard interceptors

## Usage Example

```python
from bento.persistence.interceptor import (
    InterceptorFactory,
    InterceptorConfig,
    EntityMetadataRegistry,
)

# Configure entity metadata
EntityMetadataRegistry.register(
    UserEntity,
    features={"audit": True, "soft_delete": True},
    fields={
        "audit_fields": {
            "created_at": "creation_time",
            "updated_at": "modification_time"
        }
    }
)

# Create interceptor chain
config = InterceptorConfig(
    enable_audit=True,
    enable_soft_delete=True,
    enable_optimistic_lock=True,
    actor="user@example.com"
)
factory = InterceptorFactory(config)
chain = factory.build_chain()

# Use in repository operations
context = InterceptorContext(
    session=session,
    entity_type=UserEntity,
    operation=OperationType.CREATE,
    entity=user,
    actor="user@example.com"
)

await chain.execute_before(context)
# ... perform operation ...
result = await chain.execute_after(context, result)
```

## Custom Interceptors

Create custom interceptors by extending the Interceptor base class:

```python
from bento.persistence.interceptor import Interceptor, InterceptorPriority

class CustomInterceptor(Interceptor[T]):
    interceptor_type = "custom"

    @property
    def priority(self):
        return InterceptorPriority.NORMAL

    async def before_operation(self, context, next_interceptor):
        # Custom logic before operation
        return await next_interceptor(context)

    async def after_operation(self, context, result, next_interceptor):
        # Custom logic after operation
        return await next_interceptor(context, result)
```

## Priority System

Interceptors execute in priority order (lower number = higher priority):
- HIGHEST (50): Critical operations (e.g., transactions)
- HIGH (100): Core functionality (e.g., optimistic locking)
- NORMAL (200): Regular functionality (e.g., audit, soft delete)
- LOW (300): Optional functionality (e.g., logging)
- LOWEST (400): Secondary functionality
"""

# Core components
from .core import (
    EntityMetadataRegistry,
    Interceptor,
    InterceptorChain,
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)

# Factory
from .factory import (
    InterceptorConfig,
    InterceptorFactory,
    create_default_chain,
)

# Standard implementations
from .impl import (
    AuditInterceptor,
    OptimisticLockException,
    OptimisticLockInterceptor,
    SoftDeleteInterceptor,
)

__all__ = [
    # Core
    "Interceptor",
    "InterceptorChain",
    "InterceptorContext",
    "InterceptorPriority",
    "OperationType",
    "EntityMetadataRegistry",
    # Standard implementations
    "AuditInterceptor",
    "SoftDeleteInterceptor",
    "OptimisticLockInterceptor",
    "OptimisticLockException",
    # Factory
    "InterceptorFactory",
    "InterceptorConfig",
    "create_default_chain",
]
