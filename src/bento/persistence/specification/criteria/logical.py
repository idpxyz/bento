"""Logical combination criteria for building complex queries.

This module provides criteria for combining multiple conditions with logical operators.
"""

from ..core import FilterGroup
from .base import AndCriterion, CompositeCriterion, Criterion, OrCriterion

__all__ = [
    "And",
    "Or",
    "to_filter_group",
]


def And(*criteria: Criterion) -> AndCriterion:
    """Combine multiple criteria with AND logic.

    Args:
        *criteria: Variable number of criteria to combine

    Returns:
        AndCriterion combining all provided criteria

    Example:
        ```python
        from bento.persistence.specification.criteria import And, Equals

        # status = 'active' AND age >= 18
        criterion = And(
            Equals("status", "active"),
            GreaterEqual("age", 18)
        )
        ```
    """
    return AndCriterion(*criteria)


def Or(*criteria: Criterion) -> OrCriterion:
    """Combine multiple criteria with OR logic.

    Args:
        *criteria: Variable number of criteria to combine

    Returns:
        OrCriterion combining all provided criteria

    Example:
        ```python
        from bento.persistence.specification.criteria import Or, Equals

        # role = 'admin' OR role = 'superuser'
        criterion = Or(
            Equals("role", "admin"),
            Equals("role", "superuser")
        )
        ```
    """
    return OrCriterion(*criteria)


def to_filter_group(criterion: CompositeCriterion) -> FilterGroup:
    """Convert a composite criterion to a filter group.

    This is a convenience function for converting composite criteria
    (And/Or) into FilterGroup objects suitable for Specifications.

    Args:
        criterion: CompositeCriterion to convert

    Returns:
        FilterGroup with the appropriate logical operator

    Example:
        ```python
        from bento.persistence.specification.criteria import And, Equals, to_filter_group

        criterion = And(
            Equals("status", "active"),
            Equals("verified", True)
        )

        # Convert to FilterGroup for use in Specification
        filter_group = to_filter_group(criterion)
        spec = CompositeSpecification(groups=[filter_group])
        ```
    """
    return criterion.to_filter_group()
