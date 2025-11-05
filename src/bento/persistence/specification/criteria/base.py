"""Base criteria interfaces and classes.

This module provides the foundation for building type-safe, composable query criteria.
Criteria are higher-level abstractions that convert to Filters.
"""

from abc import ABC, abstractmethod

from ..core import Filter, FilterGroup, LogicalOperator


class Criterion(ABC):
    """Base interface for all criteria.

    Criteria represent query conditions in a type-safe, composable manner.
    They can be converted to Filters for use in Specifications.
    """

    @abstractmethod
    def to_filter(self) -> Filter:
        """Convert criterion to a filter.

        Returns:
            Filter instance representing this criterion
        """
        ...


class CompositeCriterion(Criterion):
    """Base class for composite criteria combining multiple conditions.

    This class allows combining multiple criteria with logical operators (AND/OR).
    """

    __slots__ = ("_criteria", "_operator")

    def __init__(self, criteria: list[Criterion], operator: LogicalOperator) -> None:
        """Initialize composite criterion.

        Args:
            criteria: List of criteria to combine
            operator: Logical operator to combine criteria with (AND/OR)
        """
        if not criteria:
            raise ValueError("CompositeCriterion must have at least one criterion")
        self._criteria = tuple(criteria)
        self._operator = operator

    def to_filter(self) -> Filter:
        """Convert the first criterion to a filter.

        Note: Use to_filter_group() for proper composite behavior.
        """
        return self._criteria[0].to_filter()

    def to_filter_group(self) -> FilterGroup:
        """Convert composite criterion to a filter group.

        Returns:
            FilterGroup containing all child criteria filters
        """
        return FilterGroup(
            filters=tuple(c.to_filter() for c in self._criteria),
            operator=self._operator,
        )


class AndCriterion(CompositeCriterion):
    """Criterion that combines multiple criteria with AND logic."""

    def __init__(self, *criteria: Criterion) -> None:
        """Initialize AND criterion.

        Args:
            *criteria: Variable number of criteria to combine with AND
        """
        super().__init__(list(criteria), LogicalOperator.AND)


class OrCriterion(CompositeCriterion):
    """Criterion that combines multiple criteria with OR logic."""

    def __init__(self, *criteria: Criterion) -> None:
        """Initialize OR criterion.

        Args:
            *criteria: Variable number of criteria to combine with OR
        """
        super().__init__(list(criteria), LogicalOperator.OR)
