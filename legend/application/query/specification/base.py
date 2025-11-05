from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from idp.framework.infrastructure.persistence.specification import SpecificationBuilder
from idp.framework.infrastructure.persistence.specification.core.base import (
    Specification,
)
from idp.framework.infrastructure.persistence.specification.core.type import (
    SortDirection,
)

TQuerySpec = TypeVar('TQuerySpec')


class BaseSpecificationFactory(Generic[TQuerySpec], ABC):
    """基础查询规范工厂

    提供通用的查询规范构建功能，具体聚合继承此类并实现业务特定逻辑。
    """

    def __init__(self):
        self.builder = SpecificationBuilder()

    @abstractmethod
    def get_entity_type(self) -> str:
        """获取实体类型名称，用于字段解析"""
        pass

    def build_by_id_spec(self, entity_id: str) -> Specification:
        """构建按ID查询规范"""
        return self.builder.filter("id", entity_id).build()

    def build_by_code_spec(self, code: str) -> Specification:
        """构建按代码查询规范"""
        return self.builder.filter("code", code).build()

    def build_by_name_spec(self, name: str) -> Specification:
        """构建按名称查询规范"""
        return self.builder.filter("name", name).build()

    def build_active_spec(self, active_field: str = "is_active") -> Specification:
        """构建活跃状态查询规范"""
        return self.builder.filter(active_field, True).build()

    def build_query_spec(self, query: TQuerySpec) -> Specification:
        """构建搜索规范（抽象方法，子类实现）"""
        raise NotImplementedError

    def build_paginated_spec(self, query: TQuerySpec, page: int, size: int) -> Specification:
        """构建分页查询规范"""
        spec = self.build_query_spec(query)
        return spec.set_page(page=page, size=size)

    def build_sorted_spec(self, query: TQuerySpec, sort_field: str, direction: SortDirection = SortDirection.ASC) -> Specification:
        """构建排序查询规范"""
        spec = self.build_query_spec(query)
        return spec.add_sort(sort_field, direction)
