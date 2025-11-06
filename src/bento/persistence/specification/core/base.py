"""Core interfaces and base classes for the specification pattern.

This module defines the core interfaces and base classes that form the foundation
of the specification pattern implementation. It provides:

1. Base Specification Protocol (Port)
2. Composite Specification implementation
3. Type-safe query building
4. Support for complex logical combinations
5. Rich query operations

Key components:
- Specification: Base Protocol for all specifications (Domain Port)
- CompositeSpecification: Implementation that combines multiple conditions
- Support for filters, groups, sorting, and pagination
- Statistical operations and field selection
- Relation loading and aggregation
"""

from typing import Any, TypeVar

from bento.domain.ports.specification import Specification as ISpecification

from .types import (
    Filter,
    FilterGroup,
    Having,
    LogicalOperator,
    Page,
    Sort,
    Statistic,
)

T = TypeVar("T")


class CompositeSpecification[T: Any](ISpecification[T]):
    """Composite specification that combines multiple filters and conditions.

    This class implements the Specification Protocol and provides:
    1. Support for multiple filter conditions
    2. Logical grouping of conditions (AND/OR)
    3. Sorting and pagination
    4. Field selection and relation loading
    5. Statistical operations and aggregation

    Example:
        ```python
        from bento.persistence.specification import CompositeSpecification, Filter, FilterOperator

        spec = CompositeSpecification(
            filters=[
                Filter(field="status", operator=FilterOperator.EQUALS, value="active"),
                Filter(field="age", operator=FilterOperator.GREATER_EQUAL, value=18)
            ],
            sorts=[Sort(field="created_at", direction=SortDirection.DESC)],
            page=PageParams(page=1, size=10)
        )
        ```
    """

    __slots__ = (
        "_filters",
        "_groups",
        "_sorts",
        "_page",
        "_fields",
        "_includes",
        "_statistics",
        "_group_by",
        "_having",
        "_joins",
    )

    def __init__(
        self,
        *,
        filters: list[Filter] | None = None,
        groups: list[FilterGroup] | None = None,
        sorts: list[Sort] | None = None,
        page: Page | None = None,
        fields: list[str] | None = None,
        includes: list[str] | None = None,
        statistics: list[Statistic] | None = None,
        group_by: list[str] | None = None,
        having: list[Having] | None = None,
        joins: list[dict[str, Any]] | None = None,
    ) -> None:
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
        self._filters = tuple(filters) if filters else ()
        self._groups = tuple(groups) if groups else ()
        self._sorts = tuple(sorts) if sorts else ()
        self._page = page
        self._fields = tuple(fields) if fields else ()
        self._includes = tuple(includes) if includes else ()
        self._statistics = tuple(statistics) if statistics else ()
        self._group_by = tuple(group_by) if group_by else ()
        self._having = tuple(having) if having else ()
        self._joins = tuple(joins) if joins else ()

    @property
    def filters(self) -> tuple[Filter, ...]:
        """Get filter conditions."""
        return self._filters

    @property
    def groups(self) -> tuple[FilterGroup, ...]:
        """Get filter groups."""
        return self._groups

    @property
    def sorts(self) -> tuple[Sort, ...]:
        """Get sort conditions."""
        return self._sorts

    @property
    def page(self) -> Page | None:
        """Get pagination parameters."""
        return self._page

    @property
    def fields(self) -> tuple[str, ...]:
        """Get selected fields."""
        return self._fields

    @property
    def includes(self) -> tuple[str, ...]:
        """Get relations to load."""
        return self._includes

    @property
    def statistics(self) -> tuple[Statistic, ...]:
        """Get statistical operations."""
        return self._statistics

    @property
    def group_by(self) -> tuple[str, ...]:
        """Get grouping fields."""
        return self._group_by

    @property
    def having(self) -> tuple[Having, ...]:
        """Get having conditions."""
        return self._having

    @property
    def joins(self) -> tuple[dict[str, Any], ...]:
        """Get relation joins."""
        return self._joins

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
        for filter_ in self._filters:
            value = getattr(candidate, filter_.field, None)
            if not self._check_filter(value, filter_):
                return False

        # Group filter checking
        for group in self._groups:
            if not self._check_group(candidate, group):
                return False

        return True

    def _check_filter(self, value: Any, filter_: Filter) -> bool:
        """Check if a value satisfies a filter condition.

        Args:
            value: Value to check
            filter_: Filter condition to apply

        Returns:
            True if the condition is satisfied, False otherwise
        """
        from .types import FilterOperator

        op = filter_.operator
        target = filter_.value

        match op:
            case FilterOperator.EQUALS:
                return value == target
            case FilterOperator.NOT_EQUALS:
                return value != target
            case FilterOperator.GREATER_THAN:
                return value > target
            case FilterOperator.GREATER_EQUAL:
                return value >= target
            case FilterOperator.LESS_THAN:
                return value < target
            case FilterOperator.LESS_EQUAL:
                return value <= target
            case FilterOperator.IN:
                return value in target
            case FilterOperator.NOT_IN:
                return value not in target
            case FilterOperator.IS_NULL:
                return value is None
            case FilterOperator.IS_NOT_NULL:
                return value is not None
            case _:
                return False

    def _check_group(self, candidate: T, group: FilterGroup) -> bool:
        """Check if a candidate satisfies a filter group.

        Args:
            candidate: Object to check
            group: Filter group to apply

        Returns:
            True if the group conditions are satisfied, False otherwise
        """
        results = [self._check_filter(getattr(candidate, f.field, None), f) for f in group.filters]

        if group.operator == LogicalOperator.AND:
            return all(results)
        elif group.operator == LogicalOperator.OR:
            return any(results)
        return False

    def to_query_params(self) -> dict[str, Any]:
        """Convert the specification to query parameters.

        Returns:
            Dictionary containing all query parameters organized by type
        """
        params: dict[str, Any] = {}

        if self._filters:
            params["filters"] = list(self._filters)

        if self._groups:
            params["groups"] = list(self._groups)

        if self._sorts:
            params["sorts"] = list(self._sorts)

        if self._page:
            params["page"] = self._page

        if self._fields:
            params["fields"] = list(self._fields)

        if self._includes:
            params["includes"] = list(self._includes)

        if self._statistics:
            params["statistics"] = list(self._statistics)

        if self._group_by:
            params["group_by"] = list(self._group_by)

        if self._having:
            params["having"] = list(self._having)

        if self._joins:
            params["joins"] = list(self._joins)

        return params

    def with_filters(self, filters: list[Filter]) -> "CompositeSpecification[T]":
        """Create a new specification with additional filters.

        Args:
            filters: Filters to add

        Returns:
            New CompositeSpecification with combined filters
        """
        return CompositeSpecification(
            filters=list(self._filters) + filters,
            groups=list(self._groups),
            sorts=list(self._sorts),
            page=self._page,
            fields=list(self._fields),
            includes=list(self._includes),
            statistics=list(self._statistics),
            group_by=list(self._group_by),
            having=list(self._having),
            joins=list(self._joins),
        )

    def with_sorts(self, sorts: list[Sort]) -> "CompositeSpecification[T]":
        """Create a new specification with sorting.

        Args:
            sorts: Sort conditions to apply

        Returns:
            New CompositeSpecification with sorting
        """
        return CompositeSpecification(
            filters=list(self._filters),
            groups=list(self._groups),
            sorts=sorts,
            page=self._page,
            fields=list(self._fields),
            includes=list(self._includes),
            statistics=list(self._statistics),
            group_by=list(self._group_by),
            having=list(self._having),
            joins=list(self._joins),
        )

    def with_page(self, page: Page) -> "CompositeSpecification[T]":
        """Create a new specification with pagination.

        Args:
            page: Pagination parameters

        Returns:
            New CompositeSpecification with pagination
        """
        return CompositeSpecification(
            filters=list(self._filters),
            groups=list(self._groups),
            sorts=list(self._sorts),
            page=page,
            fields=list(self._fields),
            includes=list(self._includes),
            statistics=list(self._statistics),
            group_by=list(self._group_by),
            having=list(self._having),
            joins=list(self._joins),
        )

    def and_(self, other: "CompositeSpecification[T]") -> "CompositeSpecification[T]":
        """Combine with another specification using AND logic."""
        return CompositeSpecification(
            filters=list(self._filters) + list(other._filters),
            groups=list(self._groups) + list(other._groups),
            sorts=list(self._sorts) or list(other._sorts),
            page=self._page or other._page,
            fields=list(self._fields) or list(other._fields),
            includes=list(self._includes) + list(other._includes),
            statistics=list(self._statistics) + list(other._statistics),
            group_by=list(self._group_by) or list(other._group_by),
            having=list(self._having) + list(other._having),
            joins=list(self._joins) + list(other._joins),
        )

    def or_(self, other: "CompositeSpecification[T]") -> "CompositeSpecification[T]":
        """Combine with another specification using OR logic."""
        from .types import FilterGroup, LogicalOperator

        combined_filters = list(self._filters) + list(other._filters)
        return CompositeSpecification(
            filters=None,
            groups=list(self._groups)
            + list(other._groups)
            + [FilterGroup(filters=tuple(combined_filters), operator=LogicalOperator.OR)]
            if combined_filters
            else list(self._groups) + list(other._groups),
            sorts=list(self._sorts) or list(other._sorts),
            page=self._page or other._page,
            fields=list(self._fields) or list(other._fields),
            includes=list(self._includes) + list(other._includes),
            statistics=list(self._statistics) + list(other._statistics),
            group_by=list(self._group_by) or list(other._group_by),
            having=list(self._having) + list(other._having),
            joins=list(self._joins) + list(other._joins),
        )

    def not_(self) -> "CompositeSpecification[T]":
        """Negate this specification."""
        raise NotImplementedError("NOT operation not yet supported for CompositeSpecification")
