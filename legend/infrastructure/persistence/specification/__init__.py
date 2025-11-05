"""
Specification pattern implementation.

This package provides a complete implementation of the specification pattern
for building complex queries in a type-safe and maintainable way.

Key Features:
1. Type-safe query building with Pydantic models
2. Support for complex logical combinations (AND/OR/NOT)
3. Rich filtering operations (comparison, text search, array operations)
4. Sorting and pagination
5. Field selection and relation loading
6. Statistical operations and aggregation
7. Extensible architecture

Example Usage:
    ```python
    from idp.domain.persistence.repo.query.spec import (
        SpecificationBuilder,
        FilterOperator,
        LogicalOperator
    )
    
    # Create a specification for active users
    spec = (SpecificationBuilder()
        .filter("status", FilterOperator.EQUALS, "active")
        .filter("age", FilterOperator.GREATER_EQUAL, 18)
        .filter("email", FilterOperator.LIKE, "@example.com")
        .group(LogicalOperator.OR, [
            Filter(field="role", operator=FilterOperator.EQUALS, value="admin"),
            Filter(field="permission_level", operator=FilterOperator.GREATER_EQUAL, value=5)
        ])
        .sort("created_at", ascending=False)
        .page(offset=0, limit=20)
        .select_fields(["id", "name", "email", "role"])
        .include_relations(["profile", "permissions"])
        .add_statistic("total_users", StatisticalFunction.COUNT, "id")
        .add_statistic("avg_score", StatisticalFunction.AVG, "score")
        .group_by(["role"])
        .having("total_users", FilterOperator.GREATER_THAN, 10)
        .build()
    )
    
    # Convert to query parameters
    params = spec.to_query_params()
    
    # Use with repository
    users = await user_repository.find_many(spec)
    ```

For more examples and detailed documentation, see:
1. builder/base.py - Base specification builder
2. criteria/ - Filter criteria implementations
3. core/ - Core interfaces and data types
"""

from .builder import (
    AggregateSpecificationBuilder,
    EntitySpecificationBuilder,
    SpecificationBuilder,
)
from .core import (  # Enums; Data classes; Type aliases; Base classes
    CompositeSpecification,
    ExistsSpec,
    FieldList,
    Filter,
    FilterGroup,
    FilterList,
    FilterOperator,
    FilterValue,
    GroupList,
    Having,
    HavingList,
    LogicalOperator,
    NotExistsSpec,
    Page,
    PageParams,
    Sort,
    SortList,
    Specification,
    Statistic,
    StatisticalFunction,
    StatisticList,
)

__all__ = [
    # Core types
    'FilterOperator',
    'LogicalOperator',
    'StatisticalFunction',
    'Filter',
    'Sort',
    'PageParams'
    'Page',
    'FilterGroup',
    'Statistic',
    'Having',
    'ExistsSpec',
    'NotExistsSpec',
    'FilterValue',
    'SortList',
    'FilterList',
    'GroupList',
    'StatisticList',
    'HavingList',
    'FieldList',
    'Specification',
    'CompositeSpecification',

    # Builders
    'SpecificationBuilder',
    'EntitySpecificationBuilder',
    'AggregateSpecificationBuilder'
]
