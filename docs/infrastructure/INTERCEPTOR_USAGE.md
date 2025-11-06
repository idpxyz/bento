# Interceptor System Usage Guide

The Interceptor system provides a powerful way to handle cross-cutting concerns in your persistence layer using the Chain of Responsibility pattern.

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Standard Interceptors](#standard-interceptors)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Custom Interceptors](#custom-interceptors)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

The Interceptor system allows you to intercept and modify database operations without modifying your core business logic. It's particularly useful for:

- **Auditing**: Automatic tracking of created/updated timestamps and actors
- **Soft Delete**: Logical deletion instead of physical deletion
- **Optimistic Locking**: Preventing concurrent update conflicts
- **Logging**: Tracking database operations
- **Validation**: Enforcing business rules
- **Caching**: Automatic cache management

### Architecture

```
┌─────────────────┐
│ Repository      │
├─────────────────┤
│ ┌─────────────┐ │
│ │Interceptor 1│ │  (Priority: HIGH)
│ ├─────────────┤ │
│ │Interceptor 2│ │  (Priority: NORMAL)
│ ├─────────────┤ │
│ │Interceptor 3│ │  (Priority: NORMAL)
│ └─────────────┘ │
└─────────────────┘
        ↓
   Database
```

---

## Core Concepts

### 1. Interceptor

Base class for all interceptors. Provides hooks for:
- `before_operation`: Execute logic before database operation
- `after_operation`: Execute logic after database operation
- `process_result`: Process operation result
- `on_error`: Handle errors

### 2. InterceptorChain

Manages execution of multiple interceptors in priority order.

### 3. Priority

Interceptors execute in priority order (lower number = higher priority):
- **HIGHEST** (50): Critical operations
- **HIGH** (100): Core functionality (e.g., optimistic locking)
- **NORMAL** (200): Regular functionality (e.g., audit, soft delete)
- **LOW** (300): Optional functionality
- **LOWEST** (400): Secondary functionality

### 4. InterceptorContext

Contains all contextual information during execution:
- Session
- Entity type
- Operation type (CREATE, UPDATE, DELETE, etc.)
- Entity/entities
- Actor
- Custom context data

---

## Standard Interceptors

### AuditInterceptor

Automatically maintains audit fields:

```python
class MyEntity:
    id: str
    name: str
    created_at: datetime  # Auto-set on CREATE
    created_by: str       # Auto-set on CREATE
    updated_at: datetime  # Auto-set on CREATE/UPDATE
    updated_by: str       # Auto-set on CREATE/UPDATE
```

**Priority**: NORMAL (200)

### SoftDeleteInterceptor

Converts DELETE operations to soft deletes:

```python
class MyEntity:
    id: str
    name: str
    is_deleted: bool      # Set to True on DELETE
    deleted_at: datetime  # Set to current time on DELETE
    deleted_by: str       # Set to actor on DELETE
```

**Priority**: NORMAL (200)

### OptimisticLockInterceptor

Implements version-based concurrency control:

```python
class MyEntity:
    id: str
    name: str
    version: int  # Incremented on each UPDATE
```

Raises `OptimisticLockException` if version mismatch detected.

**Priority**: HIGH (100)

---

## Quick Start

### Basic Usage

```python
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession

# Create repository with default interceptor chain
base_repo = BaseRepository(
    session=session,
    po_type=UserPO,
    actor="admin@example.com",
    interceptor_chain=create_default_chain("admin@example.com"),
)

# All operations now automatically apply interceptors
user_po = UserPO(id="user-001", name="John")
await base_repo.create_po(user_po)  # ← Audit fields auto-populated

# Update with optimistic lock check
user_po.name = "Jane"
await base_repo.update_po(user_po)  # ← Version incremented, updated_at set

# Soft delete
await base_repo.delete_po(user_po)  # ← Marked as deleted, not removed
```

### With RepositoryAdapter

```python
from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.interceptor import create_default_chain

class UserRepository(RepositoryAdapter[User, UserPO, str]):
    def __init__(self, session: AsyncSession, actor: str = "system"):
        # Create base repository with interceptors
        base_repo = BaseRepository(
            session=session,
            po_type=UserPO,
            actor=actor,
            interceptor_chain=create_default_chain(actor),
        )

        # Initialize adapter
        mapper = UserPOMapper()
        super().__init__(repository=base_repo, mapper=mapper)

# Usage
repo = UserRepository(session, actor="admin@example.com")
user = User(id="user-001", name="John")
await repo.save(user)  # ← All interceptors applied automatically
```

---

## Configuration

### InterceptorConfig

Control which interceptors are enabled:

```python
from bento.persistence.interceptor import InterceptorConfig, InterceptorFactory

# Custom configuration
config = InterceptorConfig(
    enable_audit=True,
    enable_soft_delete=True,
    enable_optimistic_lock=False,  # Disable optimistic locking
    actor="system",
)

factory = InterceptorFactory(config)
chain = factory.build_chain()
```

### Selective Interceptor Chains

Build chains with specific interceptors:

```python
factory = InterceptorFactory(config)

# Only audit
audit_chain = factory.build_audit_chain()

# Only soft delete
soft_delete_chain = factory.build_soft_delete_chain()

# Only optimistic lock
lock_chain = factory.build_optimistic_lock_chain()

# All standard interceptors
full_chain = factory.build_chain()
```

### Custom Field Names

Configure custom field names via EntityMetadataRegistry:

```python
from bento.persistence.interceptor import EntityMetadataRegistry

# Custom audit field names
EntityMetadataRegistry.register(
    UserPO,
    fields={
        "audit_fields": {
            "created_at": "creation_time",
            "created_by": "creator",
            "updated_at": "modification_time",
            "updated_by": "modifier",
        }
    },
)

# Custom soft delete field names
EntityMetadataRegistry.register(
    ProductPO,
    fields={
        "soft_delete_fields": {
            "is_deleted": "is_archived",
            "deleted_at": "archived_at",
            "deleted_by": "archiver",
        }
    },
)

# Custom version field name
EntityMetadataRegistry.register(
    OrderPO,
    version_field="revision",  # Use 'revision' instead of 'version'
)
```

---

## Custom Interceptors

### Creating a Custom Interceptor

```python
from bento.persistence.interceptor import (
    Interceptor,
    InterceptorContext,
    InterceptorPriority,
    OperationType,
)
from collections.abc import Awaitable, Callable
import logging

class LoggingInterceptor(Interceptor[T]):
    """Logs all database operations."""

    interceptor_type = "logging"

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @property
    def priority(self) -> InterceptorPriority:
        return InterceptorPriority.LOW  # Low priority

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]],
    ) -> Any:
        """Log before operation."""
        self.logger.info(
            f"Operation: {context.operation.name}, "
            f"Entity: {context.entity_type.__name__}, "
            f"Actor: {context.actor}"
        )
        return await next_interceptor(context)

    async def after_operation(
        self,
        context: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[InterceptorContext[T], Any], Awaitable[Any]],
    ) -> Any:
        """Log after operation."""
        self.logger.info(f"Operation {context.operation.name} completed")
        return await next_interceptor(context, result)
```

### Using Custom Interceptors

```python
from bento.persistence.interceptor import InterceptorFactory

# Create custom interceptor
logger = logging.getLogger(__name__)
logging_interceptor = LoggingInterceptor(logger)

# Add to factory
config = InterceptorConfig(actor="admin@example.com")
factory = InterceptorFactory(config)

# Build chain with additional interceptors
chain = factory.build_chain(additional_interceptors=[logging_interceptor])

# Or create fully custom chain
custom_chain = factory.create_custom_chain([
    logging_interceptor,
    AuditInterceptor(actor="admin@example.com"),
])
```

---

## Best Practices

### 1. Choose Appropriate Priorities

```python
# Critical operations: HIGHEST
class TransactionInterceptor(Interceptor):
    @property
    def priority(self):
        return InterceptorPriority.HIGHEST  # Execute first

# Core functionality: HIGH
class OptimisticLockInterceptor(Interceptor):
    @property
    def priority(self):
        return InterceptorPriority.HIGH  # Before audit

# Regular functionality: NORMAL
class AuditInterceptor(Interceptor):
    @property
    def priority(self):
        return InterceptorPriority.NORMAL

# Logging/metrics: LOW
class MetricsInterceptor(Interceptor):
    @property
    def priority(self):
        return InterceptorPriority.LOW  # Execute last
```

### 2. Use Context Data for Communication

```python
class CachingInterceptor(Interceptor):
    async def before_operation(self, context, next_interceptor):
        # Store data for later use
        context.set_context_value("cache_key", f"{context.entity_type.__name__}:{context.entity.id}")
        return await next_interceptor(context)

    async def after_operation(self, context, result, next_interceptor):
        # Retrieve stored data
        cache_key = context.get_context_value("cache_key")
        await self.cache.set(cache_key, result)
        return await next_interceptor(context, result)
```

### 3. Handle Batch Operations Efficiently

```python
class BatchOptimizedInterceptor(Interceptor):
    async def process_batch_results(
        self,
        context: InterceptorContext[T],
        results: list[T],
        next_interceptor,
    ) -> list[T]:
        """Override for batch-optimized processing."""
        # Process all results in one operation
        ids = [r.id for r in results]
        await self.bulk_process(ids)

        return await next_interceptor(context, results)
```

### 4. Fail Gracefully

```python
class ResilientInterceptor(Interceptor):
    async def on_error(self, context, error, next_interceptor):
        """Handle errors gracefully."""
        if isinstance(error, TransientError):
            # Log and swallow transient errors
            self.logger.warning(f"Transient error: {error}")
            return None  # Swallow error

        # Propagate other errors
        return await next_interceptor(context, error)
```

### 5. Don't Mix Concerns

❌ **Bad**: One interceptor doing too much
```python
class GodInterceptor(Interceptor):
    """Anti-pattern: does auditing, caching, logging, validation..."""
    pass
```

✅ **Good**: Separate concerns
```python
class AuditInterceptor(Interceptor):
    """Only handles auditing"""
    pass

class CachingInterceptor(Interceptor):
    """Only handles caching"""
    pass
```

---

## Examples

### Example 1: Basic Audit and Soft Delete

```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from bento.persistence.repository.sqlalchemy import BaseRepository
from bento.persistence.interceptor import create_default_chain

# Define entity with audit and soft delete fields
class UserPO(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)

    # Audit fields
    created_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String, nullable=True)

    # Soft delete fields
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String, nullable=True)

# Create repository
async def create_user_repository(session: AsyncSession, actor: str):
    return BaseRepository(
        session=session,
        po_type=UserPO,
        actor=actor,
        interceptor_chain=create_default_chain(actor),
    )

# Usage
async def main():
    repo = await create_user_repository(session, "admin@example.com")

    # Create - audit fields auto-populated
    user = UserPO(id="user-001", name="John", email="john@example.com")
    await repo.create_po(user)
    print(f"Created at: {user.created_at}")  # Auto-set
    print(f"Created by: {user.created_by}")  # "admin@example.com"

    # Update - updated_at/updated_by auto-set
    user.name = "Jane"
    await repo.update_po(user)
    print(f"Updated at: {user.updated_at}")  # Auto-set

    # Delete - soft delete
    await repo.delete_po(user)
    print(f"Is deleted: {user.is_deleted}")  # True
    print(f"Deleted at: {user.deleted_at}")  # Auto-set
```

### Example 2: Optimistic Locking

```python
from bento.persistence.interceptor import OptimisticLockException

class ProductPO(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    version = Column(Integer, default=0)  # Version field

# Usage
async def update_product_price(session: AsyncSession):
    repo = BaseRepository(
        session=session,
        po_type=ProductPO,
        actor="system",
        interceptor_chain=create_default_chain("system"),
    )

    # Load product (version = 5)
    product = await repo.get_po_by_id("prod-001")
    print(f"Version: {product.version}")  # 5

    # Concurrent update happens here (version becomes 6)

    try:
        # Attempt to update
        product.price = 2000
        await repo.update_po(product)  # Version incremented to 7
    except OptimisticLockException as e:
        print(f"Conflict detected: {e}")
        # Handle conflict (retry, merge, etc.)
```

### Example 3: Custom Validation Interceptor

```python
class ValidationInterceptor(Interceptor):
    """Validates entities before database operations."""

    @property
    def priority(self):
        return InterceptorPriority.HIGH  # Validate early

    async def before_operation(self, context, next_interceptor):
        if context.operation in (OperationType.CREATE, OperationType.UPDATE):
            await self._validate_entity(context.entity)
        return await next_interceptor(context)

    async def _validate_entity(self, entity):
        if hasattr(entity, 'email'):
            if not '@' in entity.email:
                raise ValueError(f"Invalid email: {entity.email}")

        if hasattr(entity, 'age'):
            if entity.age < 0:
                raise ValueError(f"Invalid age: {entity.age}")

# Usage
validator = ValidationInterceptor()
config = InterceptorConfig(actor="system")
factory = InterceptorFactory(config)
chain = factory.build_chain(additional_interceptors=[validator])

repo = BaseRepository(
    session=session,
    po_type=UserPO,
    actor="system",
    interceptor_chain=chain,
)
```

### Example 4: Selective Interceptors per Entity

```python
from bento.persistence.interceptor import EntityMetadataRegistry

# Disable soft delete for certain entities
EntityMetadataRegistry.register(
    LogPO,
    features={
        "audit": True,
        "soft_delete": False,  # Logs should be hard deleted
        "optimistic_lock": False,
    }
)

# Enable all for user entities
EntityMetadataRegistry.register(
    UserPO,
    features={
        "audit": True,
        "soft_delete": True,
        "optimistic_lock": True,
    }
)

# Interceptors will respect these settings automatically
```

---

## Troubleshooting

### Issue: Audit fields not being set

**Cause**: Entity doesn't have the required fields.

**Solution**: Ensure entity has `created_at`, `created_by`, `updated_at`, `updated_by` fields, or configure custom field names.

```python
# Add fields to entity
class UserPO(Base):
    created_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)
    # ... other audit fields

# Or configure custom names
EntityMetadataRegistry.register(
    UserPO,
    fields={"audit_fields": {"created_at": "creation_time"}}
)
```

### Issue: OptimisticLockException on every update

**Cause**: Version field not being loaded or saved properly.

**Solution**: Ensure version field is included in queries and properly mapped.

```python
# Make sure version is loaded
product = await session.get(ProductPO, product_id)
print(product.version)  # Should have a value

# Don't manually set version
product.version = 10  # ❌ Don't do this
# Let interceptor manage it automatically
```

### Issue: Soft delete not working

**Cause**: Entity doesn't have `is_deleted` field.

**Solution**: Add soft delete fields to entity.

```python
class MyEntity(Base):
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String, nullable=True)
```

---

## Performance Considerations

### 1. Interceptor Overhead

Interceptors add minimal overhead. Benchmarks:
- Empty chain: ~0.1ms
- Full chain (3 interceptors): ~0.5ms

### 2. Batch Operations

Use batch operations for better performance:

```python
# ✅ Good: Batch operation
users = [UserPO(...) for _ in range(100)]
await repo.batch_po_create(users)  # Interceptors applied to all

# ❌ Avoid: Individual operations in loop
for user in users:
    await repo.create_po(user)  # Slower
```

### 3. Conditional Interceptors

Disable interceptors when not needed:

```python
# For bulk imports where audit isn't needed
config = InterceptorConfig(
    enable_audit=False,  # Skip audit for performance
    enable_soft_delete=False,
    enable_optimistic_lock=False,
)
```

---

## Testing

### Testing with Interceptors

```python
import pytest
from bento.persistence.interceptor import create_default_chain

@pytest.mark.asyncio
async def test_user_creation_with_audit(session):
    repo = BaseRepository(
        session=session,
        po_type=UserPO,
        actor="test@example.com",
        interceptor_chain=create_default_chain("test@example.com"),
    )

    user = UserPO(id="test-001", name="Test User")
    await repo.create_po(user)

    # Verify audit fields were set
    assert user.created_at is not None
    assert user.created_by == "test@example.com"
    assert user.updated_at is not None
```

### Mocking Interceptors

```python
# Test without interceptors
repo = BaseRepository(
    session=session,
    po_type=UserPO,
    actor="test@example.com",
    interceptor_chain=None,  # No interceptors
)
```

---

## Summary

The Interceptor system provides:

✅ **Separation of Concerns**: Cross-cutting logic separated from business logic
✅ **Flexibility**: Enable/disable interceptors per entity or globally
✅ **Extensibility**: Easy to create custom interceptors
✅ **Performance**: Minimal overhead, batch-optimized
✅ **Testability**: Can be enabled/disabled for testing

For more examples, see:
- `/examples/interceptor_example.py`
- `/tests/integration/test_interceptor_sqlalchemy.py`

For API reference, see:
- `/src/bento/persistence/interceptor/`

