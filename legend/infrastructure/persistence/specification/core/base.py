"""
Core interfaces and base classes for the specification pattern.

This module defines the core interfaces and base classes that form the foundation
of the specification pattern implementation. It provides:

1. Base Specification interface
2. Composite Specification implementation
3. Type-safe query building
4. Support for complex logical combinations
5. Rich query operations

Key components:
- Specification: Base interface for all specifications
- CompositeSpecification: Implementation that combines multiple conditions
- Support for filters, groups, sorting, and pagination
- Statistical operations and field selection
- Relation loading and aggregation
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from .type import (
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
    Page,
    Sort,
    SortList,
    Statistic,
    StatisticalFunction,
    StatisticList,
)

T = TypeVar('T')


class Specification(Generic[T], ABC):
    """Base specification interface.

    This interface defines the core contract for all specifications.
    It provides methods for:
    1. Checking if an object satisfies the specification
    2. Converting the specification to query parameters

    The specification pattern allows for:
    - Encapsulating complex query logic
    - Reusing query conditions
    - Composing complex queries from simple ones
    - Separating query logic from data access
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if the candidate satisfies this specification.

        Args:
            candidate: Object to check against the specification

        Returns:
            True if the candidate satisfies all conditions, False otherwise
        """
        pass

    @abstractmethod
    def to_query_params(self) -> Dict[str, Any]:
        """Convert the specification to query parameters.

        Returns:
            Dictionary containing all query parameters including:
            - filters: List of basic filter conditions
            - groups: List of filter groups with logical operators
            - sorts: List of sort conditions
            - page: Pagination parameters
            - fields: Selected fields
            - includes: Related entities to load
            - statistics: Statistical operations
            - group_by: Grouping fields
            - having: Having conditions
        """
        pass

    def with_type(self, target_type: type) -> 'Specification[Any]':
        """Convert the specification to target type.

        This method allows converting a specification from one type to another
        while preserving all the query conditions. This is particularly useful
        when converting between domain and persistence layer specifications.

        Args:
            target_type: The target type to convert to

        Returns:
            A new specification instance with the target type
        """
        return self  # Default implementation returns self, subclasses can override


class CompositeSpecification(Specification[T]):
    """Composite specification that combines multiple filters and conditions.

    This class implements the Specification interface and provides:
    1. Support for multiple filter conditions
    2. Logical grouping of conditions (AND/OR/NOT)
    3. Sorting and pagination
    4. Field selection and relation loading
    5. Statistical operations and aggregation

    Example:
        ```python
        spec = CompositeSpecification(
            filters=[
                Filter(field="status", operator=FilterOperator.EQUALS, value="active"),
                Filter(field="age", operator=FilterOperator.GREATER_EQUAL, value=18)
            ],
            groups=[
                FilterGroup(
                    operator=LogicalOperator.OR,
                    filters=[
                        Filter(field="type", operator=FilterOperator.EQUALS, value="admin"),
                        Filter(field="type", operator=FilterOperator.EQUALS, value="superuser")
                    ]
                )
            ],
            sorts=[Sort(field="created_at", ascending=False)],
            page=Page(offset=0, limit=10)
        )
        ```
    """

    def __init__(
        self,
        filters: Optional[FilterList] = None,
        groups: Optional[GroupList] = None,
        sorts: Optional[SortList] = None,
        page: Optional[Page] = None,
        fields: Optional[FieldList] = None,
        includes: Optional[List[str]] = None,
        statistics: Optional[StatisticList] = None,
        group_by: Optional[FieldList] = None,
        having: Optional[HavingList] = None,
        joins: Optional[List[dict]] = None
    ):
        """Initialize the composite specification.

        Args:
            filters: Basic filter conditions
            groups: Filter groups with logical operators
            sorts: Sort conditions
            page: Pagination parameters
            fields: Fields to select
            includes: Relations to load
            statistics: Statistical operations
            group_by: Fields to group by
            having: Having conditions
            joins: Relation joins
        """
        self.filters = filters or []
        self.groups = groups or []
        self.sorts = sorts or []
        self.page = page
        self.fields = fields
        self.includes = includes
        self.statistics = statistics
        self.group_by = group_by
        self.having = having
        self.joins = joins or []

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if the candidate satisfies all filters and conditions.

        This implementation provides basic filter checking. For complex
        scenarios, consider overriding this method in a subclass.

        Args:
            candidate: Object to check against the specification

        Returns:
            True if the candidate satisfies all conditions, False otherwise
        """
        # Basic filter checking
        for filter_ in self.filters:
            value = getattr(candidate, filter_.field, None)
            if not self._check_filter(value, filter_.operator, filter_.value):
                return False

        # Group filter checking
        for group in self.groups:
            if not self._check_group(candidate, group):
                return False

        return True

    def _check_filter(self, value: Any, operator: FilterOperator, target: Any) -> bool:
        """Check if a value satisfies a filter condition.

        Args:
            value: Value to check
            operator: Comparison operator
            target: Value to compare against

        Returns:
            True if the condition is satisfied, False otherwise
        """
        if operator == FilterOperator.EQUALS:
            return value == target
        elif operator == FilterOperator.NOT_EQUALS:
            return value != target
        elif operator == FilterOperator.GREATER_THAN:
            return value > target
        elif operator == FilterOperator.GREATER_EQUAL:
            return value >= target
        elif operator == FilterOperator.LESS_THAN:
            return value < target
        elif operator == FilterOperator.LESS_EQUAL:
            return value <= target
        elif operator == FilterOperator.IN:
            return value in target
        elif operator == FilterOperator.NOT_IN:
            return value not in target
        # Add more operators as needed
        return False

    def _check_group(self, candidate: T, group: FilterGroup) -> bool:
        """Check if a candidate satisfies a filter group.

        Args:
            candidate: Object to check
            group: Filter group to apply

        Returns:
            True if the group conditions are satisfied, False otherwise
        """
        results = []
        for filter_ in group.filters:
            value = getattr(candidate, filter_.field, None)
            results.append(self._check_filter(
                value, filter_.operator, filter_.value))

        if group.operator == LogicalOperator.AND:
            return all(results)
        elif group.operator == LogicalOperator.OR:
            return any(results)
        elif group.operator == LogicalOperator.NOT:
            return not any(results)
        return False

    def to_query_params(self) -> Dict[str, Any]:
        """Convert the specification to query parameters.

        Returns:
            Dictionary containing all query parameters organized by type
        """
        params = {}

        if self.filters:
            params['filters'] = self.filters

        if self.groups:
            params['groups'] = self.groups

        if self.sorts:
            params['sorts'] = self.sorts

        if self.page:
            params['page'] = self.page

        if self.fields:
            params['fields'] = self.fields

        if self.includes:
            params['includes'] = self.includes

        if self.statistics:
            params['statistics'] = self.statistics

        if self.group_by:
            params['group_by'] = self.group_by

        if self.having:
            params['having'] = self.having

        if self.joins:
            params['joins'] = self.joins

        return params

    def with_type(self, target_type: type) -> 'CompositeSpecification[Any]':
        """Convert the specification to target type.

        Creates a new CompositeSpecification instance with the target type
        while preserving all query conditions and parameters.

        Args:
            target_type: The target type to convert to

        Returns:
            A new CompositeSpecification instance with the target type
        """
        return CompositeSpecification[Any](
            filters=self.filters.copy() if self.filters else None,
            groups=self.groups.copy() if self.groups else None,
            sorts=self.sorts.copy() if self.sorts else None,
            page=self.page,  # Page is immutable, no need to copy
            fields=self.fields.copy() if self.fields else None,
            includes=self.includes.copy() if self.includes else None,
            statistics=self.statistics.copy() if self.statistics else None,
            group_by=self.group_by.copy() if self.group_by else None,
            having=self.having.copy() if self.having else None,
            joins=self.joins.copy() if self.joins else None
        )
