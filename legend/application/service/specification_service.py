"""Specification服务层

专门处理查询规范的构建、管理和优化，提供：
- 类型安全的查询构建
- 预定义查询模式
- 查询规范缓存
- 性能优化
- 业务逻辑封装

设计原则：
- 单一职责：专注查询规范管理
- 开闭原则：支持扩展新的查询模式
- 依赖倒置：依赖抽象而非具体实现
"""

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from idp.framework.infrastructure.persistence.specification import (
    FilterOperator,
    LogicalOperator,
    Specification,
    SpecificationBuilder,
)
from idp.framework.infrastructure.persistence.specification.core.type import (
    Sort,
    SortDirection,
)

T = TypeVar('T')  # 实体类型


class BaseSpecificationService(Generic[T], ABC):
    """基础Specification服务

    提供通用的查询规范构建和管理功能
    """

    def __init__(self):
        self._builder_pool = []  # 构建器池，用于性能优化

    @abstractmethod
    def get_default_includes(self) -> List[str]:
        """获取默认包含的关系"""
        pass

    @abstractmethod
    def get_default_sorts(self) -> List[tuple]:
        """获取默认排序"""
        pass

    def create_builder(self) -> SpecificationBuilder:
        """创建新的构建器实例"""
        if self._builder_pool:
            return self._builder_pool.pop()
        return SpecificationBuilder()

    def return_builder(self, builder: SpecificationBuilder):
        """归还构建器到池中"""
        builder.criteria.clear()
        builder.sorts.clear()
        builder.page = None
        builder.selected_fields.clear()
        builder.included_relations.clear()
        builder.statistics.clear()
        builder.group_by_fields.clear()
        builder.having_conditions.clear()
        builder.filter_groups.clear()
        self._builder_pool.append(builder)

    def build_basic_spec(self, **filters) -> Specification:
        """构建基础查询规范"""
        builder = self.create_builder()
        try:
            # 应用默认包含
            for include in self.get_default_includes():
                builder.include(include)

            # 应用过滤条件
            for field, value in filters.items():
                if value is not None:
                    builder.filter(field, value)

            # 应用默认排序
            for field, direction in self.get_default_sorts():
                builder.add_sort(field, direction)

            return builder.build()
        finally:
            self.return_builder(builder)

    def build_search_spec(
        self,
        search_text: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        includes: Optional[List[str]] = None,
        sorts: Optional[List[tuple]] = None,
        page: Optional[Dict[str, int]] = None
    ) -> Specification:
        """构建搜索查询规范"""
        builder = self.create_builder()
        try:
            # 基础包含
            default_includes = self.get_default_includes()
            if includes:
                default_includes.extend(includes)
            for include in default_includes:
                builder.include(include)

            # 文本搜索
            if search_text:
                self._apply_text_search(builder, search_text)

            # 过滤条件
            if filters:
                for field, value in filters.items():
                    if value is not None:
                        builder.filter(field, value)

            # 排序
            if sorts:
                for field, direction in sorts:
                    builder.add_sort(field, direction)
            else:
                for field, direction in self.get_default_sorts():
                    builder.add_sort(field, direction)

            # 分页
            if page:
                builder.set_page(page=page.get(
                    'offset', 0) // (page.get('limit') or 1) + 1, size=page.get('limit'))

            return builder.build()
        finally:
            self.return_builder(builder)

    def _apply_text_search(self, builder: SpecificationBuilder, search_text: str):
        """应用文本搜索逻辑 - 子类可重写"""
        # 默认实现：在name和code字段中搜索
        builder.or_(
            lambda b: b.text_search("name", search_text),
            lambda b: b.text_search("code", search_text)
        )

    @lru_cache(maxsize=128)
    def get_cached_spec(self, spec_key: str) -> Specification:
        """获取缓存的查询规范"""
        # 子类实现具体的缓存逻辑
        raise NotImplementedError

    def build_advanced_spec(
        self,
        criteria: Dict[str, Any],
        operator: str = "and"
    ) -> Specification:
        """构建高级查询规范"""
        builder = self.create_builder()
        try:
            # 应用默认包含
            for include in self.get_default_includes():
                builder.include(include)

            # 构建复杂条件
            conditions = []
            for field, value in criteria.items():
                if value is not None:
                    if isinstance(value, dict):
                        # 复杂条件：{"operator": "in", "value": [1,2,3]}
                        op = value.get("operator", "=")
                        val = value.get("value")
                        if val is not None:
                            conditions.append((field, op, val))
                    else:
                        # 简单条件
                        conditions.append((field, "=", value))

            # 应用条件
            if operator.lower() == "or":
                builder.or_(*[
                    lambda b, cond=cond: b.where(cond[0], cond[1], cond[2])
                    for cond in conditions
                ])
            else:
                for field, op, value in conditions:
                    builder.where(field, op, value)

            # 应用默认排序
            for field, direction in self.get_default_sorts():
                builder.add_sort(field, direction)

            return builder.build()
        finally:
            self.return_builder(builder)


class SpecificationFactory:
    """Specification工厂

    提供预定义的查询规范创建方法
    """

    @staticmethod
    def create_list_spec(
        includes: Optional[List[str]] = None,
        sorts: Optional[List[tuple]] = None,
        page: Optional[Dict[str, int]] = None
    ) -> Specification:
        """创建列表查询规范"""
        builder = SpecificationBuilder()

        if includes:
            for include in includes:
                builder.include(include)

        if sorts:
            for field, direction in sorts:
                builder.add_sort(field, direction)

        if page:
            builder.set_page(page=page.get('offset', 0) //
                             (page.get('limit') or 1) + 1, size=page.get('limit'))

        return builder.build()

    @staticmethod
    def create_detail_spec(
        entity_id: str,
        includes: Optional[List[str]] = None
    ) -> Specification:
        """创建详情查询规范"""
        builder = SpecificationBuilder()
        builder.by_id(entity_id)

        if includes:
            for include in includes:
                builder.include(include)

        return builder.build()

    @staticmethod
    def create_search_spec(
        search_text: str,
        search_fields: List[str],
        includes: Optional[List[str]] = None
    ) -> Specification:
        """创建搜索查询规范"""
        builder = SpecificationBuilder()

        # 文本搜索
        if len(search_fields) == 1:
            builder.text_search(search_fields[0], search_text)
        else:
            builder.or_(*[
                lambda b, field=field: b.text_search(field, search_text)
                for field in search_fields
            ])

        if includes:
            for include in includes:
                builder.include(include)

        return builder.build()


class SpecificationOptimizer:
    """Specification优化器

    提供查询规范的性能优化功能
    """

    @staticmethod
    def optimize_includes(spec: Specification, required_fields: List[str]) -> Specification:
        """优化包含关系"""
        # 移除不必要的包含关系
        if spec.includes:
            optimized_includes = [
                include for include in spec.includes
                if any(field.startswith(include) for field in required_fields)
            ]

            # 创建新的规范
            return Specification(
                filters=spec.filters,
                groups=spec.groups,
                sorts=spec.sorts,
                page=spec.page,
                fields=spec.fields,
                includes=optimized_includes,
                statistics=spec.statistics,
                group_by=spec.group_by,
                having=spec.having
            )
        return spec

    @staticmethod
    def add_default_sorts(spec: Specification, default_sorts: List[tuple]) -> Specification:
        """添加默认排序"""
        if not spec.sorts and default_sorts:
            sorts = [
                Sort(field=field, direction=direction)
                for field, direction in default_sorts
            ]
            return Specification(
                filters=spec.filters,
                groups=spec.groups,
                sorts=sorts,
                page=spec.page,
                fields=spec.fields,
                includes=spec.includes,
                statistics=spec.statistics,
                group_by=spec.group_by,
                having=spec.having
            )
        return spec
