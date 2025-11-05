"""Core types for the specification pattern.

This module defines the core types, enums and data classes used in the specification pattern.
Following Bento's architecture principles and type safety.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel


class FilterOperator(str, Enum):
    """Query filter operators.

    Standard operators:
    - Equality: eq, ne
    - Comparison: gt, ge, lt, le
    - Collection: in, not_in
    - Range: between
    - Null checks: is_null, is_not_null

    Text operators:
    - Pattern matching: like, ilike
    - Contains: contains, not_contains
    - Prefix/Suffix: starts_with, ends_with
    - Regular expression: regex, iregex

    Array operators:
    - Array containment: array_contains
    - Array overlap: array_overlaps
    - Array empty: array_empty
    - Array not empty: array_not_empty

    JSON operators:
    - JSON containment: json_contains
    - JSON exists: json_exists
    - JSON has key: json_has_key
    """

    # Standard operators
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "ge"
    LESS_THAN = "lt"
    LESS_EQUAL = "le"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"

    # Text operators
    LIKE = "like"
    ILIKE = "ilike"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    IREGEX = "iregex"

    # Array operators
    ARRAY_CONTAINS = "array_contains"
    ARRAY_OVERLAPS = "array_overlaps"
    ARRAY_EMPTY = "array_empty"
    ARRAY_NOT_EMPTY = "array_not_empty"

    # JSON operators
    JSON_CONTAINS = "json_contains"
    JSON_EXISTS = "json_exists"
    JSON_HAS_KEY = "json_has_key"


class LogicalOperator(str, Enum):
    """Logical operators for combining filters and specifications."""

    AND = "and"
    OR = "or"


class SortDirection(str, Enum):
    """Sort direction for query results."""

    ASC = "asc"
    DESC = "desc"


class StatisticalFunction(str, Enum):
    """Statistical functions for aggregate queries."""

    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    GROUP_CONCAT = "group_concat"


@dataclass(frozen=True, slots=True)
class Filter:
    """Represents a filter condition in a query.

    Attributes:
        field: Field name to filter on
        operator: Filter operator to apply
        value: Value to compare against
    """

    field: str
    operator: FilterOperator
    value: Any

    def __post_init__(self) -> None:
        """Validate filter attributes after initialization."""
        if not self.field:
            raise ValueError("Filter field cannot be empty")

        # Operator validation
        if not isinstance(self.operator, FilterOperator):
            try:
                object.__setattr__(self, "operator", FilterOperator(self.operator))
            except ValueError as e:
                valid_operators = ", ".join(op.value for op in FilterOperator)
                raise ValueError(
                    f"Invalid operator: {self.operator}\n"
                    f"Valid operators are: {valid_operators}"
                ) from e

        # Collection operators validation
        if self.operator in (
            FilterOperator.IN,
            FilterOperator.NOT_IN,
            FilterOperator.ARRAY_CONTAINS,
            FilterOperator.ARRAY_OVERLAPS,
        ):
            if not hasattr(self.value, "__iter__") or isinstance(
                self.value, (str, bytes, dict)
            ):
                raise ValueError(
                    f"Value for {self.operator} must be iterable (not string/bytes/dict)"
                )

        # Text operators validation
        if self.operator in (
            FilterOperator.LIKE,
            FilterOperator.ILIKE,
            FilterOperator.CONTAINS,
            FilterOperator.NOT_CONTAINS,
            FilterOperator.STARTS_WITH,
            FilterOperator.ENDS_WITH,
            FilterOperator.REGEX,
            FilterOperator.IREGEX,
        ):
            if not isinstance(self.value, str):
                raise ValueError(f"Value for {self.operator} must be string")

        # Range operator validation
        if self.operator == FilterOperator.BETWEEN:
            if (
                not isinstance(self.value, dict)
                or "start" not in self.value
                or "end" not in self.value
            ):
                raise ValueError(
                    "Value for BETWEEN must be a dict with 'start' and 'end' keys"
                )
            if self.value["start"] > self.value["end"]:
                raise ValueError("Start value must be less than or equal to end value")

        # Array empty operators validation
        if self.operator in (
            FilterOperator.ARRAY_EMPTY,
            FilterOperator.ARRAY_NOT_EMPTY,
        ):
            if self.value is not None:
                raise ValueError(f"{self.operator} operator does not accept a value")

        # JSON operators validation
        if self.operator in (FilterOperator.JSON_CONTAINS, FilterOperator.JSON_EXISTS):
            if not isinstance(self.value, (dict, list)):
                raise ValueError(f"Value for {self.operator} must be a dict or list")
        elif self.operator == FilterOperator.JSON_HAS_KEY:
            if not isinstance(self.value, str):
                raise ValueError("Value for JSON_HAS_KEY must be a string")


@dataclass(frozen=True, slots=True)
class Sort:
    """Represents a sort condition in a query.

    Attributes:
        field: Field name to sort on
        direction: Sort direction (ASC or DESC)
    """

    field: str
    direction: SortDirection = SortDirection.ASC

    def __post_init__(self) -> None:
        """Validate sort attributes after initialization."""
        if not self.field:
            raise ValueError("Sort field cannot be empty")

        if not isinstance(self.direction, SortDirection):
            try:
                object.__setattr__(self, "direction", SortDirection(self.direction))
            except ValueError as e:
                valid_directions = ", ".join(d.value for d in SortDirection)
                raise ValueError(
                    f"Invalid sort direction: {self.direction}\n"
                    f"Valid directions are: {valid_directions}"
                ) from e

    @property
    def ascending(self) -> bool:
        """Backward compatibility property."""
        return self.direction == SortDirection.ASC


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PageParams:
    """Unified pagination parameters.

    Attributes:
        page: Page number, starting from 1
        size: Page size (items per page)
    """

    page: int = 1
    size: int = 10

    def __post_init__(self) -> None:
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.size < 1:
            raise ValueError("Size must be >= 1")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Get limit value (alias for size)."""
        return self.size


