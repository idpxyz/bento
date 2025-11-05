"""Base specification builder for fluent query construction.

This module provides a fluent interface for building specifications
with type-safe criteria and a clean, readable API.
"""

from typing import Any, Self, TypeVar

from ..core import (
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
from ..criteria import CompositeCriterion, Criterion

T = TypeVar("T")


class SpecificationBuilder[T]:
    """Base builder for specifications with fluent interface.

    This class provides a fluent, chainable API for building complex
    specifications with criteria, filters, sorts, pagination, etc.

    Example:
        ```python
        spec = (SpecificationBuilder()
            .where("status", "=", "active")
            .where("age", ">=", 18)
            .order_by("created_at", "desc")
            .paginate(page=1, size=20)
            .build())
        ```
    """

    __slots__ = (
        "_criteria",
        "_sorts",
        "_page",
        "_fields",
        "_includes",
        "_statistics",
        "_group_by",
        "_having",
        "_filter_groups",
        "_current_group",
        "_current_group_operator",
        "_joins",
    )

    def __init__(self) -> None:
        """Initialize builder with empty state."""
        self._criteria: list[Criterion] = []
        self._sorts: list[Sort] = []
        self._page: PageParams | None = None
        self._fields: list[str] = []
        self._includes: list[str] = []
        self._statistics: list[Statistic] = []
        self._group_by: list[str] = []
        self._having: list[Having] = []
        self._filter_groups: list[FilterGroup] = []
        self._current_group: list[Filter] | None = None
        self._current_group_operator: LogicalOperator | None = None
        self._joins: list[dict[str, Any]] = []

    def where(self, field: str, operator: str, value: Any = None) -> Self:
        """Add a filter condition using string operators.

        This method allows using intuitive string operators:
        - Comparison: "=", "!=", ">", ">=", "<", "<="
        - Collection: "in", "not in"
        - Null: "is null", "is not null"
        - Text: "like", "ilike", "contains", "starts with", "ends with"
        - Range: "between" (value should be [start, end])

        Args:
            field: Field to filter on
            operator: String operator
            value: Value to compare against (optional for some operators)

        Returns:
            Self for method chaining

        Example:
            ```python
            builder.where("age", ">=", 18)
            builder.where("status", "in", ["active", "pending"])
            builder.where("deleted_at", "is null")
            ```
        """
        op_lower = operator.lower().strip()

        # Handle special cases
        if op_lower in ("is null", "is not null", "array empty", "array not empty"):
            value = None

        # Convert between operator
        if op_lower == "between" and isinstance(value, (list, tuple)) and len(value) == 2:
            value = {"start": value[0], "end": value[1]}

        # Convert string operator to FilterOperator
        # Mapping common operators
        operator_map = {
            "=": FilterOperator.EQUALS,
            "==": FilterOperator.EQUALS,
            "!=": FilterOperator.NOT_EQUALS,
            "<>": FilterOperator.NOT_EQUALS,
            ">": FilterOperator.GREATER_THAN,
            ">=": FilterOperator.GREATER_EQUAL,
            "<": FilterOperator.LESS_THAN,
            "<=": FilterOperator.LESS_EQUAL,
            "in": FilterOperator.IN,
            "not in": FilterOperator.NOT_IN,
            "between": FilterOperator.BETWEEN,
            "is null": FilterOperator.IS_NULL,
            "is not null": FilterOperator.IS_NOT_NULL,
            "like": FilterOperator.LIKE,
            "ilike": FilterOperator.ILIKE,
            "contains": FilterOperator.CONTAINS,
            "starts with": FilterOperator.STARTS_WITH,
            "ends with": FilterOperator.ENDS_WITH,
            "regex": FilterOperator.REGEX,
            "iregex": FilterOperator.IREGEX,
            "array contains": FilterOperator.ARRAY_CONTAINS,
            "array overlaps": FilterOperator.ARRAY_OVERLAPS,
            "array empty": FilterOperator.ARRAY_EMPTY,
            "array not empty": FilterOperator.ARRAY_NOT_EMPTY,
            "json contains": FilterOperator.JSON_CONTAINS,
            "json exists": FilterOperator.JSON_EXISTS,
            "json has key": FilterOperator.JSON_HAS_KEY,
        }

        if op_lower not in operator_map:
            raise ValueError(
                f"Unknown operator: {operator}\nValid operators: {', '.join(operator_map.keys())}"
            )

        filter_op = operator_map[op_lower]
        filter_obj = Filter(field=field, operator=filter_op, value=value)

        # Add to current group or as standalone criterion
        if self._current_group is not None:
            self._current_group.append(filter_obj)
        else:
            # Convert filter to criterion and add
            from ..criteria.comparison import ComparisonCriterion

            self._criteria.append(ComparisonCriterion(field, value, filter_op))

        return self

    def equals(self, field: str, value: Any) -> Self:
        """Shorthand for equality comparison.

        Args:
            field: Field to compare
            value: Value to match

        Returns:
            Self for method chaining
        """
        return self.where(field, "=", value)

    def not_equals(self, field: str, value: Any) -> Self:
        """Shorthand for inequality comparison.

        Args:
            field: Field to compare
            value: Value to exclude

        Returns:
            Self for method chaining
        """
        return self.where(field, "!=", value)

    def greater_than(self, field: str, value: Any) -> Self:
        """Shorthand for greater than comparison.

        Args:
            field: Field to compare
            value: Lower bound (exclusive)

        Returns:
            Self for method chaining
        """
        return self.where(field, ">", value)

    def less_than(self, field: str, value: Any) -> Self:
        """Shorthand for less than comparison.

        Args:
            field: Field to compare
            value: Upper bound (exclusive)

        Returns:
            Self for method chaining
        """
        return self.where(field, "<", value)

    def between(self, field: str, start: Any, end: Any) -> Self:
        """Add BETWEEN range filter.

        Args:
            field: Field to check
            start: Start of range (inclusive)
            end: End of range (inclusive)

        Returns:
            Self for method chaining
        """
        return self.where(field, "between", [start, end])

    def in_list(self, field: str, values: list[Any]) -> Self:
        """Add IN filter for collection membership.

        Args:
            field: Field to check
            values: List of values to match against

        Returns:
            Self for method chaining
        """
        return self.where(field, "in", values)

    def is_null(self, field: str) -> Self:
        """Add IS NULL filter.

        Args:
            field: Field to check for NULL

        Returns:
            Self for method chaining
        """
        return self.where(field, "is null")

    def is_not_null(self, field: str) -> Self:
        """Add IS NOT NULL filter.

        Args:
            field: Field to check for NOT NULL

        Returns:
            Self for method chaining
        """
        return self.where(field, "is not null")

    def contains(self, field: str, text: str) -> Self:
        """Add text contains filter (case-insensitive).

        Args:
            field: Field to search
            text: Text to find

        Returns:
            Self for method chaining
        """
        return self.where(field, "ilike", f"%{text}%")

    def add_criterion(self, criterion: Criterion) -> Self:
        """Add a criterion directly.

        Args:
            criterion: Criterion to add

        Returns:
            Self for method chaining
        """
        if self._current_group is not None:
            self._current_group.append(criterion.to_filter())
        else:
            self._criteria.append(criterion)
        return self

    def group(self, operator: LogicalOperator | str = LogicalOperator.AND) -> Self:
        """Start a new filter group.

        Args:
            operator: Logical operator to combine filters (AND/OR)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If a group is already active

        Example:
            ```python
            builder.group("OR")
                .where("status", "=", "active")
                .where("status", "=", "pending")
                .end_group()
            ```
        """
        if self._current_group is not None:
            raise ValueError("Cannot start a new group while another group is active")

        if isinstance(operator, str):
            operator = LogicalOperator(operator.lower())

        self._current_group = []
        self._current_group_operator = operator
        return self

    def end_group(self) -> Self:
        """End the current filter group.

        Returns:
            Self for method chaining

        Raises:
            ValueError: If no group is currently active
        """
        if self._current_group is None:
            raise ValueError("No active filter group to end")

        if self._current_group and self._current_group_operator:
            self._filter_groups.append(
                FilterGroup(
                    filters=tuple(self._current_group),
                    operator=self._current_group_operator,
                )
            )

        self._current_group = None
        self._current_group_operator = None
        return self

    def order_by(self, field: str, direction: str | SortDirection = SortDirection.ASC) -> Self:
        """Add sorting.

        Args:
            field: Field to sort by
            direction: Sort direction ("asc" or "desc")

        Returns:
            Self for method chaining
        """
        if isinstance(direction, str):
            direction = SortDirection(direction.lower())

        self._sorts.append(Sort(field=field, direction=direction))
        return self

    def paginate(self, page: int = 1, size: int = 10) -> Self:
        """Add pagination.

        Args:
            page: Page number (starting from 1)
            size: Page size (items per page)

        Returns:
            Self for method chaining
        """
        self._page = PageParams(page=page, size=size)
        return self

    def select(self, *fields: str) -> Self:
        """Select specific fields.

        Args:
            *fields: Fields to select

        Returns:
            Self for method chaining
        """
        self._fields.extend(fields)
        return self

    def include(self, *relations: str) -> Self:
        """Include related entities.

        Args:
            *relations: Relation names to include

        Returns:
            Self for method chaining
        """
        self._includes.extend(relations)
        return self

    def group_by(self, *fields: str) -> Self:
        """Group results by fields.

        Args:
            *fields: Fields to group by

        Returns:
            Self for method chaining
        """
        self._group_by.extend(fields)
        return self

    def count(self, field: str = "*", alias: str | None = None) -> Self:
        """Add COUNT statistic.

        Args:
            field: Field to count (default: *)
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        self._statistics.append(
            Statistic(function=StatisticalFunction.COUNT, field=field, alias=alias)
        )
        return self

    def sum(self, field: str, alias: str | None = None) -> Self:
        """Add SUM statistic.

        Args:
            field: Field to sum
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        self._statistics.append(
            Statistic(function=StatisticalFunction.SUM, field=field, alias=alias)
        )
        return self

    def avg(self, field: str, alias: str | None = None) -> Self:
        """Add AVG statistic.

        Args:
            field: Field to average
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        self._statistics.append(
            Statistic(function=StatisticalFunction.AVG, field=field, alias=alias)
        )
        return self

    def build(self) -> CompositeSpecification[T]:
        """Build the final specification.

        Returns:
            CompositeSpecification with all configured criteria

        Raises:
            ValueError: If a filter group is still open
        """
        if self._current_group is not None:
            raise ValueError("Cannot build specification with an open filter group")

        # Convert criteria to filters
        filters = [c.to_filter() for c in self._criteria]

        # Add filter groups from composite criteria
        groups = list(self._filter_groups)
        for criterion in self._criteria:
            if isinstance(criterion, CompositeCriterion):
                groups.append(criterion.to_filter_group())

        # Convert PageParams to Page if present
        page = None
        if self._page:
            page = Page.create(items=[], total=0, page=self._page.page, size=self._page.size)

        return CompositeSpecification(
            filters=filters if filters else None,
            groups=groups if groups else None,
            sorts=self._sorts if self._sorts else None,
            page=page,
            fields=self._fields if self._fields else None,
            includes=self._includes if self._includes else None,
            statistics=self._statistics if self._statistics else None,
            group_by=self._group_by if self._group_by else None,
            having=self._having if self._having else None,
            joins=self._joins if self._joins else None,
        )
