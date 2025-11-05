"""Specification pattern implementation for Bento Framework.

This module provides a comprehensive implementation of the Specification pattern
for building type-safe, composable, and reusable query conditions.

## Core Components

### Types and Core Classes
- **Filter**: Represents a single filter condition
- **FilterGroup**: Groups multiple filters with logical operators
- **Sort**: Represents sorting conditions
- **PageParams**: Pagination parameters
- **Page**: Paginated result container
- **CompositeSpecification**: Main specification implementation

### Criteria
Type-safe query condition builders:
- **Comparison**: Equality, inequality, range comparisons
- **Text**: LIKE, ILIKE, contains, regex
- **Null checks**: IS NULL, IS NOT NULL
- **Collections**: IN, NOT IN
- **Arrays**: Contains, overlaps, empty checks
- **JSON**: JSON path operations
- **Temporal**: Date/time range queries
- **Logical**: AND, OR combinations

### Builders
Fluent API for building specifications:
- **SpecificationBuilder**: Base builder with fluent interface
- **EntitySpecificationBuilder**: Entity-specific query patterns
- **AggregateSpecificationBuilder**: Aggregate root patterns

## Usage Example

```python
from bento.persistence.specification import (
    EntitySpecificationBuilder,
    Filter,
    FilterOperator,
    CompositeSpecification,
)

# Using builder (recommended)
spec = (EntitySpecificationBuilder()
    .is_active()
    .created_in_last_days(30)
    .order_by("created_at", "desc")
    .paginate(page=1, size=20)
    .build())

# Using specification directly
spec = CompositeSpecification(
    filters=[
        Filter(field="status", operator=FilterOperator.EQUALS, value="active"),
        Filter(field="age", operator=FilterOperator.GREATER_EQUAL, value=18),
    ],
    sorts=[Sort(field="created_at", direction=SortDirection.DESC)],
    page=PageParams(page=1, size=20)
)

# Using criteria
from bento.persistence.specification.criteria import And, Equals, GreaterEqual

criterion = And(
    Equals("status", "active"),
    GreaterEqual("age", 18)
)
```

## Architecture

This implementation follows Bento's hexagonal architecture:
- Implements the `Specification` Protocol from `domain.ports`
- Provides persistence-layer query building
- Type-safe and composable
- Supports complex queries with minimal code
"""

# Core types and classes
# Criteria (import sub-module for users who want it)
from . import criteria

# Builders
from .builder import (
    AggregateSpecificationBuilder,
    EntitySpecificationBuilder,
    SpecificationBuilder,
)
from .core import (
    CompositeSpecification,
    Filter,
    FilterGroup,
    FilterOperator,
    Having,
    LogicalOperator,
    Page,
    PageParams,
    Sort,
    SortDirection,
    Statistic,
    StatisticalFunction,
)

__all__ = [
    # Core
    "CompositeSpecification",
    "Filter",
    "FilterGroup",
    "FilterOperator",
    "LogicalOperator",
    "Sort",
    "SortDirection",
    "PageParams",
    "Page",
    "Statistic",
    "StatisticalFunction",
    "Having",
    # Builders
    "SpecificationBuilder",
    "EntitySpecificationBuilder",
    "AggregateSpecificationBuilder",
    # Criteria module
    "criteria",
]
