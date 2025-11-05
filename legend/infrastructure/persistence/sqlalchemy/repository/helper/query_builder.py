"""Query builder helper.

This module provides helper classes for building SQLAlchemy queries.
"""

from typing import Any, List, Optional, Type, TypeVar, Union

from infrastructure.persistence.specification.core.type import SortDirection
from infrastructure.persistence.sqlalchemy.po.base import BasePO
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import RelationshipProperty, aliased, selectinload

from idp.framework.infrastructure.persistence.specification import (
    ExistsSpec,
    Filter,
    FilterGroup,
    FilterOperator,
    Having,
    LogicalOperator,
    NotExistsSpec,
    Page,
    Sort,
    Statistic,
    StatisticalFunction,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import (
    FieldResolver,
    FieldSecurityConfig,
    FieldSecurityError,
)

T = TypeVar('T', bound=BasePO)


def build_condition(field: Any, filter_: Filter) -> Any:
    """构建SQLAlchemy条件

    Args:
        field: SQLAlchemy列或属性
        filter_: 过滤规范

    Returns:
        SQLAlchemy条件或None（如果操作符不支持）
    """
    operator = filter_.operator
    value = filter_.value

    # 处理空值检查
    if operator in (FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL):
        return field.is_(None) if operator == FilterOperator.IS_NULL else field.isnot(None)

    # 处理数组空值检查
    if operator in (FilterOperator.ARRAY_EMPTY, FilterOperator.ARRAY_NOT_EMPTY):
        return field == [] if operator == FilterOperator.ARRAY_EMPTY else field != []

    # 处理比较操作符
    if operator == FilterOperator.EQUALS:
        return field == value
    if operator == FilterOperator.NOT_EQUALS:
        return field != value
    if operator == FilterOperator.GREATER_THAN:
        return field > value
    if operator == FilterOperator.GREATER_EQUAL:
        return field >= value
    if operator == FilterOperator.LESS_THAN:
        return field < value
    if operator == FilterOperator.LESS_EQUAL:
        return field <= value

    # 处理集合操作符
    if operator == FilterOperator.IN:
        return field.in_(value)
    if operator == FilterOperator.NOT_IN:
        return ~field.in_(value)
    if operator == FilterOperator.BETWEEN:
        return field.between(value['start'], value['end'])

    # 处理文本操作符
    if operator == FilterOperator.LIKE:
        return field.like(value)
    if operator == FilterOperator.ILIKE:
        return field.ilike(value)
    if operator == FilterOperator.CONTAINS:
        return field.contains(value)
    if operator == FilterOperator.NOT_CONTAINS:
        return ~field.contains(value)
    if operator == FilterOperator.STARTS_WITH:
        return field.startswith(value)
    if operator == FilterOperator.ENDS_WITH:
        return field.endswith(value)
    if operator == FilterOperator.REGEX:
        return field.regexp_match(value)
    if operator == FilterOperator.IREGEX:
        return field.regexp_match(value, flags='i')

    # 处理数组操作符
    if operator == FilterOperator.ARRAY_CONTAINS:
        return field.contains(value)
    if operator == FilterOperator.ARRAY_OVERLAPS:
        return field.overlap(value)

    # 处理JSON操作符
    if operator == FilterOperator.JSON_CONTAINS:
        return field.contains(value)
    if operator in (FilterOperator.JSON_EXISTS, FilterOperator.JSON_HAS_KEY):
        return field.has_key(value)

    raise ValueError(f"Unsupported operator: {operator}")


def _apply_joins_to_stmt(stmt, entity_type, field_resolver, joins, applied_joins_dict):
    """通用JOIN处理工具函数，供QueryBuilder和CountQueryBuilder共用，支持自动推断on条件"""
    if not joins:
        return stmt
    from sqlalchemy import text
    from sqlalchemy.orm import RelationshipProperty, aliased

    #  _apply_joins_to_stmt 内部用 set 跟踪 join 路径，和外部的 dict 分离。
    # 这样不会影响 QueryBuilder/CountQueryBuilder 的 join 逻辑，也不会报错。
    # 用 set 跟踪已处理路径，避免 AttributeError
    applied_paths = set(applied_joins_dict.keys()) if isinstance(
        applied_joins_dict, dict) else set()
    for join in joins:
        path = join["path"]
        if path in applied_paths:
            continue
        applied_paths.add(path)
        try:
            field_resolver.validate_field_access(path, operation="read")
            parts = path.split('.')
            current_model = entity_type
            for idx, rel_name in enumerate(parts):
                rel = getattr(current_model, rel_name)
                # 自动推断 on 条件（仅在 join["on"] 为空时）
                on_clause = None
                if idx == len(parts) - 1 and not join.get("on"):
                    # 只在最后一级 join 且未手写 on 时推断
                    prop = getattr(type(current_model), rel_name).property
                    if isinstance(prop, RelationshipProperty):
                        # 只支持一对多/多对一
                        local_cols = list(prop.local_columns)
                        remote_cols = list(prop.remote_side)
                        if len(local_cols) == 1 and len(remote_cols) == 1:
                            on_clause = local_cols[0] == remote_cols[0]
                # 用户手写 on 优先
                if idx == len(parts) - 1 and join.get("on"):
                    on_condition = join["on"]
                    if isinstance(on_condition, str):
                        if "=" in on_condition:
                            field_parts = on_condition.split("=")
                            if len(field_parts) == 2:
                                on_clause = text(on_condition)
                        else:
                            on_clause = text(on_condition)
                    else:
                        on_clause = on_condition
                alias = aliased(rel.property.mapper.class_) if join.get(
                    "alias") else rel.property.mapper.class_
                join_type = join.get("type", "left")
                if join_type == "left":
                    if on_clause is not None:
                        stmt = stmt.outerjoin(alias, on_clause)
                    else:
                        stmt = stmt.outerjoin(alias, rel)
                else:
                    if on_clause is not None:
                        stmt = stmt.join(alias, on_clause)
                    else:
                        stmt = stmt.join(alias, rel)
                current_model = alias
        except FieldSecurityError as e:
            import logging
            logging.warning(f"Join security error: {e}")
            continue
    return stmt


class CountQueryBuilder:
    """专门用于构建计数查询的构建器"""

    def __init__(self, entity_type: Type[T], field_resolver: Optional[FieldResolver] = None):
        """初始化计数查询构建器

        Args:
            entity_type: 实体类型
            field_resolver: 字段解析器，用于安全验证
        """
        self.entity_type = entity_type
        self.field_resolver = field_resolver or FieldResolver(entity_type)
        self.reset()
        self._applied_joins = set()  # 跟踪已应用的 join 路径

    def reset(self) -> 'CountQueryBuilder':
        """重置查询构建器到初始状态

        Returns:
            CountQueryBuilder实例
        """
        self.stmt = select(func.count(self.entity_type.id).label('count'))
        return self

    def apply_filters(self, filters: List[Filter], resolver: Optional[Any] = None) -> 'CountQueryBuilder':
        """应用过滤条件

        Args:
            filters: 过滤条件列表
            resolver: 字段解析器，用于安全验证

        Returns:
            CountQueryBuilder实例
        """
        if not filters:
            return self

        applied_conditions = set()
        conditions = []

        for filter_ in filters:
            try:
                # 用 resolver 解析字段
                if resolver:
                    field = resolver(filter_.field, operation="filter")
                else:
                    field = self.field_resolver.resolve(
                        filter_.field, operation="filter")
                condition_key = (str(field), filter_.operator)

                if condition_key not in applied_conditions:
                    condition = build_condition(field, filter_)
                    if condition is not None:
                        conditions.append(condition)
                        applied_conditions.add(condition_key)
            except FieldSecurityError as e:
                import logging
                logging.warning(f"Filter security error: {e}")
                continue

        if conditions:
            self.stmt = self.stmt.where(and_(*conditions))

        return self

    def apply_groups(self, groups: List[FilterGroup], resolver: Optional[Any] = None) -> 'CountQueryBuilder':
        """应用过滤组

        Args:
            groups: 过滤组列表
            resolver: 字段解析器，用于安全验证

        Returns:
            CountQueryBuilder实例
        """
        if not groups:
            return self

        for group in groups:
            applied_conditions = set()
            conditions = []

            for filter_ in group.filters:
                try:
                    if resolver:
                        field = resolver(filter_.field, operation="filter")
                    else:
                        field = self.field_resolver.resolve(
                            filter_.field, operation="filter")
                    condition_key = (str(field), filter_.operator)

                    if condition_key not in applied_conditions:
                        condition = build_condition(field, filter_)
                        if condition is not None:
                            conditions.append(condition)
                            applied_conditions.add(condition_key)
                except FieldSecurityError as e:
                    import logging
                    logging.warning(f"Filter group security error: {e}")
                    continue

            if conditions:
                if group.operator == LogicalOperator.AND:
                    self.stmt = self.stmt.where(and_(*conditions))
                else:
                    self.stmt = self.stmt.where(or_(*conditions))

        return self

    def apply_joins(self, joins: List[dict]):
        self.stmt = _apply_joins_to_stmt(
            self.stmt, self.entity_type, self.field_resolver, joins, self._applied_joins)
        return self

    def apply_statistics(self, statistics: List[Statistic], resolver: Optional[Any] = None) -> 'CountQueryBuilder':
        """应用统计函数

        Args:
            statistics: 统计函数列表
            resolver: 字段解析器，用于安全验证

        Returns:
            CountQueryBuilder实例
        """
        if not statistics:
            return self

        stat_columns = []
        for stat in statistics:
            try:
                field_path = stat.field
                if resolver:
                    field = resolver(field_path, operation="read")
                else:
                    field = self.field_resolver.resolve(
                        field_path, operation="read")
                self.field_resolver.validate_field_access(
                    field_path, operation="read")
                label = stat.alias or f"{stat.function.value}_{stat.field}"
                if stat.function == StatisticalFunction.COUNT:
                    if getattr(stat, 'distinct', False):
                        stat_columns.append(func.count(
                            field.distinct()).label(label))
                    else:
                        stat_columns.append(func.count(field).label(label))
                elif stat.function == StatisticalFunction.SUM:
                    stat_columns.append(func.sum(field).label(label))
                elif stat.function == StatisticalFunction.AVG:
                    stat_columns.append(func.avg(field).label(label))
                elif stat.function == StatisticalFunction.MIN:
                    stat_columns.append(func.min(field).label(label))
                elif stat.function == StatisticalFunction.MAX:
                    stat_columns.append(func.max(field).label(label))
                elif stat.function == StatisticalFunction.GROUP_CONCAT:
                    stat_columns.append(func.group_concat(
                        field, separator=stat.separator or ',').label(label))
            except FieldSecurityError as e:
                import logging
                logging.warning(f"Statistics security error: {e}")
                continue

        where_clause = self.stmt.whereclause
        self.stmt = select(*stat_columns)
        if where_clause is not None:
            self.stmt = self.stmt.where(where_clause)

        return self

    def build(self, joins: Optional[List[dict]] = None, statistics: Optional[List[Statistic]] = None) -> Any:
        """构建最终的查询，先应用统计再应用 joins，确保 join 不会丢失"""
        if statistics:
            self.apply_statistics(statistics)
        if joins:
            self.apply_joins(joins)
        return self.stmt


class QueryBuilder:
    """Helper class for building SQLAlchemy queries with security validation."""

    def __init__(self, entity_type: Type[T], field_resolver: Optional[FieldResolver] = None):
        """Initialize query builder.

        Args:
            entity_type: Entity type to build queries for
            field_resolver: 字段解析器，用于安全验证
        """
        self.entity_type = entity_type
        self.field_resolver = field_resolver or FieldResolver(entity_type)
        # 添加查询限制配置
        self._query_limits = {
            'max_limit': 1000,        # 最大查询限制
            'default_limit': 50,      # 默认查询限制
            'max_offset': 10000,      # 最大偏移量（防止深度分页）
            'max_page_size': 100,     # 最大页面大小
            'default_page_size': 20,  # 默认页面大小
        }
        self.reset()

    def reset(self) -> 'QueryBuilder':
        """重置查询构建器到初始状态

        Returns:
            QueryBuilder实例
        """
        self.stmt = select(self.entity_type)
        self.count_builder = CountQueryBuilder(
            self.entity_type, self.field_resolver)
        # 添加 JOIN 跟踪机制
        self._applied_joins = {}  # 跟踪已应用的 JOIN: {path: (alias, model)}
        self._join_aliases = {}   # 跟踪别名: {path: alias}
        return self

    def _get_or_create_join(self, field_path: str) -> tuple:
        """获取或创建 JOIN，避免重复 JOIN

        Args:
            field_path: 字段路径，如 "user.department"

        Returns:
            (alias, model) 元组
        """
        if field_path in self._applied_joins:
            return self._applied_joins[field_path]

        parts = field_path.split('.')
        current_model = self.entity_type
        current_path = ""

        for rel_name in parts:
            if current_path:
                current_path += "." + rel_name
            else:
                current_path = rel_name

            # 检查是否已经 JOIN 过这个路径
            if current_path in self._applied_joins:
                current_model = self._applied_joins[current_path][1]
                continue

            # 创建新的 JOIN
            rel = getattr(current_model, rel_name)

            # 为每个路径创建唯一的别名
            if current_path not in self._join_aliases:
                alias_name = f"alias_{len(self._join_aliases)}"
                self._join_aliases[current_path] = alias_name

            alias = aliased(rel.property.mapper.class_,
                            name=self._join_aliases[current_path])

            # 执行 JOIN
            self.stmt = self.stmt.outerjoin(alias, rel)

            # 记录已应用的 JOIN
            self._applied_joins[current_path] = (alias, alias)
            current_model = alias

        return self._applied_joins[field_path]

    def _resolve_field_with_joins(self, field_path: str) -> Any:
        """解析字段路径并确保必要的 JOIN 已创建

        Args:
            field_path: 字段路径，如 "user.department.name"

        Returns:
            SQLAlchemy 列对象
        """
        parts = field_path.split('.')

        if len(parts) == 1:
            # 直接字段，不需要 JOIN
            return getattr(self.entity_type, field_path)

        # 需要 JOIN 的嵌套字段
        relation_path = '.'.join(parts[:-1])
        field_name = parts[-1]

        # 获取或创建 JOIN
        alias, _ = self._get_or_create_join(relation_path)

        # 返回字段
        return getattr(alias, field_name)

    def build_query(self) -> 'QueryBuilder':
        """创建一个新的查询构建器实例

        Returns:
            新的QueryBuilder实例
        """
        return QueryBuilder(self.entity_type, self.field_resolver)

    def build_count_query(self) -> CountQueryBuilder:
        """获取计数查询构建器

        Returns:
            CountQueryBuilder实例
        """
        return self.count_builder

    def apply_filters(self, filters: List[Filter], resolver: Optional[Any] = None) -> 'QueryBuilder':
        """Apply filters to the query with security validation.

        Args:
            filters: List of filters to apply
            resolver: 字段解析器，用于安全验证

        Returns:
            Self for method chaining
        """
        if not filters:
            return self

        applied_conditions = set()
        conditions = []

        for filter_ in filters:
            try:
                field_path = filter_.field
                # 用 resolver 解析字段
                if resolver:
                    column = resolver(field_path, operation="filter")
                else:
                    column = self._resolve_field_with_joins(field_path)
                self.field_resolver.validate_field_access(
                    field_path, operation="filter")
                condition_key = (str(column), filter_.operator)
                if condition_key not in applied_conditions:
                    condition = build_condition(column, filter_)
                    if condition is not None:
                        conditions.append(condition)
                        applied_conditions.add(condition_key)
            except FieldSecurityError as e:
                import logging
                logging.warning(f"Filter security error: {e}")
                continue

        if conditions:
            self.stmt = self.stmt.where(and_(*conditions))

        return self

    def apply_groups(self, groups: List[FilterGroup], resolver: Optional[Any] = None) -> 'QueryBuilder':
        """Apply filter groups to the query with security validation.

        Args:
            groups: List of filter groups to apply
            resolver: 字段解析器，用于安全验证

        Returns:
            Self for method chaining
        """
        if not groups:
            return self

        for group in groups:
            applied_conditions = set()
            conditions = []

            for filter_ in group.filters:
                try:
                    if resolver:
                        field = resolver(filter_.field, operation="filter")
                    else:
                        field = self._resolve_field_with_joins(filter_.field)
                    condition_key = (str(field), filter_.operator)
                    if condition_key not in applied_conditions:
                        condition = build_condition(field, filter_)
                        if condition is not None:
                            conditions.append(condition)
                            applied_conditions.add(condition_key)
                except FieldSecurityError as e:
                    import logging
                    logging.warning(f"Filter group security error: {e}")
                    continue

            if conditions:
                if group.operator == LogicalOperator.AND:
                    self.stmt = self.stmt.where(and_(*conditions))
                else:
                    self.stmt = self.stmt.where(or_(*conditions))

        return self

    def apply_sorts(self, sorts: List[Sort], resolver: Optional[Any] = None) -> 'QueryBuilder':
        """Apply sorting to the query with security validation.

        Args:
            sorts: List of sort conditions to apply
            resolver: 字段解析器，用于安全验证

        Returns:
            Self for method chaining
        """
        if not sorts:
            return self

        for sort_ in sorts:
            try:
                field_path = sort_.field
                # 用 resolver 解析字段
                if resolver:
                    field = resolver(field_path, operation="sort")
                else:
                    field = self._resolve_field_with_joins(field_path)
                self.field_resolver.validate_field_access(
                    field_path, operation="sort")
                if sort_.direction == SortDirection.DESC:
                    self.stmt = self.stmt.order_by(field.desc())
                else:
                    self.stmt = self.stmt.order_by(field.asc())
            except FieldSecurityError as e:
                import logging
                logging.warning(f"Sort security error: {e}")
                continue

        return self

    def apply_pagination(self, page: Optional[Page]) -> 'QueryBuilder':
        """Apply pagination to the query with enhanced validation and protection.

        Args:
            page: Pagination parameters

        Returns:
            Self for method chaining
        """
        if not page:
            # 如果没有分页参数，应用默认限制
            return self.apply_query_limit()

        # 兼容新版 Page 只含 page/size 字段
        if hasattr(page, 'page') and hasattr(page, 'size'):
            page_num = getattr(page, 'page', 1)
            page_size = getattr(
                page, 'size', self._query_limits['default_page_size'])

            # 验证并限制页面大小
            page_size = min(page_size, self._query_limits['max_page_size'])
            page_size = max(1, page_size)  # 确保页面大小至少为1

            # 验证并限制页码
            page_num = max(1, page_num)  # 确保页码至少为1

            # 计算偏移量
            offset = (page_num - 1) * page_size

            # 验证偏移量不超过最大限制
            if offset > self._query_limits['max_offset']:
                # 如果偏移量过大，调整到最大允许的页码
                max_page = self._query_limits['max_offset'] // page_size + 1
                page_num = max_page
                offset = (page_num - 1) * page_size

            self.stmt = self.stmt.offset(offset).limit(page_size)

        # 向后兼容老的 offset/limit 字段
        elif hasattr(page, 'offset') and hasattr(page, 'limit'):
            offset = getattr(page, 'offset', 0)
            limit = getattr(page, 'limit', self._query_limits['default_limit'])

            # 验证并限制参数
            offset = min(offset, self._query_limits['max_offset'])
            offset = max(0, offset)

            limit = min(limit, self._query_limits['max_limit'])
            limit = max(1, limit)

            self.stmt = self.stmt.offset(offset).limit(limit)

        return self

    def apply_smart_pagination(self, page_num: int = 1, page_size: int = None,
                               max_pages: int = None) -> 'QueryBuilder':
        """应用智能分页，自动处理边界情况和性能优化

        Args:
            page_num: 页码，从1开始
            page_size: 页面大小，如果为None则使用默认值
            max_pages: 最大页码限制，如果为None则使用配置的最大偏移量计算

        Returns:
            Self for method chaining
        """
        if page_size is None:
            page_size = self._query_limits['default_page_size']

        # 验证并限制页面大小
        page_size = min(page_size, self._query_limits['max_page_size'])
        page_size = max(1, page_size)

        # 验证并限制页码
        page_num = max(1, page_num)

        # 计算最大页码
        if max_pages is None:
            max_pages = self._query_limits['max_offset'] // page_size + 1

        # 限制页码不超过最大值
        page_num = min(page_num, max_pages)

        # 计算偏移量
        offset = (page_num - 1) * page_size

        self.stmt = self.stmt.offset(offset).limit(page_size)
        return self

    def apply_field_selection(self, fields: List[str], resolver: Optional[Any] = None) -> 'QueryBuilder':
        """Apply field selection to the query with security validation.

        Args:
            fields: List of fields to select
            resolver: 字段解析器，用于安全验证

        Returns:
            Self for method chaining
        """
        if not fields:
            return self

        try:
            # 验证字段访问权限
            valid_fields = self.field_resolver.validate_fields(
                fields, operation="read")
            if resolver:
                selected_fields = [resolver(field, operation="read")
                                   for field in valid_fields]
            else:
                selected_fields = [self.field_resolver.resolve(
                    field) for field in valid_fields]
            self.stmt = select(*selected_fields)
        except FieldSecurityError as e:
            import logging
            logging.warning(f"Field selection security error: {e}")
            allowed_fields = self.field_resolver.get_allowed_fields()
            if allowed_fields:
                if resolver:
                    selected_fields = [
                        resolver(field, operation="read") for field in allowed_fields]
                else:
                    selected_fields = [self.field_resolver.resolve(
                        field) for field in allowed_fields]
                self.stmt = select(*selected_fields)

        return self

    def apply_eager_loading(self, includes: List[str], resolver: Optional[Any] = None) -> 'QueryBuilder':
        """Apply eager loading to the query with security validation.

        Args:
            includes: List of relations to eager load
            resolver: 字段解析器，用于安全验证

        Returns:
            Self for method chaining
        """
        if not includes:
            return self

        for relation in includes:
            try:
                self.field_resolver.validate_field_access(
                    relation, operation="read")
                if resolver:
                    relationship_attr = resolver(relation, operation="read")
                else:
                    relationship_attr = getattr(self.entity_type, relation)
                self.stmt = self.stmt.options(selectinload(relationship_attr))
            except FieldSecurityError as e:
                import logging
                logging.warning(f"Eager loading security error: {e}")
                continue

        return self

    def apply_grouping(self, group_by: List[str], resolver: Optional[Any] = None) -> 'QueryBuilder':
        """Apply grouping to the query with security validation.

        Args:
            group_by: List of fields to group by
            resolver: 字段解析器，用于安全验证

        Returns:
            Self for method chaining
        """
        if not group_by:
            return self

        try:
            valid_fields = self.field_resolver.validate_fields(
                group_by, operation="read")
            group_by_fields = []
            for field in valid_fields:
                if resolver:
                    resolved_field = resolver(field, operation="read")
                else:
                    resolved_field = self._resolve_field_with_joins(field)
                group_by_fields.append(resolved_field)
            self.stmt = self.stmt.group_by(*group_by_fields)
        except FieldSecurityError as e:
            import logging
            logging.warning(f"Grouping security error: {e}")

        return self

    def apply_having(self, having: List[Having], resolver: Optional[Any] = None) -> 'QueryBuilder':
        """Apply having conditions to the query with security validation.

        Args:
            having: List of having conditions to apply
            resolver: 字段解析器，用于安全验证

        Returns:
            Self for method chaining
        """
        if not having:
            return self

        having_conditions = []
        for condition in having:
            try:
                field_path = condition.field
                if resolver:
                    field = resolver(field_path, operation="filter")
                else:
                    field = self._resolve_field_with_joins(field_path)
                self.field_resolver.validate_field_access(
                    field_path, operation="filter")
                having_condition = build_condition(field, condition)
                if having_condition is not None:
                    having_conditions.append(having_condition)
            except FieldSecurityError as e:
                import logging
                logging.warning(f"Having security error: {e}")
                continue

        if having_conditions:
            self.stmt = self.stmt.having(and_(*having_conditions))

        return self

    def apply_statistics(self, statistics: List[Statistic], resolver: Optional[Any] = None) -> 'QueryBuilder':
        """应用统计函数

        Args:
            statistics: 统计函数列表
            resolver: 字段解析器，用于安全验证

        Returns:
            QueryBuilder实例
        """
        if not statistics:
            return self

        stat_columns = []
        for stat in statistics:
            try:
                field_path = stat.field
                if resolver:
                    field = resolver(field_path, operation="read")
                else:
                    field = self._resolve_field_with_joins(field_path)
                self.field_resolver.validate_field_access(
                    field_path, operation="read")
                label = stat.alias or f"{stat.function.value}_{stat.field}"
                if stat.function == StatisticalFunction.COUNT:
                    if getattr(stat, 'distinct', False):
                        stat_columns.append(func.count(
                            field.distinct()).label(label))
                    else:
                        stat_columns.append(func.count(field).label(label))
                elif stat.function == StatisticalFunction.SUM:
                    stat_columns.append(func.sum(field).label(label))
                elif stat.function == StatisticalFunction.AVG:
                    stat_columns.append(func.avg(field).label(label))
                elif stat.function == StatisticalFunction.MIN:
                    stat_columns.append(func.min(field).label(label))
                elif stat.function == StatisticalFunction.MAX:
                    stat_columns.append(func.max(field).label(label))
                elif stat.function == StatisticalFunction.GROUP_CONCAT:
                    stat_columns.append(func.group_concat(
                        field, separator=stat.separator or ',').label(label))
            except FieldSecurityError as e:
                import logging
                logging.warning(f"Statistics security error: {e}")
                continue

        where_clause = self.stmt.whereclause
        self.stmt = select(*stat_columns)
        if where_clause is not None:
            self.stmt = self.stmt.where(where_clause)

        return self

    def apply_joins(self, joins: List[dict]):
        self.stmt = _apply_joins_to_stmt(
            self.stmt, self.entity_type, self.field_resolver, joins, self._applied_joins)
        return self

    def build(self) -> Any:
        """Build the final query.

        Returns:
            SQLAlchemy select statement
        """
        # 优先处理显式 joins
        spec = getattr(self, 'spec', None)
        if spec and hasattr(spec, 'joins') and spec.joins:
            self.apply_joins(spec.joins)
        # 检查是否是计数查询
        is_count_query = any(
            hasattr(col, 'element') and
            isinstance(col.element, func.count)
            for col in self.stmt.columns
        )

        # 如果是计数查询，确保移除所有排序和分页
        if is_count_query:
            # 完全重置查询，只保留统计列和WHERE条件
            stat_columns = [col for col in self.stmt.columns]
            where_clause = self.stmt.whereclause

            # 创建新的查询，只包含统计列
            self.stmt = select(*stat_columns)

            # 重新添加WHERE条件
            if where_clause is not None:
                self.stmt = self.stmt.where(where_clause)

        return self.stmt

    def get_join_statistics(self) -> dict:
        """获取 JOIN 统计信息，用于调试和监控

        Returns:
            JOIN 统计信息字典
        """
        return {
            "applied_joins": list(self._applied_joins.keys()),
            "join_count": len(self._applied_joins),
            "alias_mapping": self._join_aliases.copy()
        }

    def clear_joins(self) -> 'QueryBuilder':
        """清除所有已应用的 JOIN，重置查询

        Returns:
            Self for method chaining
        """
        self._applied_joins.clear()
        self._join_aliases.clear()
        self.stmt = select(self.entity_type)
        return self

    def set_query_limits(self, **limits) -> 'QueryBuilder':
        """设置查询限制配置

        Args:
            **limits: 查询限制参数
                - max_limit: 最大查询限制
                - default_limit: 默认查询限制
                - max_offset: 最大偏移量
                - max_page_size: 最大页面大小
                - default_page_size: 默认页面大小

        Returns:
            Self for method chaining
        """
        for key, value in limits.items():
            if key in self._query_limits:
                self._query_limits[key] = value
        return self

    def get_query_limits(self) -> dict:
        """获取当前查询限制配置

        Returns:
            查询限制配置字典
        """
        return self._query_limits.copy()

    def apply_query_limit(self, limit: Optional[int] = None) -> 'QueryBuilder':
        """应用查询限制

        Args:
            limit: 查询限制数量，如果为None则使用默认限制

        Returns:
            Self for method chaining
        """
        if limit is None:
            limit = self._query_limits['default_limit']

        # 验证并限制查询数量
        limit = min(limit, self._query_limits['max_limit'])
        limit = max(1, limit)  # 确保至少返回1条记录

        self.stmt = self.stmt.limit(limit)
        return self

    def apply_offset(self, offset: int = 0) -> 'QueryBuilder':
        """应用偏移量

        Args:
            offset: 偏移量

        Returns:
            Self for method chaining
        """
        # 验证并限制偏移量
        offset = min(offset, self._query_limits['max_offset'])
        offset = max(0, offset)  # 确保偏移量非负

        self.stmt = self.stmt.offset(offset)
        return self

    def validate_pagination_params(self, page_num: int, page_size: int) -> tuple:
        """验证分页参数并返回修正后的值

        Args:
            page_num: 页码
            page_size: 页面大小

        Returns:
            (修正后的页码, 修正后的页面大小)
        """
        # 验证页面大小
        page_size = min(page_size, self._query_limits['max_page_size'])
        page_size = max(1, page_size)

        # 验证页码
        page_num = max(1, page_num)

        # 检查偏移量是否超过限制
        offset = (page_num - 1) * page_size
        if offset > self._query_limits['max_offset']:
            # 调整到最大允许的页码
            max_page = self._query_limits['max_offset'] // page_size + 1
            page_num = max_page

        return page_num, page_size

    def get_pagination_info(self, page_num: int, page_size: int, total_count: int) -> dict:
        """获取分页信息

        Args:
            page_num: 页码
            page_size: 页面大小
            total_count: 总记录数

        Returns:
            分页信息字典
        """
        # 验证参数
        page_num, page_size = self.validate_pagination_params(
            page_num, page_size)

        # 计算分页信息
        total_pages = (total_count + page_size - 1) // page_size
        offset = (page_num - 1) * page_size
        has_next = page_num < total_pages
        has_prev = page_num > 1

        return {
            'page_num': page_num,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': total_pages,
            'offset': offset,
            'has_next': has_next,
            'has_prev': has_prev,
            'start_index': offset + 1,
            'end_index': min(offset + page_size, total_count)
        }

    def apply_cursor_pagination(self, cursor: Optional[str] = None,
                                limit: Optional[int] = None) -> 'QueryBuilder':
        """应用游标分页（适用于大数据量场景）

        Args:
            cursor: 游标值，用于标识起始位置
            limit: 限制数量

        Returns:
            Self for method chaining
        """
        if limit is None:
            limit = self._query_limits['default_limit']

        # 验证并限制查询数量
        limit = min(limit, self._query_limits['max_limit'])
        limit = max(1, limit)

        # 如果有游标，添加游标条件（这里需要根据具体实现来扩展）
        if cursor:
            # TODO: 实现游标条件
            pass

        self.stmt = self.stmt.limit(limit)
        return self

    def apply_exists(self, exists_spec: ExistsSpec) -> 'QueryBuilder':
        """应用 EXISTS 子查询条件

        Args:
            exists_spec: EXISTS 规范

        Returns:
            Self for method chaining
        """
        if not exists_spec:
            return self

        try:
            # 构建子查询
            subquery = self._build_exists_subquery(exists_spec)

            # 应用 EXISTS 条件
            self.stmt = self.stmt.where(subquery.exists())

        except Exception as e:
            # 记录错误但继续处理
            import logging
            logging.warning(f"EXISTS subquery error: {e}")

        return self

    def apply_not_exists(self, not_exists_spec: NotExistsSpec) -> 'QueryBuilder':
        """应用 NOT EXISTS 子查询条件

        Args:
            not_exists_spec: NOT EXISTS 规范

        Returns:
            Self for method chaining
        """
        if not not_exists_spec:
            return self

        try:
            # 构建子查询
            subquery = self._build_exists_subquery(not_exists_spec)

            # 应用 NOT EXISTS 条件
            self.stmt = self.stmt.where(~subquery.exists())

        except Exception as e:
            # 记录错误但继续处理
            import logging
            logging.warning(f"NOT EXISTS subquery error: {e}")

        return self

    def _build_exists_subquery(self, exists_spec: Union[ExistsSpec, NotExistsSpec]) -> Any:
        """构建 EXISTS 子查询

        Args:
            exists_spec: EXISTS 或 NOT EXISTS 规范

        Returns:
            SQLAlchemy 子查询
        """
        from sqlalchemy.orm import aliased

        # 获取子查询的实体类型
        # 这里需要根据实体类型名称获取实际的 SQLAlchemy 模型
        # 暂时使用一个简单的映射，实际使用时可能需要更复杂的实体解析
        entity_type = self._get_entity_type_by_name(exists_spec.entity_type)
        if not entity_type:
            raise ValueError(f"Unknown entity type: {exists_spec.entity_type}")

        # 创建子查询
        subquery = select(1).select_from(entity_type)

        # 应用过滤条件
        if exists_spec.filters:
            for filter_ in exists_spec.filters:
                try:
                    # 验证字段访问权限
                    self.field_resolver.validate_field_access(
                        filter_.field, operation="filter")

                    # 解析字段
                    field = self._resolve_field_for_entity(
                        filter_.field, entity_type)
                    condition = build_condition(field, filter_)
                    if condition is not None:
                        subquery = subquery.where(condition)
                except Exception as e:
                    import logging
                    logging.warning(f"Filter error in EXISTS subquery: {e}")
                    continue

        # 应用过滤组
        if exists_spec.filter_groups:
            for group in exists_spec.filter_groups:
                conditions = []
                for filter_ in group.filters:
                    try:
                        # 验证字段访问权限
                        self.field_resolver.validate_field_access(
                            filter_.field, operation="filter")

                        # 解析字段
                        field = self._resolve_field_for_entity(
                            filter_.field, entity_type)
                        condition = build_condition(field, filter_)
                        if condition is not None:
                            conditions.append(condition)
                    except Exception as e:
                        import logging
                        logging.warning(
                            f"Filter group error in EXISTS subquery: {e}")
                        continue

                if conditions:
                    if group.operator == LogicalOperator.AND:
                        subquery = subquery.where(and_(*conditions))
                    else:
                        subquery = subquery.where(or_(*conditions))

        # 应用关联条件
        if exists_spec.correlation_field:
            try:
                # 解析主查询的关联字段（支持 correlation_main_field）
                main_field_name = getattr(
                    exists_spec, 'correlation_main_field', None) or exists_spec.correlation_field
                main_field = self._resolve_field_with_joins(main_field_name)
                # 解析子查询的关联字段
                sub_field = self._resolve_field_for_entity(
                    exists_spec.correlation_field, entity_type)
                # 构建关联条件
                if exists_spec.correlation_operator == FilterOperator.EQUALS:
                    correlation_condition = sub_field == main_field
                else:
                    correlation_condition = build_condition(
                        sub_field,
                        Filter(
                            field=exists_spec.correlation_field,
                            operator=exists_spec.correlation_operator,
                            value=main_field
                        )
                    )
                if correlation_condition is not None:
                    subquery = subquery.where(correlation_condition)
            except Exception as e:
                import logging
                logging.warning(f"Correlation error in EXISTS subquery: {e}")

        return subquery

    def _get_entity_type_by_name(self, entity_name: str) -> Optional[Type]:
        """根据实体名称获取实体类型

        Args:
            entity_name: 实体名称

        Returns:
            实体类型或 None
        """
        # 这里需要实现实体类型解析逻辑
        # 暂时返回 None，实际使用时需要根据具体的实体映射来实现
        # 可以通过注册表、反射或其他方式来获取实体类型

        # 示例实现（需要根据实际情况调整）
        entity_mapping = {
            'User': self.entity_type,  # 假设当前实体类型就是 User
            # 可以添加更多实体映射
        }

        return entity_mapping.get(entity_name)

    def _resolve_field_for_entity(self, field_path: str, entity_type: Type) -> Any:
        """为指定实体解析字段路径

        Args:
            field_path: 字段路径
            entity_type: 实体类型

        Returns:
            SQLAlchemy 列对象
        """
        parts = field_path.split('.')

        if len(parts) == 1:
            # 直接字段
            return getattr(entity_type, field_path)

        # 嵌套字段（需要处理 JOIN）
        current_model = entity_type
        for part in parts[:-1]:
            if hasattr(current_model, part):
                current_model = getattr(
                    current_model, part).property.mapper.class_
            else:
                raise ValueError(f"Invalid field path: {field_path}")

        return getattr(current_model, parts[-1])
