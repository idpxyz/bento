"""重构后的查询服务基类

专注数据查询和转换，移除Specification构建职责。
Specification构建由独立的SpecificationService负责。

设计原则：
- 单一职责：专注数据查询和转换
- 依赖注入：通过SpecificationService获取查询规范
- 开闭原则：支持扩展新的查询方法
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from idp.framework.application.mapper import ApplicationMapper
from idp.framework.domain.repository import PageParams, PaginatedResult
from idp.framework.infrastructure.persistence.specification import Specification

TEntity = TypeVar('TEntity')  # 实体类型
TPO = TypeVar('TPO')  # PO类型
TDTO = TypeVar('TDTO')  # DTO类型


class BaseQueryService(Generic[TEntity, TPO, TDTO], ABC):
    """重构后的查询服务基类

    专注数据查询和转换，不负责Specification构建
    """

    def __init__(
        self,
        repository: Any,  # 仓储接口
        po_type: type,
        entity_type: type,
        dto_type: type
    ):
        self.repository = repository
        self.po_type = po_type
        self.entity_type = entity_type
        self.dto_type = dto_type

        # 自动配置映射器
        self._mapper = ApplicationMapper.create_pydantic_mapper(
            entity_type, dto_type
        )

    # ============ 核心查询方法 ============

    async def find_by_specification(self, spec: Specification) -> List[TDTO]:
        """根据Specification查询实体列表"""
        entities = await self.repository.query_by_spec(spec)
        return self.entities_to_dtos(entities)

    async def find_page_by_specification(
        self,
        spec: Specification,
        page_params: PageParams
    ) -> PaginatedResult[TDTO]:
        """根据Specification分页查询"""
        result = await self.repository.find_page_by_spec(spec, page_params)
        return PaginatedResult(
            items=self.entities_to_dtos(result.items),
            total=result.total,
            page=result.page,
            page_size=result.page_size
        )

    async def find_by_id(self, entity_id: str) -> Optional[TDTO]:
        """根据ID查询单个实体"""
        entity = await self.repository.get_by_id(entity_id)
        return self.entity_to_dto(entity) if entity else None

    async def find_all(self) -> List[TDTO]:
        """查询所有实体"""
        entities = await self.repository.find_all()
        return self.entities_to_dtos(entities)

    async def count_by_specification(self, spec: Specification) -> int:
        """根据Specification统计数量"""
        return await self.repository.count_by_spec(spec)

    async def exists_by_specification(self, spec: Specification) -> bool:
        """根据Specification检查是否存在"""
        return await self.repository.exists_by_spec(spec)

    # ============ 便捷查询方法 ============

    async def find_by_field(self, field: str, value: Any) -> List[TDTO]:
        """根据字段值查询"""
        spec = self._create_field_spec(field, value)
        return await self.find_by_specification(spec)

    async def find_by_fields(self, **filters) -> List[TDTO]:
        """根据多个字段值查询"""
        spec = self._create_fields_spec(**filters)
        return await self.find_by_specification(spec)

    async def find_by_code(self, code: str) -> Optional[TDTO]:
        """根据代码查询"""
        entities = await self.find_by_field("code", code)
        return entities[0] if entities else None

    async def find_by_name(self, name: str) -> Optional[TDTO]:
        """根据名称查询"""
        entities = await self.find_by_field("name", name)
        return entities[0] if entities else None

    # ============ 转换方法 ============

    def entity_to_dto(self, entity: TEntity) -> TDTO:
        """实体到DTO转换"""
        if entity is None:
            return None
        return self._mapper.map_to_dto(entity)

    def entities_to_dtos(self, entities: List[TEntity]) -> List[TDTO]:
        """实体列表到DTO列表转换"""
        if not entities:
            return []
        return [self.entity_to_dto(entity) for entity in entities]

    def dto_to_entity(self, dto: TDTO) -> TEntity:
        """DTO到实体转换"""
        if dto is None:
            return None
        return self._mapper.map_to_entity(dto)

    def dtos_to_entities(self, dtos: List[TDTO]) -> List[TEntity]:
        """DTO列表到实体列表转换"""
        if not dtos:
            return []
        return [self.dto_to_entity(dto) for dto in dtos]

    # ============ 私有方法 ============

    def _create_field_spec(self, field: str, value: Any) -> Specification:
        """创建单字段查询规范"""
        from idp.framework.infrastructure.persistence.specification import (
            SpecificationBuilder,
        )
        return SpecificationBuilder().filter(field, value).build()

    def _create_fields_spec(self, **filters) -> Specification:
        """创建多字段查询规范"""
        from idp.framework.infrastructure.persistence.specification import (
            SpecificationBuilder,
        )
        builder = SpecificationBuilder()
        for field, value in filters.items():
            if value is not None:
                builder.filter(field, value)
        return builder.build()


class BaseAggregateQueryService(BaseQueryService[TEntity, TPO, TDTO]):
    """聚合查询服务基类

    为聚合根提供特定的查询功能
    """

    async def find_with_children(self, entity_id: str) -> Optional[TDTO]:
        """查询聚合根及其子实体"""
        spec = self._create_detail_spec(entity_id)
        entities = await self.find_by_specification(spec)
        return entities[0] if entities else None

    async def find_all_with_children(self) -> List[TDTO]:
        """查询所有聚合根及其子实体"""
        spec = self._create_list_spec()
        return await self.find_by_specification(spec)

    def _create_detail_spec(self, entity_id: str) -> Specification:
        """创建详情查询规范"""
        from idp.framework.infrastructure.persistence.specification import (
            SpecificationBuilder,
        )
        return (SpecificationBuilder()
                .by_id(entity_id)
                .include(*self.get_default_includes())
                .build())

    def _create_list_spec(self) -> Specification:
        """创建列表查询规范"""
        from idp.framework.infrastructure.persistence.specification import (
            SpecificationBuilder,
        )
        builder = SpecificationBuilder()

        # 应用默认包含
        for include in self.get_default_includes():
            builder.include(include)

        # 应用默认排序
        for field, direction in self.get_default_sorts():
            builder.add_sort(field, direction)

        return builder.build()

    def get_default_includes(self) -> List[str]:
        """获取默认包含的关系 - 子类可重写"""
        return []

    def get_default_sorts(self) -> List[tuple]:
        """获取默认排序 - 子类可重写"""
        return [("created_at", "desc")]
