"""Query criteria implementations.

This package provides various criteria implementations for the specification pattern.
Each criterion represents a specific type of query condition that can be combined
to create complex queries.

Available criteria types:
- Base criteria (Criterion, CompositeCriterion)
- Comparison criteria (equals, in, text search, between, etc.)
- Logical criteria (AND, OR, NOT)
- Temporal criteria (date ranges, relative dates)

Example:
    ```python
    # Simple equals criterion
    criterion = EqualsCriterion("status", "active")
    
    # Between criterion
    criterion = BetweenCriterion("age", 18, 30)
    
    # Complex comparison using NOT
    criterion = NotCriterion(EqualsCriterion("status", "deleted"))
    
    # Text search criterion
    criterion = TextSearchCriterion("name", "John", case_sensitive=False)
    
    # Date range criterion
    criterion = DateRangeCriterion(
        "created_at",
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now()
    )
    
    # Complex logical criterion
    criterion = AndCriterion([
        EqualsCriterion("is_active", True),
        NotCriterion(EqualsCriterion("status", "deleted")),
        OrCriterion([
            TextSearchCriterion("name", "John"),
            TextSearchCriterion("email", "john@example.com")
        ])
    ])
    ```
"""

from .base import (
    Criterion,
    CompositeCriterion,
)

from .comparison import (
    ComparisonCriterion,
    EqualsCriterion,
    InCriterion,
    TextSearchCriterion,
    NullCriterion,
    BetweenCriterion,
)

from .logical import (
    AndCriterion,
    OrCriterion,
)

from .temporal import (
    DateRangeCriterion,
    DateCriterion,
    RelativeDateCriterion,
)

__all__ = [
    # Base
    'Criterion',
    'CompositeCriterion',
    
    # Comparison
    'ComparisonCriterion',
    'EqualsCriterion',
    'InCriterion',
    'TextSearchCriterion',
    'NullCriterion',
    'BetweenCriterion',
    
    # Logical
    'AndCriterion',
    'OrCriterion',
    
    # Temporal
    'DateRangeCriterion',
    'DateCriterion',
    'RelativeDateCriterion',
]
