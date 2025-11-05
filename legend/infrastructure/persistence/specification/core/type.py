"""
Core types for the specification pattern.

This module defines the core types, enums and data classes used in the specification pattern.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

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
    EQUALS = 'eq'
    NOT_EQUALS = 'ne'
    GREATER_THAN = 'gt'
    GREATER_EQUAL = 'ge'
    LESS_THAN = 'lt'
    LESS_EQUAL = 'le'
    IN = 'in'
    NOT_IN = 'not_in'
    BETWEEN = 'between'
    IS_NULL = 'is_null'
    IS_NOT_NULL = 'is_not_null'

    # Text operators
    LIKE = 'like'
    ILIKE = 'ilike'
    CONTAINS = 'contains'
    NOT_CONTAINS = 'not_contains'
    STARTS_WITH = 'starts_with'
    ENDS_WITH = 'ends_with'
    REGEX = 'regex'
    IREGEX = 'iregex'

    # Array operators
    ARRAY_CONTAINS = 'array_contains'
    ARRAY_OVERLAPS = 'array_overlaps'
    ARRAY_EMPTY = 'array_empty'
    ARRAY_NOT_EMPTY = 'array_not_empty'

    # JSON operators
    JSON_CONTAINS = 'json_contains'
    JSON_EXISTS = 'json_exists'
    JSON_HAS_KEY = 'json_has_key'

    @classmethod
    def get_operator_map(cls) -> Dict[str, 'FilterOperator']:
        """Get all operator mappings including symbols and text aliases.

        Returns:
            Dictionary mapping all operator forms to their corresponding operators
        """
        return {
            # Symbol operators
            '=': cls.EQUALS,
            '==': cls.EQUALS,
            '!=': cls.NOT_EQUALS,
            '<>': cls.NOT_EQUALS,
            '>': cls.GREATER_THAN,
            '>=': cls.GREATER_EQUAL,
            '<': cls.LESS_THAN,
            '<=': cls.LESS_EQUAL,

            # Text aliases
            'equals': cls.EQUALS,
            'equal': cls.EQUALS,
            'eq': cls.EQUALS,
            'not_equals': cls.NOT_EQUALS,
            'not_equal': cls.NOT_EQUALS,
            'ne': cls.NOT_EQUALS,
            'greater_than': cls.GREATER_THAN,
            'gt': cls.GREATER_THAN,
            'greater_equal': cls.GREATER_EQUAL,
            'ge': cls.GREATER_EQUAL,
            'less_than': cls.LESS_THAN,
            'lt': cls.LESS_THAN,
            'less_equal': cls.LESS_EQUAL,
            'le': cls.LESS_EQUAL,
            'in': cls.IN,
            'not_in': cls.NOT_IN,
            'between': cls.BETWEEN,
            'is_null': cls.IS_NULL,
            'is_not_null': cls.IS_NOT_NULL,
            'like': cls.LIKE,
            'ilike': cls.ILIKE,
            'contains': cls.CONTAINS,
            'not_contains': cls.NOT_CONTAINS,
            'starts_with': cls.STARTS_WITH,
            'ends_with': cls.ENDS_WITH,
            'regex': cls.REGEX,
            'iregex': cls.IREGEX,
            'array_contains': cls.ARRAY_CONTAINS,
            'array_overlaps': cls.ARRAY_OVERLAPS,
            'array_empty': cls.ARRAY_EMPTY,
            'array_not_empty': cls.ARRAY_NOT_EMPTY,
            'json_contains': cls.JSON_CONTAINS,
            'json_exists': cls.JSON_EXISTS,
            'json_has_key': cls.JSON_HAS_KEY
        }

    @classmethod
    def from_string(cls, operator: str) -> 'FilterOperator':
        """Convert a string operator to FilterOperator enum.

        Args:
            operator: String operator to convert (can be symbol or text form)

        Returns:
            Corresponding FilterOperator enum value

        Raises:
            ValueError: If operator is not recognized
        """
        operator = operator.lower()

        # First try direct enum value
        try:
            return cls(operator)
        except ValueError:
            pass

        # Then try operator map
        operator_map = cls.get_operator_map()
        if operator in operator_map:
            return operator_map[operator]

        # If not found, raise error with valid operators
        valid_operators = ", ".join(sorted(set(
            list(cls.__members__.values()) + list(operator_map.keys())
        )))
        raise ValueError(
            f"Unknown operator: {operator}\n"
            f"Valid operators are: {valid_operators}"
        )

    @classmethod
    def get_valid_operators(cls) -> List[str]:
        """Get list of all valid operators (including symbols and aliases).

        Returns:
            List of valid operator strings
        """
        return sorted(set(
            list(cls.__members__.values()) +
            list(cls.get_operator_map().keys())
        ))


class LogicalOperator(str, Enum):
    """Logical operators for combining filters and specifications."""
    AND = 'and'
    OR = 'or'


class SortDirection(str, Enum):
    """Sort direction for query results."""
    ASC = 'asc'
    DESC = 'desc'


class StatisticalFunction(str, Enum):
    """Statistical functions for aggregate queries."""
    COUNT = 'count'
    COUNT_DISTINCT = 'count_distinct'
    SUM = 'sum'
    AVG = 'avg'
    MIN = 'min'
    MAX = 'max'
    GROUP_CONCAT = 'group_concat'


@dataclass
class Filter:
    """Represents a filter condition in a query."""
    field: str
    operator: FilterOperator
    value: Any

    def __post_init__(self):
        """Validate filter attributes after initialization."""
        # Basic validation
        if not self.field:
            raise ValueError("Filter field cannot be empty")

        # Operator validation
        if not isinstance(self.operator, FilterOperator):
            try:
                self.operator = FilterOperator(self.operator)
            except ValueError:
                valid_operators = ", ".join(op.value for op in FilterOperator)
                raise ValueError(
                    f"Invalid operator: {self.operator}\n"
                    f"Valid operators are: {valid_operators}"
                )

        # Collection operators validation
        if self.operator in (FilterOperator.IN, FilterOperator.NOT_IN,
                             FilterOperator.ARRAY_CONTAINS, FilterOperator.ARRAY_OVERLAPS):
            if not hasattr(self.value, '__iter__') or isinstance(self.value, (str, bytes, dict)):
                raise ValueError(
                    f"Value for {self.operator} must be iterable (not string/bytes/dict)")

        # Text operators validation
        if self.operator in (FilterOperator.LIKE, FilterOperator.ILIKE,
                             FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS,
                             FilterOperator.STARTS_WITH, FilterOperator.ENDS_WITH,
                             FilterOperator.REGEX, FilterOperator.IREGEX):
            if not isinstance(self.value, str):
                raise ValueError(f"Value for {self.operator} must be string")

        # Range operator validation
        if self.operator == FilterOperator.BETWEEN:
            if not isinstance(self.value, dict) or 'start' not in self.value or 'end' not in self.value:
                raise ValueError(
                    "Value for BETWEEN must be a dict with 'start' and 'end' keys")
            if self.value['start'] > self.value['end']:
                raise ValueError(
                    "Start value must be less than or equal to end value")

        # Array empty operators validation
        if self.operator in (FilterOperator.ARRAY_EMPTY, FilterOperator.ARRAY_NOT_EMPTY):
            if self.value is not None:
                raise ValueError(
                    f"{self.operator} operator does not accept a value")

        # JSON operators validation
        if self.operator in (FilterOperator.JSON_CONTAINS, FilterOperator.JSON_EXISTS):
            if not isinstance(self.value, (dict, list)):
                raise ValueError(
                    f"Value for {self.operator} must be a dict or list")
        elif self.operator == FilterOperator.JSON_HAS_KEY:
            if not isinstance(self.value, str):
                raise ValueError("Value for JSON_HAS_KEY must be a string")


@dataclass
class Sort:
    """Represents a sort condition in a query."""
    field: str
    direction: SortDirection = SortDirection.ASC

    def __post_init__(self):
        """Validate sort attributes after initialization."""
        if not self.field:
            raise ValueError("Sort field cannot be empty")

        if not isinstance(self.direction, SortDirection):
            try:
                self.direction = SortDirection(self.direction)
            except ValueError:
                valid_directions = ", ".join(d.value for d in SortDirection)
                raise ValueError(
                    f"Invalid sort direction: {self.direction}\n"
                    f"Valid directions are: {valid_directions}"
                )

    @property
    def ascending(self) -> bool:
        """Backward compatibility property."""
        return self.direction == SortDirection.ASC


T = TypeVar('T')


@dataclass
class PageParams:
    """统一的分页参数"""
    page: int = 1          # 页码，从1开始
    size: int = 10         # 每页大小

    def __post_init__(self):
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.size < 1:
            raise ValueError("Size must be >= 1")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


class Page(BaseModel, Generic[T]):
    """统一的分页结果"""
    items: List[T]
    total: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int) -> "Page[T]":
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
            has_prev=has_prev
        )


@dataclass
class FilterGroup:
    """Represents a group of filters combined with a logical operator."""
    filters: List[Filter]
    operator: LogicalOperator = LogicalOperator.AND

    def __post_init__(self):
        """Validate filter group attributes after initialization."""
        if not self.filters:
            raise ValueError("Filter group must contain at least one filter")

        if not isinstance(self.operator, LogicalOperator):
            try:
                self.operator = LogicalOperator(self.operator)
            except ValueError:
                valid_operators = ", ".join(op.value for op in LogicalOperator)
                raise ValueError(
                    f"Invalid logical operator: {self.operator}\n"
                    f"Valid operators are: {valid_operators}"
                )


@dataclass
class Statistic:
    """Represents a statistical calculation in a query."""
    function: StatisticalFunction
    field: str
    alias: Optional[str] = None
    distinct: bool = False
    separator: Optional[str] = None

    def __post_init__(self):
        """Validate statistic attributes after initialization."""
        if not self.field:
            raise ValueError("Field cannot be empty")

        if not isinstance(self.function, StatisticalFunction):
            try:
                self.function = StatisticalFunction(self.function)
            except ValueError:
                valid_functions = ", ".join(
                    f.value for f in StatisticalFunction)
                raise ValueError(
                    f"Invalid statistical function: {self.function}\n"
                    f"Valid functions are: {valid_functions}"
                )
        if self.separator is not None and self.function != StatisticalFunction.GROUP_CONCAT:
            raise ValueError(
                "Separator is only valid for GROUP_CONCAT function")
        if self.function == StatisticalFunction.GROUP_CONCAT and not self.separator:
            self.separator = ","


@dataclass
class Having:
    """Represents a HAVING clause for filtering aggregates."""
    field: str
    operator: FilterOperator
    value: Any

    def __post_init__(self):
        """Validate having condition attributes after initialization."""
        if not self.field:
            raise ValueError("Having field cannot be empty")

        if not isinstance(self.operator, FilterOperator):
            try:
                self.operator = FilterOperator(self.operator)
            except ValueError:
                valid_operators = ", ".join(op.value for op in FilterOperator)
                raise ValueError(
                    f"Invalid operator: {self.operator}\n"
                    f"Valid operators are: {valid_operators}"
                )


@dataclass
class ExistsSpec:
    """Represents an EXISTS subquery condition."""
    entity_type: str  # 子查询的实体类型
    filters: Optional[List[Filter]] = None
    filter_groups: Optional[List[FilterGroup]] = None
    correlation_field: Optional[str] = None  # 子查询字段
    correlation_main_field: Optional[str] = None  # 主查询字段
    correlation_operator: FilterOperator = FilterOperator.EQUALS

    def __post_init__(self):
        """Validate EXISTS specification attributes after initialization."""
        if not self.entity_type:
            raise ValueError("Entity type cannot be empty")
        if not self.filters and not self.filter_groups:
            raise ValueError(
                "At least one filter or filter group must be provided")
        if self.filters is None:
            self.filters = []
        if self.filter_groups is None:
            self.filter_groups = []
        # 兼容旧用法：如果 correlation_main_field 未指定，默认与 correlation_field 相同
        if self.correlation_field and not self.correlation_main_field:
            self.correlation_main_field = self.correlation_field


@dataclass
class NotExistsSpec:
    """Represents a NOT EXISTS subquery condition."""
    entity_type: str  # 子查询的实体类型
    filters: Optional[List[Filter]] = None
    filter_groups: Optional[List[FilterGroup]] = None
    correlation_field: Optional[str] = None  # 子查询字段
    correlation_main_field: Optional[str] = None  # 主查询字段
    correlation_operator: FilterOperator = FilterOperator.EQUALS

    def __post_init__(self):
        """Validate NOT EXISTS specification attributes after initialization."""
        if not self.entity_type:
            raise ValueError("Entity type cannot be empty")
        if not self.filters and not self.filter_groups:
            raise ValueError(
                "At least one filter or filter group must be provided")
        if self.filters is None:
            self.filters = []
        if self.filter_groups is None:
            self.filter_groups = []
        # 兼容旧用法：如果 correlation_main_field 未指定，默认与 correlation_field 相同
        if self.correlation_field and not self.correlation_main_field:
            self.correlation_main_field = self.correlation_field


# Type aliases for improved readability
FilterValue = Union[str, int, float, bool, List[Any], Dict[str, Any], None]
SortList = List[Sort]
FilterList = List[Filter]
GroupList = List[FilterGroup]
StatisticList = List[Statistic]
HavingList = List[Having]
FieldList = List[str]
