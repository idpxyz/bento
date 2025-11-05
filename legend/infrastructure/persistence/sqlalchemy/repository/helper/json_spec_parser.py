"""Specification builder helper.

This module provides helper classes for building specifications from JSON.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from infrastructure.persistence.sqlalchemy.po.base import BasePO

from idp.framework.infrastructure.persistence.specification import (
    Specification,
    StatisticalFunction,
)
from idp.framework.infrastructure.persistence.specification.builder.base import (
    SpecificationBuilder,
)
from idp.framework.infrastructure.persistence.specification.core.type import (
    FilterOperator,
    LogicalOperator,
    SortDirection,
)

if TYPE_CHECKING:
    from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import (
        FieldResolver,
        FieldSecurityError,
    )

T = TypeVar('T', bound=BasePO)


class JsonSpecParser:
    """JSON to Specification Parser for Infrastructure Layer.

    This parser is responsible for converting JSON-based query specifications
    into domain-agnostic Specification objects. It belongs to the Infrastructure
    layer and should NOT be exposed to the Domain layer.

    Following DDD principles:
    - Domain layer: Works with pure Specification objects
    - Infrastructure layer: Handles JSON parsing and conversion
    - Application layer: Orchestrates the parsing and domain operations

    Usage:
        ```python
        # In Infrastructure layer
        parser = JsonSpecParser(UserPO)
        spec = parser.parse(json_data)

        # Application Layer  
        async def search_users(self, json_query: dict):
            spec = self.json_parser.parse(json_query)
            return await self.user_repo.find_by_spec(spec)

        # Domain Layer - 保持纯净
        async def find_by_spec(self, spec: Specification[User]) -> List[User]:
        ```
    """

    def __init__(self, entity_type: Type[T], field_resolver=None):
        """Initialize JSON specification parser.

        Args:
            entity_type: Entity type to build specifications for
            field_resolver: 字段解析器，用于安全验证
        """
        self.entity_type = entity_type
        self.builder = SpecificationBuilder()
        from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import (
            FieldResolver,
        )
        self.field_resolver = field_resolver or FieldResolver(entity_type)

    def parse(self, json_spec: Dict[str, Any]) -> Specification[T]:
        """Parse JSON specification into Specification object with security validation.

        Args:
            json_spec: JSON specification

        Returns:
            Specification object

        Example JSON format:
        {
            "filters": [
                {
                    "field": "name",
                    "operator": "equals",
                    "value": "John"
                }
            ],
            "groups": [
                {
                    "operator": "and",
                    "filters": [
                        {
                            "field": "age",
                            "operator": "greater_than",
                            "value": 18
                        }
                    ]
                }
            ],
            "sorts": [
                {
                    "field": "created_at",
                    "direction": "desc"
                }
            ],
            "page": {
                "offset": 0,
                "limit": 10
            },
            "fields": ["id", "name", "age"],
            "includes": ["address", "orders"],
            "group_by": ["department"],
            "having": [
                {
                    "field": "count",
                    "operator": "greater_than",
                    "value": 5
                }
            ],
            "statistics": [
                {
                    "field": "salary",
                    "function": "avg"
                }
            ]
        }
        """
        # 去重 filters
        if filters := json_spec.get('filters'):
            # 使用字典来存储唯一的过滤条件，以 (field, operator, str(value)) 为键
            unique_filters = {}
            for f in filters:
                # 确保所有必要的字段都存在
                if not all(k in f for k in ('field', 'operator')):
                    continue

                # 规范化值，处理 None 和特殊类型
                value = f.get('value')
                if value is not None:
                    # 对于可序列化的值，使用 str 表示
                    if isinstance(value, (str, int, float, bool)):
                        value_str = str(value)
                    else:
                        # 对于复杂类型，使用 repr 确保唯一性
                        value_str = repr(value)
                else:
                    value_str = 'None'

                key = (f['field'], f['operator'], value_str)
                if key not in unique_filters:
                    unique_filters[key] = f

            # 更新原始 filters 列表
            json_spec['filters'] = list(unique_filters.values())

            # 应用过滤条件（带安全验证）
            for filter_ in json_spec['filters']:
                self._apply_filter(filter_)

        # Apply groups
        if groups := json_spec.get('groups'):
            for group in groups:
                self._apply_group(group)

        # Apply sorts
        if sorts := json_spec.get('sorts'):
            for sort_ in sorts:
                self._apply_sort(sort_)

        # Apply pagination
        if page := json_spec.get('page'):
            self._apply_page(page)

        # Apply field selection
        if fields := json_spec.get('fields'):
            self._apply_fields(fields)

        # Apply eager loading
        if includes := json_spec.get('includes'):
            self._apply_includes(includes)

        # Apply grouping
        if group_by := json_spec.get('group_by'):
            self._apply_grouping(group_by)

        # Apply having conditions
        if having := json_spec.get('having'):
            self._apply_having(having)

        # Apply statistics
        if statistics := json_spec.get('statistics'):
            self._apply_statistics(statistics)

        return self.builder.build()

    def _apply_filter(self, filter_data: dict[str, Any]) -> None:
        """Apply a filter to the specification builder with security validation.

        Args:
            filter_data: Filter data dictionary
        """
        if not filter_data.get("field") or not filter_data.get("operator"):
            return

        field = filter_data["field"]
        operator = filter_data["operator"]
        value = filter_data.get("value")

        try:
            # 解析字段（带安全验证）
            resolved_field = self.field_resolver.resolve(
                field, return_key=True, operation="filter")
            # 转换操作符
            enum_operator = FilterOperator.from_string(operator)

            # 对于 IS_NULL 和 IS_NOT_NULL 操作符，value 应该为 None
            if enum_operator in [FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL]:
                self.builder.where(resolved_field, enum_operator, None)
            else:
                # 对于其他操作符，确保有值
                if value is None:
                    raise ValueError(f"Operator {operator} requires a value")
                self.builder.where(resolved_field, enum_operator, value)
        except FieldSecurityError as e:
            # 记录安全错误但继续处理其他过滤条件
            import logging
            logging.warning(f"Filter security error: {e}")
            # 可以选择跳过这个过滤条件或抛出异常

    def _apply_group(self, group: Dict[str, Any]) -> None:
        """Apply a filter group to the specification builder with security validation.

        Args:
            group: Filter group dictionary

        Raises:
            ValueError: If group is missing required fields
        """
        operator = group.get('operator', 'and')
        filters = group.get('filters', [])

        if not filters:
            raise ValueError("Filter group must have filters")

        # 验证操作符
        try:
            enum_operator = LogicalOperator(operator.lower())
        except ValueError:
            valid_operators = ", ".join(op.value for op in LogicalOperator)
            raise ValueError(
                f"Invalid group operator: {operator}\n"
                f"Valid operators are: {valid_operators}"
            )

        # 应用组过滤条件
        for filter_ in filters:
            self._apply_filter(filter_)

        # 设置组操作符
        self.builder.set_group_operator(enum_operator)

    def _apply_sort(self, sort_: Dict[str, Any]) -> None:
        """Apply a sort to the specification builder with security validation.

        Args:
            sort_: Sort dictionary containing field and direction

        Raises:
            ValueError: If sort is missing required fields or has invalid direction
        """
        field = sort_.get('field')
        direction = sort_.get('direction', 'asc')

        if not field:
            raise ValueError("Sort must have field")

        try:
            # 解析字段名（带安全验证）
            resolved_field = self.field_resolver.resolve(
                field, return_key=True, operation="sort")

            # 应用排序
            try:
                self.builder.add_sort(
                    resolved_field,
                    direction=SortDirection(direction.lower())
                )
            except ValueError:
                valid_directions = ", ".join(
                    dir.value for dir in SortDirection)
                raise ValueError(
                    f"Invalid sort direction: {direction}\n"
                    f"Valid directions are: {valid_directions}"
                )
        except FieldSecurityError as e:
            # 记录安全错误但继续处理其他排序条件
            import logging
            logging.warning(f"Sort security error: {e}")

    def _apply_page(self, page: Dict[str, Any]) -> None:
        """Apply pagination to the specification builder.

        Args:
            page: Page dictionary containing offset and limit

        Raises:
            ValueError: If page parameters are invalid
        """
        offset = page.get('offset', 0)
        limit = page.get('limit', 10)

        if offset < 0:
            raise ValueError("Page offset cannot be negative")
        if limit is not None and limit < 0:
            raise ValueError("Page limit cannot be negative")

        self.builder.set_page(offset=offset, limit=limit)

    def _apply_fields(self, fields: List[str]) -> None:
        """Apply field selection to the specification builder with security validation.

        Args:
            fields: List of fields to select

        Raises:
            ValueError: If any field is invalid
        """
        if not isinstance(fields, list):
            raise ValueError("Fields must be a list")

        try:
            # 验证字段访问权限
            valid_fields = self.field_resolver.validate_fields(
                fields, operation="read")
            resolved_fields = []
            for field in valid_fields:
                try:
                    resolved_fields.append(
                        self.field_resolver.resolve(field, return_key=True))
                except AttributeError as e:
                    raise ValueError(f"Invalid field: {field}") from e

            self.builder.select(*resolved_fields)
        except FieldSecurityError as e:
            # 记录安全错误
            import logging
            logging.warning(f"Field selection security error: {e}")
            # 可以选择使用默认字段或抛出异常

    def _apply_includes(self, includes: List[str]) -> None:
        """Apply eager loading to the specification builder with security validation.

        Args:
            includes: List of relations to include

        Raises:
            ValueError: If includes is not a list
        """
        if not isinstance(includes, list):
            raise ValueError("Includes must be a list")

        # 验证关系访问权限
        valid_includes = []
        for relation in includes:
            try:
                self.field_resolver.validate_field_access(
                    relation, operation="read")
                valid_includes.append(relation)
            except FieldSecurityError as e:
                # 记录安全错误但继续处理其他关系
                import logging
                logging.warning(f"Include security error: {e}")

        self.builder.include(*valid_includes)

    def _apply_grouping(self, group_by: List[str]) -> None:
        """Apply grouping to the specification builder with security validation.

        Args:
            group_by: List of fields to group by

        Raises:
            ValueError: If any field is invalid
        """
        if not isinstance(group_by, list):
            raise ValueError("Group by fields must be a list")

        try:
            # 验证字段访问权限
            valid_fields = self.field_resolver.validate_fields(
                group_by, operation="read")
            resolved_fields = []
            for field in valid_fields:
                try:
                    resolved_fields.append(
                        self.field_resolver.resolve(field, return_key=True))
                except AttributeError as e:
                    raise ValueError(f"Invalid group by field: {field}") from e

            self.builder.group_by(*resolved_fields)
        except FieldSecurityError as e:
            # 记录安全错误
            import logging
            logging.warning(f"Grouping security error: {e}")

    def _apply_having(self, having: List[Dict[str, Any]]) -> None:
        """Apply having conditions to the specification builder with security validation.

        Args:
            having: List of having conditions

        Raises:
            ValueError: If any having condition is invalid
        """
        if not isinstance(having, list):
            raise ValueError("Having conditions must be a list")

        for condition in having:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')

            if not field or not operator:
                raise ValueError(
                    "Having condition must have field and operator")

            try:
                # 解析字段名（带安全验证）
                resolved_field = self.field_resolver.resolve(
                    field, return_key=True, operation="filter")
            except AttributeError as e:
                raise ValueError(f"Invalid having field: {field}") from e
            except FieldSecurityError as e:
                # 记录安全错误但继续处理其他having条件
                import logging
                logging.warning(f"Having security error: {e}")
                continue

            # 使用 FilterOperator 的 from_string 方法处理操作符
            try:
                enum_operator = FilterOperator.from_string(operator)
            except ValueError as e:
                raise ValueError(str(e))

            # 应用having条件
            self.builder.having(resolved_field, enum_operator, value)

    def _apply_statistics(self, statistics: List[Dict[str, Any]]) -> None:
        """Apply statistics to the specification builder with security validation.

        Args:
            statistics: List of statistics to apply

        Raises:
            ValueError: If any statistic is invalid
        """
        if not isinstance(statistics, list):
            raise ValueError("Statistics must be a list")

        for stat in statistics:
            field = stat.get('field')
            function = stat.get('function')
            alias = stat.get('alias')
            distinct = stat.get('distinct', False)
            separator = stat.get('separator')

            if not field or not function:
                raise ValueError("Statistic must have field and function")

            try:
                # 解析字段名（带安全验证）
                resolved_field = self.field_resolver.resolve(
                    field, return_key=True, operation="read")
            except AttributeError as e:
                raise ValueError(f"Invalid statistic field: {field}") from e
            except FieldSecurityError as e:
                # 记录安全错误但继续处理其他统计函数
                import logging
                logging.warning(f"Statistics security error: {e}")
                continue

            # 应用统计
            try:
                self.builder.add_statistic(
                    function=StatisticalFunction(function.lower()),
                    field=resolved_field,
                    alias=alias,
                    distinct=distinct,
                    separator=separator
                )
            except ValueError:
                valid_functions = ", ".join(
                    f.value for f in StatisticalFunction)
                raise ValueError(
                    f"Invalid statistical function: {function}\n"
                    f"Valid functions are: {valid_functions}"
                )