class Page(BaseModel, Generic[T]):
    """Unified pagination result.

    Attributes:
        items: List of items in current page
        total: Total number of items
        page: Current page number
        size: Page size
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """

    items: list[T]
    total: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        """Create a Page instance from raw data.

        Args:
            items: List of items in current page
            total: Total number of items
            page: Current page number
            size: Page size

        Returns:
            Page instance with calculated metadata
        """
        total_pages = (total + size - 1) // size if size > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )


@dataclass(frozen=True, slots=True)
class FilterGroup:
    """Represents a group of filters combined with a logical operator.

    Attributes:
        filters: List of filters in the group
        operator: Logical operator to combine filters (AND/OR)
    """

    filters: tuple[Filter, ...]
    operator: LogicalOperator = LogicalOperator.AND

    def __post_init__(self) -> None:
        """Validate filter group attributes after initialization."""
        if not self.filters:
            raise ValueError("Filter group must contain at least one filter")

        if not isinstance(self.operator, LogicalOperator):
            try:
                object.__setattr__(self, "operator", LogicalOperator(self.operator))
            except ValueError as e:
                valid_operators = ", ".join(op.value for op in LogicalOperator)
                raise ValueError(
                    f"Invalid logical operator: {self.operator}\n"
                    f"Valid operators are: {valid_operators}"
                ) from e


@dataclass(frozen=True, slots=True)
class Statistic:
    """Represents a statistical calculation in a query.

    Attributes:
        function: Statistical function to apply
        field: Field name to calculate on
        alias: Optional alias for the result
        distinct: Whether to count distinct values
        separator: Separator for GROUP_CONCAT (defaults to ",")
    """

    function: StatisticalFunction
    field: str
    alias: str | None = None
    distinct: bool = False
    separator: str | None = None

    def __post_init__(self) -> None:
        """Validate statistic attributes after initialization."""
        if not self.field:
            raise ValueError("Field cannot be empty")

        if not isinstance(self.function, StatisticalFunction):
            try:
                object.__setattr__(self, "function", StatisticalFunction(self.function))
            except ValueError as e:
                valid_functions = ", ".join(f.value for f in StatisticalFunction)
                raise ValueError(
                    f"Invalid statistical function: {self.function}\n"
                    f"Valid functions are: {valid_functions}"
                ) from e

        if self.separator is not None and self.function != StatisticalFunction.GROUP_CONCAT:
            raise ValueError("Separator is only valid for GROUP_CONCAT function")

        if self.function == StatisticalFunction.GROUP_CONCAT and not self.separator:
            object.__setattr__(self, "separator", ",")


@dataclass(frozen=True, slots=True)
class Having:
    """Represents a HAVING clause for filtering aggregates.

    Attributes:
        field: Field name (or aggregate alias) to filter on
        operator: Filter operator to apply
        value: Value to compare against
    """

    field: str
    operator: FilterOperator
    value: Any

    def __post_init__(self) -> None:
        """Validate having condition attributes after initialization."""
        if not self.field:
            raise ValueError("Having field cannot be empty")

        if not isinstance(self.operator, FilterOperator):
            try:
                object.__setattr__(self, "operator", FilterOperator(self.operator))
            except ValueError as e:
                valid_operators = ", ".join(op.value for op in FilterOperator)
                raise ValueError(
                    f"Invalid operator: {self.operator}\n"
                    f"Valid operators are: {valid_operators}"
                ) from e

