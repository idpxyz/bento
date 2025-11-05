"""Specification builders.

This package provides builder classes for constructing specifications in a fluent
and type-safe way. Each builder is designed for a specific use case and provides
relevant methods for building queries.

Available builders:
- SpecificationBuilder: Base builder with common query operations
- EntitySpecificationBuilder: Builder for entity-specific queries
- AggregateSpecificationBuilder: Builder for aggregate root queries

Example:
    ```python
    # Basic specification builder
    spec = (SpecificationBuilder()
        .text_search("name", "John")
        .add_sort("created_at", ascending=False)
        .set_page(offset=0, limit=10)
        .build())
    
    # Entity specification builder
    spec = (EntitySpecificationBuilder()
        .is_active()
        .created_after(days_ago=7)
        .by_tenant(tenant_id)
        .build())
    
    # Aggregate specification builder
    spec = (AggregateSpecificationBuilder()
        .by_version(1)
        .has_uncommitted_events()
        .by_type("user")
        .build())
    
    # Complex logical combinations
    spec = (SpecificationBuilder()
        .and_(
            lambda b: b.by_id(user_id),
            lambda b: b.or_(
                lambda b: b.text_search("name", "John"),
                lambda b: b.text_search("email", "john@example.com")
            )
        )
        .not_()
        .build())
    ```
"""

from .base import SpecificationBuilder
from .entity import EntitySpecificationBuilder
from .aggregate import AggregateSpecificationBuilder

__all__ = [
    'SpecificationBuilder',
    'EntitySpecificationBuilder',
    'AggregateSpecificationBuilder',
] 