"""Base specification builder.

This module defines the base specification builder class.
"""

from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union
from uuid import UUID

from infrastructure.persistence.specification.core.type import SortDirection

from idp.framework.infrastructure.persistence.specification.core import (
    CompositeSpecification,
)
from idp.framework.infrastructure.persistence.specification.core.type import (
    FilterOperator,
)

from ..core import (
    Filter,
    FilterGroup,
    Having,
    LogicalOperator,
    Page,
    Sort,
    Specification,
    Statistic,
    StatisticalFunction,
)
from ..criteria.base import Criterion
from ..criteria.comparison import (
    ArrayContainsCriterion,
    ArrayEmptyCriterion,
    ArrayOverlapsCriterion,
    BetweenCriterion,
    ComparisonCriterion,
    EqualsCriterion,
    InCriterion,
    JsonContainsCriterion,
    JsonExistsCriterion,
    JsonHasKeyCriterion,
    NullCriterion,
    RegexCriterion,
    TextSearchCriterion,
)
from ..criteria.logical import AndCriterion, OrCriterion

T = TypeVar('T')
V = TypeVar('V')


class SpecificationBuilder(Generic[T]):
    """Base builder for specifications.

    This class provides a fluent interface for building specifications
    using various criteria.
    """

    def __init__(self):
        """Initialize builder."""
        self.criteria: List[Criterion] = []
        self.sorts: List[Sort] = []
        self.page: Optional[Page] = None
        self.selected_fields: List[str] = []
        self.included_relations: List[str] = []
        self.statistics: List[Statistic] = []
        self.group_by_fields: List[str] = []
        self.having_conditions: List[Having] = []
        self.filter_groups: List[FilterGroup] = []
        self.current_group: Optional[List[Filter]] = None
        self.current_group_operator: Optional[LogicalOperator] = None
        self.joins: List[dict] = []

    def group(self, operator: Union[str, LogicalOperator] = LogicalOperator.AND) -> 'SpecificationBuilder[T]':
        """Start a new filter group.

        Args:
            operator: Logical operator to combine filters within the group

        Returns:
            Self for method chaining

        Example:
            ```python
            spec = (SpecificationBuilder()
                .group(LogicalOperator.OR)
                .where("status", "=", "active")
                .where("status", "=", "pending")
                .end_group()
                .build())
            ```
        """
        if isinstance(operator, str):
            operator = LogicalOperator(operator.lower())

        if self.current_group is not None:
            raise ValueError(
                "Cannot start a new group while another group is active")

        self.current_group = []
        self.current_group_operator = operator
        return self

    def end_group(self) -> 'SpecificationBuilder[T]':
        """End the current filter group.

        Returns:
            Self for method chaining

        Raises:
            ValueError: If no group is currently active
        """
        if self.current_group is None:
            raise ValueError("No active filter group to end")

        if self.current_group:  # Only add group if it contains filters
            self.filter_groups.append(FilterGroup(
                filters=self.current_group,
                operator=self.current_group_operator
            ))

        self.current_group = None
        self.current_group_operator = None
        return self

    def where(self, field: str, operator: str, value: Any = None) -> 'SpecificationBuilder[T]':
        """Convenience method for adding filters with string operators.

        This method allows using more intuitive string operators instead of
        FilterOperator enums. For example:
            .where("age", ">=", 18)
            .where("status", "in", ["active", "pending"])
            .where("deleted_at", "is null")

        Args:
            field: Field to filter on
            operator: String operator (e.g. "=", ">", "like", etc.)
            value: Value to compare against (optional for some operators)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If the operator is not recognized
        """
        operator = operator.lower()

        # 处理特殊情况
        if operator in ["is null", "array empty"]:
            value = None
        elif operator in ["is not null", "array not empty"]:
            value = None
        elif operator == "between" and isinstance(value, (list, tuple)) and len(value) == 2:
            return self.between(field, value[0], value[1])

        # 从FilterOperator获取对应的枚举值
        try:
            enum_operator = FilterOperator.from_string(operator)
        except ValueError as e:
            raise ValueError(str(e))

        # Create filter
        filter = Filter(field=field, operator=enum_operator, value=value)

        # Add filter to current group or main criteria
        if self.current_group is not None:
            self.current_group.append(filter)
        else:
            self.criteria.append(ComparisonCriterion(
                field, value, enum_operator))

        return self

    def filter(self, field: str, value: Any) -> 'SpecificationBuilder[T]':
        """Shorthand for equality comparison.

        Args:
            field: Field to compare
            value: Value to compare against

        Returns:
            Self for method chaining
        """
        return self.where(field, "=", value)

    def exclude(self, field: str, value: Any) -> 'SpecificationBuilder[T]':
        """Shorthand for inequality comparison.

        Args:
            field: Field to compare
            value: Value to compare against

        Returns:
            Self for method chaining
        """
        return self.where(field, "!=", value)

    def add_criterion(self, criterion: Criterion) -> 'SpecificationBuilder[T]':
        """Add a criterion to the specification.

        Args:
            criterion: The criterion to add

        Returns:
            Self for method chaining

        Raises:
            ValueError: If criterion is None
        """
        if criterion is None:
            raise ValueError("Criterion cannot be None")
        self.criteria.append(criterion)
        return self

    def compare(self, field: str, value: Any, operator: FilterOperator) -> 'SpecificationBuilder[T]':
        """Add a comparison criterion.

        Args:
            field: Field to compare
            value: Value to compare against
            operator: Comparison operator to use

        Returns:
            Self for method chaining
        """
        return self.add_criterion(ComparisonCriterion(field, value, operator))

    def and_(self, *builders_fn: Callable[['SpecificationBuilder[T]'], 'SpecificationBuilder[T]']) -> 'SpecificationBuilder[T]':
        """Combine multiple criteria with AND.

        Args:
            *builders_fn: Functions that configure builders

        Returns:
            Self for method chaining

        Example:
            ```python
            spec = (SpecificationBuilder()
                .and_(
                    lambda b: b.where("status", "=", "active"),
                    lambda b: b.where("age", ">=", 18)
                )
                .build())
            ```
        """
        criteria = []
        for builder_fn in builders_fn:
            new_builder = self.__class__()
            builder_fn(new_builder)
            criteria.extend(new_builder.criteria)

        if criteria:
            self.add_criterion(AndCriterion(criteria))
        return self

    def or_(self, *builders_fn: Callable[['SpecificationBuilder[T]'], 'SpecificationBuilder[T]']) -> 'SpecificationBuilder[T]':
        """Combine multiple criteria with OR.

        Args:
            *builders_fn: Functions that configure builders

        Returns:
            Self for method chaining

        Example:
            ```python
            spec = (SpecificationBuilder()
                .or_(
                    lambda b: b.where("status", "=", "active"),
                    lambda b: b.where("status", "=", "pending")
                )
                .build())
            ```
        """
        criteria = []
        for builder_fn in builders_fn:
            new_builder = self.__class__()
            builder_fn(new_builder)
            criteria.extend(new_builder.criteria)

        if criteria:
            self.add_criterion(OrCriterion(criteria))
        return self

    def add_sort(self, field: str, direction: SortDirection = SortDirection.ASC) -> 'SpecificationBuilder[T]':
        """Add a sort order to the specification.

        Args:
            field: Field to sort by
            direction: Sort direction

        Returns:
            Self for method chaining

        Raises:
            ValueError: If field is empty
        """
        if not field:
            raise ValueError("Sort field cannot be empty")
        self.sorts.append(Sort(field=field, direction=direction))
        return self

    def set_page(self, page: Optional[int] = 1, size: Optional[int] = 10) -> 'SpecificationBuilder[T]':
        """Set pagination parameters.

        Args:
            page: Page number (starts from 1)
            size: Page size (number of items per page)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If page or size is not positive
        """
        if page is not None and page < 1:
            raise ValueError("Page number must be >= 1")
        if size is not None and size < 1:
            raise ValueError("Page size must be >= 1")
        self.page = Page.create(
            items=[],
            total=0,
            page=page or 1,
            size=size or 10
        )
        return self

    def by_id(self, id: UUID) -> 'SpecificationBuilder[T]':
        """Add ID filter.

        Args:
            id: Entity ID to match

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion('id', str(id)))

    def by_ids(self, ids: List[UUID]) -> 'SpecificationBuilder[T]':
        """Add multiple IDs filter.

        Args:
            ids: List of entity IDs to match

        Returns:
            Self for method chaining
        """
        return self.add_criterion(InCriterion('id', [str(id) for id in ids]))

    def text_search(self, field: str, text: str, case_sensitive: bool = False) -> 'SpecificationBuilder[T]':
        """Add text search filter.

        Args:
            field: Field to search in
            text: Text to search for
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            Self for method chaining
        """
        return self.add_criterion(TextSearchCriterion(field, text, case_sensitive))

    def text_query(self, field: str, text: str, case_sensitive: bool = False) -> 'SpecificationBuilder[T]':
        """Add text search filter.

        Args:
            field: Field to search in
            text: Text to search for
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            Self for method chaining
        """
        return self.add_criterion(TextSearchCriterion(field, text, case_sensitive))

    def between(self, field: str, start: V, end: V) -> 'SpecificationBuilder[T]':
        """Add between filter.

        Args:
            field: Field to compare
            start: Start value of the range
            end: End value of the range

        Returns:
            Self for method chaining

        Raises:
            ValueError: If field is empty or start/end values are invalid
        """
        if not field:
            raise ValueError("Field cannot be empty")
        if start is None or end is None:
            raise ValueError("Start and end values cannot be None")
        if start > end:
            raise ValueError(
                "Start value must be less than or equal to end value")

        return self.add_criterion(BetweenCriterion(field, start, end))

    def is_null(self, field: str, is_null: bool = True) -> 'SpecificationBuilder[T]':
        """Add NULL check filter.

        Args:
            field: Field to check
            is_null: Whether to check for NULL or NOT NULL

        Returns:
            Self for method chaining
        """
        return self.add_criterion(NullCriterion(field, is_null))

    def regex(self, field: str, pattern: str, case_sensitive: bool = True) -> 'SpecificationBuilder[T]':
        """Add regex pattern matching criterion.

        Args:
            field: Field to match against
            pattern: Regex pattern
            case_sensitive: Whether to use case-sensitive matching

        Returns:
            Self for method chaining
        """
        return self.add_criterion(RegexCriterion(field, pattern, case_sensitive))

    def array_contains(self, field: str, values: List[Any]) -> 'SpecificationBuilder[T]':
        """Add array containment criterion.

        Args:
            field: Array field to check
            values: Values that must be contained

        Returns:
            Self for method chaining
        """
        return self.add_criterion(ArrayContainsCriterion(field, values))

    def array_overlaps(self, field: str, values: List[Any]) -> 'SpecificationBuilder[T]':
        """Add array overlap criterion.

        Args:
            field: Array field to check
            values: Values to check for overlap

        Returns:
            Self for method chaining
        """
        return self.add_criterion(ArrayOverlapsCriterion(field, values))

    def array_empty(self, field: str, is_empty: bool = True) -> 'SpecificationBuilder[T]':
        """Add array emptiness criterion.

        Args:
            field: Array field to check
            is_empty: Whether to check for emptiness or non-emptiness

        Returns:
            Self for method chaining
        """
        return self.add_criterion(ArrayEmptyCriterion(field, is_empty))

    def json_contains(self, field: str, value: Union[Dict, List]) -> 'SpecificationBuilder[T]':
        """Add JSON containment criterion.

        Args:
            field: JSON field to check
            value: Value that must be contained

        Returns:
            Self for method chaining
        """
        return self.add_criterion(JsonContainsCriterion(field, value))

    def json_exists(self, field: str, path: Union[Dict, List]) -> 'SpecificationBuilder[T]':
        """Add JSON path existence criterion.

        Args:
            field: JSON field to check
            path: Path that must exist

        Returns:
            Self for method chaining
        """
        return self.add_criterion(JsonExistsCriterion(field, path))

    def json_has_key(self, field: str, key: str) -> 'SpecificationBuilder[T]':
        """Add JSON key existence criterion.

        Args:
            field: JSON field to check
            key: Key that must exist

        Returns:
            Self for method chaining
        """
        return self.add_criterion(JsonHasKeyCriterion(field, key))

    def select(self, *fields: str) -> 'SpecificationBuilder[T]':
        """Select specific fields to return.

        Args:
            fields: Field names to include in the result

        Returns:
            Self for method chaining

        Example:
            ```python
            spec = (SpecificationBuilder()
                .select("id", "name", "email")
                .where("is_active", "=", True)
                .build())
            ```
        """
        self.selected_fields.extend(fields)
        return self

    def include(self, *relations: str) -> 'SpecificationBuilder[T]':
        """Include related entities in the query result.

        Args:
            relations: Names of relations to include

        Returns:
            Self for method chaining

        Example:
            ```python
            spec = (SpecificationBuilder()
                .include("profile", "orders", "orders.items")
                .where("is_active", "=", True)
                .build())
            ```
        """
        self.included_relations.extend(relations)
        return self

    def add_statistic(
        self,
        function: Union[str, StatisticalFunction],
        field: str,
        alias: Optional[str] = None,
        distinct: bool = False,
        separator: Optional[str] = None
    ) -> 'SpecificationBuilder[T]':
        """Add a statistical function.

        Args:
            function: Statistical function to apply
            field: Field to analyze
            alias: Optional alias for the result
            distinct: Whether to apply DISTINCT to the calculation
            separator: Separator for GROUP_CONCAT (only valid for GROUP_CONCAT)

        Returns:
            Self for method chaining

        Example:
            ```python
            spec = (SpecificationBuilder()
                .add_statistic("count", "id", alias="total_users")
                .add_statistic("sum", "amount", alias="total_amount")
                .add_statistic("avg", "score", alias="average_score", distinct=True)
                .add_statistic("group_concat", "name", separator=", ")
                .build())
            ```
        """
        # Convert string function to enum if needed
        if isinstance(function, str):
            try:
                function = StatisticalFunction(function.lower())
            except ValueError:
                valid_functions = ", ".join(
                    f.value for f in StatisticalFunction)
                raise ValueError(
                    f"Unknown statistical function: {function}\n"
                    f"Valid functions are: {valid_functions}"
                )

        self.statistics.append(Statistic(
            function=function,
            field=field,
            alias=alias,
            distinct=distinct,
            separator=separator
        ))
        return self

    def count(
        self,
        field: str = "*",
        alias: Optional[str] = None,
        distinct: bool = False
    ) -> 'SpecificationBuilder[T]':
        """Add COUNT statistical function.

        Args:
            field: Field to count (defaults to "*" for COUNT(*))
            alias: Optional alias for the result
            distinct: Whether to count distinct values

        Returns:
            Self for method chaining
        """
        function = StatisticalFunction.COUNT_DISTINCT if distinct else StatisticalFunction.COUNT
        return self.add_statistic(function, field, alias, distinct=False)

    def sum(
        self,
        field: str,
        alias: Optional[str] = None,
        distinct: bool = False
    ) -> 'SpecificationBuilder[T]':
        """Add SUM statistical function.

        Args:
            field: Field to sum
            alias: Optional alias for the result
            distinct: Whether to sum distinct values

        Returns:
            Self for method chaining
        """
        return self.add_statistic(StatisticalFunction.SUM, field, alias, distinct)

    def avg(
        self,
        field: str,
        alias: Optional[str] = None,
        distinct: bool = False
    ) -> 'SpecificationBuilder[T]':
        """Add AVG statistical function.

        Args:
            field: Field to average
            alias: Optional alias for the result
            distinct: Whether to average distinct values

        Returns:
            Self for method chaining
        """
        return self.add_statistic(StatisticalFunction.AVG, field, alias, distinct)

    def min(
        self,
        field: str,
        alias: Optional[str] = None
    ) -> 'SpecificationBuilder[T]':
        """Add MIN statistical function.

        Args:
            field: Field to find minimum of
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        return self.add_statistic(StatisticalFunction.MIN, field, alias)

    def max(
        self,
        field: str,
        alias: Optional[str] = None
    ) -> 'SpecificationBuilder[T]':
        """Add MAX statistical function.

        Args:
            field: Field to find maximum of
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        return self.add_statistic(StatisticalFunction.MAX, field, alias)

    def group_concat(
        self,
        field: str,
        separator: str = ",",
        alias: Optional[str] = None,
        distinct: bool = False
    ) -> 'SpecificationBuilder[T]':
        """Add GROUP_CONCAT statistical function.

        Args:
            field: Field to concatenate
            separator: Separator between values
            alias: Optional alias for the result
            distinct: Whether to concatenate distinct values

        Returns:
            Self for method chaining
        """
        return self.add_statistic(
            StatisticalFunction.GROUP_CONCAT,
            field,
            alias,
            distinct,
            separator
        )

    def group_by(self, *fields: str) -> 'SpecificationBuilder[T]':
        """Add GROUP BY fields.

        Args:
            fields: Fields to group by

        Returns:
            Self for method chaining

        Example:
            ```python
            spec = (SpecificationBuilder()
                .group_by("department", "role")
                .count("id", alias="employee_count")
                .build())
            ```
        """
        self.group_by_fields.extend(fields)
        return self

    def having(
        self,
        field: str,
        operator: Union[str, FilterOperator],
        value: Any
    ) -> 'SpecificationBuilder[T]':
        """Add HAVING clause for filtering aggregates.

        Args:
            field: Aggregate field to filter on
            operator: Operator to use (string or FilterOperator)
            value: Value to compare against

        Returns:
            Self for method chaining

        Example:
            ```python
            spec = (SpecificationBuilder()
                .group_by("department")
                .count("id", alias="employee_count")
                .having("employee_count", ">", 5)
                .build())
            ```
        """
        # Convert string operator to enum if needed
        if isinstance(operator, str):
            operator = operator.lower()
            enum_operator = FilterOperator.from_string(operator)
            if enum_operator is None:
                valid_operators = ", ".join(
                    sorted(FilterOperator.string_to_enum.keys()))
                raise ValueError(
                    f"Unknown operator: {operator}\n"
                    f"Valid operators are: {valid_operators}"
                )
            operator = enum_operator

        self.having_conditions.append(Having(
            field=field,
            operator=operator,
            value=value
        ))
        return self

    def join(self, path: str, join_type: str = "left", on: Optional[str] = None, alias: Optional[str] = None) -> 'SpecificationBuilder[T]':
        """Add a join path to the specification.

        Args:
            path: Join path (e.g., 'details', 'supplier')
            join_type: 'left' or 'inner'
            on: Optional custom ON condition (as string or expression)
            alias: Optional alias for the join
        Returns:
            Self for method chaining
        """
        self.joins.append(
            {"path": path, "type": join_type, "on": on, "alias": alias})
        return self

    def build(self) -> Specification[T]:
        """Build the final specification.

        Returns:
            Composite specification with all added criteria

        Note:
            If there's an active filter group when build is called,
            it will be automatically ended.
        """
        # Auto-end any active group
        if self.current_group is not None:
            self.end_group()

        return CompositeSpecification(
            filters=[c.to_filter() for c in self.criteria],
            groups=self.filter_groups if self.filter_groups else None,
            sorts=self.sorts,
            page=self.page,
            fields=self.selected_fields if self.selected_fields else None,
            includes=self.included_relations if self.included_relations else None,
            statistics=self.statistics if self.statistics else None,
            group_by=self.group_by_fields if self.group_by_fields else None,
            having=self.having_conditions if self.having_conditions else None,
            joins=self.joins if self.joins else None
        )

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SpecificationBuilder[T]':
        """Create a specification builder from a dictionary/JSON data.

        The expected format is:
        {
            "filters": [
                {"field": "age", "operator": ">=", "value": 18},
                {"field": "status", "operator": "in", "value": ["active", "pending"]}
            ],
            "groups": [
                {
                    "operator": "or",
                    "filters": [
                        {"field": "status", "operator": "eq", "value": "active"},
                        {"field": "status", "operator": "eq", "value": "pending"}
                    ]
                }
            ],
            "sorts": [
                {"field": "created_at", "direction": "desc"}
            ],
            "page": {
                "page": 1,
                "size": 10
            },
            "fields": ["id", "name", "email"],
            "includes": ["profile", "orders.items"],
            "statistics": [
                {
                    "function": "count",
                    "field": "id",
                    "alias": "total_users",
                    "distinct": true
                }
            ],
            "group_by": ["department", "role"],
            "having": [
                {"field": "count", "operator": ">", "value": 5}
            ],
            "joins": [
                {"path": "details", "type": "left", "on": "details.id = orders.id", "alias": "details"}
            ]
        }

        Args:
            data: Dictionary containing query parameters

        Returns:
            Configured specification builder

        Raises:
            ValueError: If the data format is invalid
        """
        builder = SpecificationBuilder()

        # 处理基础过滤条件
        filters = data.get("filters", [])
        if not isinstance(filters, list):
            raise ValueError("filters must be a list")

        for filter_data in filters:
            if not isinstance(filter_data, dict):
                raise ValueError("each filter must be a dictionary")

            field = filter_data.get("field")
            operator = filter_data.get("operator")
            value = filter_data.get("value")

            if not field or not operator:
                raise ValueError("filter must have field and operator")

            builder.where(field, operator, value)

        # 处理过滤组
        groups = data.get("groups", [])
        if not isinstance(groups, list):
            raise ValueError("groups must be a list")

        for group_data in groups:
            if not isinstance(group_data, dict):
                raise ValueError("each group must be a dictionary")

            operator = group_data.get("operator", "and")
            filters = group_data.get("filters", [])

            if not isinstance(filters, list):
                raise ValueError("group filters must be a list")

            builder.group(operator)
            for filter_data in filters:
                field = filter_data.get("field")
                operator = filter_data.get("operator")
                value = filter_data.get("value")

                if not field or not operator:
                    raise ValueError("filter must have field and operator")

                builder.where(field, operator, value)
            builder.end_group()

        # 处理排序
        sorts = data.get("sorts", [])
        if not isinstance(sorts, list):
            raise ValueError("sorts must be a list")

        for sort_data in sorts:
            if not isinstance(sort_data, dict):
                raise ValueError("each sort must be a dictionary")

            field = sort_data.get("field")
            direction = sort_data.get("direction", SortDirection.ASC)

            if not field:
                raise ValueError("sort must have field")

            builder.add_sort(field, direction)

        # 处理分页 - 支持 page/size 和 offset/limit 两种格式
        page_data = data.get("page")
        if page_data:
            if not isinstance(page_data, dict):
                raise ValueError("page must be a dictionary")

            # 优先使用 page/size 格式
            if "page" in page_data and "size" in page_data:
                page = page_data.get("page", 1)
                size = page_data.get("size", 10)
                builder.set_page(page=page, size=size)
            # 向后兼容 offset/limit 格式
            # elif "offset" in page_data and "limit" in page_data:
            #     offset = page_data.get("offset", 0)
            #     limit = page_data.get("limit", 10)
            #     # 转换为 page/size
            #     page = (offset // limit) + 1 if limit > 0 else 1
            #     builder.set_page(page=page, size=limit)
            else:
                raise ValueError(
                    "page must contain either 'page'/'size' or 'offset'/'limit'")

        # 处理字段选择
        fields = data.get("fields", [])
        if fields:
            if not isinstance(fields, list):
                raise ValueError("fields must be a list")
            builder.select(*fields)

        # 处理关联加载
        includes = data.get("includes", [])
        if includes:
            if not isinstance(includes, list):
                raise ValueError("includes must be a list")
            builder.include(*includes)

        # 处理统计
        statistics = data.get("statistics", [])
        if statistics:
            if not isinstance(statistics, list):
                raise ValueError("statistics must be a list")

            for stat in statistics:
                if not isinstance(stat, dict):
                    raise ValueError("each statistic must be a dictionary")

                function = stat.get("function")
                field = stat.get("field")

                if not function or not field:
                    raise ValueError("statistic must have function and field")

                builder.add_statistic(
                    function=function,
                    field=field,
                    alias=stat.get("alias"),
                    distinct=stat.get("distinct", False),
                    separator=stat.get("separator")
                )

        # 处理分组
        group_by = data.get("group_by", [])
        if group_by:
            if not isinstance(group_by, list):
                raise ValueError("group_by must be a list")
            builder.group_by(*group_by)

        # 处理Having条件
        having = data.get("having", [])
        if having:
            if not isinstance(having, list):
                raise ValueError("having must be a list")

            for having_data in having:
                if not isinstance(having_data, dict):
                    raise ValueError(
                        "each having condition must be a dictionary")

                field = having_data.get("field")
                operator = having_data.get("operator")
                value = having_data.get("value")

                if not field or not operator:
                    raise ValueError(
                        "having condition must have field and operator")

                builder.having(field, operator, value)

        # 处理 joins
        joins = data.get("joins", [])
        if joins:
            if not isinstance(joins, list):
                raise ValueError("joins must be a list")
            for join_data in joins:
                if not isinstance(join_data, dict):
                    raise ValueError("each join must be a dictionary")
                path = join_data.get("path")
                join_type = join_data.get("type", "left")
                on = join_data.get("on")
                alias = join_data.get("alias")
                if not path:
                    raise ValueError("join must have path")
                builder.join(path, join_type, on, alias)

        return builder
