"""基础查询服务

提供通用的查询服务基类，集成JsonSpecParser和仓储操作，
简化具体聚合查询服务的实现。

现代化特点：
- 集成 ApplicationMapper 统一映射标准
- 消除抽象的 entity_to_dto 方法
- 提供多种映射器策略支持
- 自动 Pydantic 映射器配置
- 保持向后兼容性
"""

from abc import ABC
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from idp.framework.application.mapper import ApplicationMapper, create_pydantic_mapper
from idp.framework.domain.model.aggregate import AggregateRoot
from idp.framework.domain.repository import PageParams, PaginatedResult
from idp.framework.infrastructure.persistence.sqlalchemy.po.base import BasePO

# 类型变量定义
TEntity = TypeVar('TEntity', bound=AggregateRoot)
TPO = TypeVar('TPO', bound=BasePO)
TDTO = TypeVar('TDTO')


class BaseQueryService(Generic[TEntity, TPO, TDTO], ABC):
    """基础查询服务类

    提供通用的JSON规范查询功能，具体的聚合查询服务可以继承此类。

    类型参数:
        TEntity: 聚合根实体类型
        TPO: 持久化对象类型
        TDTO: 数据传输对象类型

    现代化特点:
        - 内置 ApplicationMapper 支持
        - 自动 Pydantic 映射器配置
        - 统一的映射接口
        - 消除手动映射代码

    职责:
        1. 提供统一的JSON规范查询接口
        2. 集成JsonSpecParser处理JSON查询规范
        3. 协调仓储操作和DTO转换
        4. 提供常用的便捷查询方法

    使用示例:
        ```python
        class OptionCategoryQueryService(BaseQueryService[OptionCategory, OptionCategoryPO, OptionCategoryDTO]):
            def __init__(self, repository: OptionCategoryRepository):
                super().__init__(
                    repository=repository,
                    po_type=OptionCategoryPO,
                    entity_type=OptionCategory,
                    dto_type=OptionCategoryDTO
                )
        ```
    """

    def __init__(
        self,
        repository,
        po_type: Type[TPO],
        entity_type: Optional[Type[TEntity]] = None,
        dto_type: Optional[Type[TDTO]] = None,
        mapper: Optional[ApplicationMapper[TEntity, TDTO]] = None
    ):
        """初始化基础查询服务

        Args:
            repository: 仓储接口实现
            po_type: 持久化对象类型，用于初始化JsonSpecParser
            entity_type: 实体类型（新增，用于映射器）
            dto_type: DTO类型（新增，用于映射器）
            mapper: 可选的自定义映射器，如果不提供则使用默认Pydantic映射器

        Note:
            为了保持向后兼容性，entity_type 和 dto_type 是可选的。
            如果不提供，则回退到原有的抽象方法模式。
        """
        self.repository = repository
        self.po_type = po_type
        self.entity_type = entity_type
        self.dto_type = dto_type

        # 初始化映射器（如果提供了类型信息）
        if entity_type is not None and dto_type is not None:
            if mapper is not None:
                self._mapper = mapper
            else:
                # 使用默认的 Pydantic 映射器
                self._mapper = create_pydantic_mapper(entity_type, dto_type)
        else:
            self._mapper = None

        # 延迟初始化 JsonSpecParser
        self._json_spec_parser = None

    @property
    def json_spec_parser(self):
        """延迟初始化JsonSpecParser"""
        if self._json_spec_parser is None:
            from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.json_spec_parser import (
                JsonSpecParser,
            )
            self._json_spec_parser = JsonSpecParser(self.po_type)
        return self._json_spec_parser

    @property
    def mapper(self) -> Optional[ApplicationMapper[TEntity, TDTO]]:
        """获取映射器实例"""
        return self._mapper

    def entity_to_dto(self, entity: TEntity) -> TDTO:
        """将实体转换为DTO

        现代化实现：优先使用配置的应用层映射器进行转换。
        如果没有配置映射器，则回退到子类实现的抽象方法（向后兼容）。

        Args:
            entity: 聚合根实体

        Returns:
            对应的DTO对象

        Note:
            子类可以重写此方法来定义自定义转换逻辑，
            但推荐使用映射器配置方式。
        """
        if self._mapper is not None:
            # 使用现代化的映射器
            return self._mapper.map_entity_to_dto(entity)
        else:
            # 向后兼容：子类必须重写此方法
            raise NotImplementedError(
                "Either provide entity_type and dto_type in constructor, "
                "or override entity_to_dto method in subclass"
            )

    def entities_to_dtos(self, entities: List[TEntity]) -> List[TDTO]:
        """批量将实体转换为DTO

        Args:
            entities: 聚合根实体列表

        Returns:
            DTO对象列表
        """
        if self._mapper is not None:
            # 使用映射器的批量转换
            return self._mapper.map_entities_to_dtos(entities)
        else:
            # 向后兼容：使用循环调用
            return [self.entity_to_dto(entity) for entity in entities]

    def optional_entity_to_dto(self, entity: Optional[TEntity]) -> Optional[TDTO]:
        """将可选实体转换为可选DTO

        Args:
            entity: 可选的聚合根实体

        Returns:
            可选的DTO对象
        """
        if self._mapper is not None:
            return self._mapper.map_optional_entity_to_dto(entity)
        else:
            # 向后兼容
            if entity is None:
                return None
            return self.entity_to_dto(entity)

    # ============ JSON规范查询方法 ============

    async def query_by_json_spec(
        self,
        json_spec: Dict[str, Any],
        page_params: Optional[PageParams] = None
    ) -> PaginatedResult[TDTO]:
        """使用JSON规范查询实体（分页）

        Args:
            json_spec: JSON查询规范
            page_params: 分页参数

        Returns:
            分页查询结果

        Example:
            ```python
            json_spec = {
                "filters": [
                    {"field": "name", "operator": "contains", "value": "test"},
                    {"field": "is_active", "operator": "equals", "value": True}
                ],
                "sorts": [{"field": "created_at", "direction": "desc"}],
                "includes": ["details"]
            }
            result = await service.query_by_json_spec(json_spec, page_params)
            ```
        """
        # Infrastructure层：JSON -> Specification转换
        spec = self.json_spec_parser.parse(json_spec)

        # 如果没有分页参数，使用默认分页
        if page_params is None:
            page_params = PageParams(page=1, page_size=20)

        # Domain层：使用纯净的Specification对象
        result = await self.repository.find_page_by_spec(spec, page_params)

        # 使用映射器转换为DTO
        dto_items = self.entities_to_dtos(result.items)

        return PaginatedResult(
            items=dto_items,
            total=result.total,
            page=result.page,
            page_size=result.page_size
        )

    async def search_by_json_spec(self, json_spec: Dict[str, Any]) -> List[TDTO]:
        """使用JSON规范搜索实体（不分页）

        Args:
            json_spec: JSON查询规范

        Returns:
            实体DTO列表
        """
        spec = self.json_spec_parser.parse(json_spec)
        entities = await self.repository.find_all_by_spec(spec)
        return self.entities_to_dtos(entities)

    async def count_by_json_spec(self, json_spec: Dict[str, Any]) -> int:
        """使用JSON规范统计实体数量

        Args:
            json_spec: JSON查询规范

        Returns:
            实体数量
        """
        spec = self.json_spec_parser.parse(json_spec)
        return await self.repository.count_by_spec(spec)

    async def exists_by_json_spec(self, json_spec: Dict[str, Any]) -> bool:
        """使用JSON规范检查实体是否存在

        Args:
            json_spec: JSON查询规范

        Returns:
            是否存在匹配的实体
        """
        spec = self.json_spec_parser.parse(json_spec)
        return await self.repository.exists_by_spec(spec)

    async def get_by_id(self, entity_id: str) -> Optional[TDTO]:
        """根据ID获取单个实体

        Args:
            entity_id: 实体ID

        Returns:
            实体DTO或None
        """
        entity = await self.repository.get_by_id(entity_id)
        return self.optional_entity_to_dto(entity)

    async def find_by_ids(self, entity_ids: List[str]) -> List[TDTO]:
        """根据ID列表批量获取实体

        Args:
            entity_ids: 实体ID列表

        Returns:
            实体DTO列表
        """
        entities = await self.repository.find_by_ids(entity_ids)
        return self.entities_to_dtos(entities)

    # ============ 便捷查询方法 ============

    async def find_active(self, additional_filters: Optional[List[Dict[str, Any]]] = None) -> List[TDTO]:
        """查找活跃的实体

        Args:
            additional_filters: 额外的过滤条件

        Returns:
            活跃实体DTO列表
        """
        filters = [{"field": "is_active", "operator": "equals", "value": True}]
        if additional_filters:
            filters.extend(additional_filters)

        json_spec = {"filters": filters}
        return await self.search_by_json_spec(json_spec)

    async def find_by_code(self, code: str) -> Optional[TDTO]:
        """根据代码查找实体

        Args:
            code: 实体代码

        Returns:
            实体DTO或None
        """
        json_spec = {
            "filters": [{"field": "code", "operator": "equals", "value": code}]
        }
        results = await self.search_by_json_spec(json_spec)
        return results[0] if results else None

    async def find_by_code_pattern(self, code_pattern: str) -> List[TDTO]:
        """根据代码模式查找实体

        Args:
            code_pattern: 代码模式

        Returns:
            匹配的实体DTO列表
        """
        json_spec = {
            "filters": [
                {"field": "code", "operator": "like", "value": f"%{code_pattern}%"}
            ],
            "sorts": [{"field": "code", "direction": "asc"}]
        }
        return await self.search_by_json_spec(json_spec)

    async def find_by_name_pattern(self, name_pattern: str) -> List[TDTO]:
        """根据名称模式查找实体

        Args:
            name_pattern: 名称模式

        Returns:
            匹配的实体DTO列表
        """
        json_spec = {
            "filters": [
                {"field": "name", "operator": "contains", "value": name_pattern}
            ],
            "sorts": [{"field": "name", "direction": "asc"}]
        }
        return await self.search_by_json_spec(json_spec)

    async def find_created_after(self, date_time: str) -> List[TDTO]:
        """查找指定时间后创建的实体

        Args:
            date_time: 时间字符串 (ISO格式)

        Returns:
            实体DTO列表
        """
        json_spec = {
            "filters": [
                {"field": "created_at", "operator": "greater_than", "value": date_time}
            ],
            "sorts": [{"field": "created_at", "direction": "desc"}]
        }
        return await self.search_by_json_spec(json_spec)

    async def find_created_between(self, start_date: str, end_date: str) -> List[TDTO]:
        """查找在指定时间范围内创建的实体

        Args:
            start_date: 开始时间 (ISO格式)
            end_date: 结束时间 (ISO格式)

        Returns:
            实体DTO列表
        """
        json_spec = {
            "filters": [
                {
                    "field": "created_at",
                    "operator": "between",
                    "value": [start_date, end_date]
                }
            ],
            "sorts": [{"field": "created_at", "direction": "desc"}]
        }
        return await self.search_by_json_spec(json_spec)

    async def find_all(self) -> List[TDTO]:
        """查找所有实体

        Returns:
            所有实体DTO列表
        """
        return await self.search_by_json_spec({})
    

    # 扩展点方法，子类可以重写
    def get_default_includes(self) -> List[str]:
        """获取默认的关联加载字段

        Returns:
            默认包含的关联字段列表

        Note:
            子类可以重写此方法来定义默认的关联加载
        """
        return []

    def get_default_sorts(self) -> List[Dict[str, str]]:
        """获取默认的排序字段

        Returns:
            默认排序配置

        Note:
            子类可以重写此方法来定义默认排序
        """
        return [{"field": "created_at", "direction": "desc"}]

    async def find_with_defaults(self, additional_spec: Optional[Dict[str, Any]] = None) -> List[TDTO]:
        """使用默认配置查找实体

        Args:
            additional_spec: 额外的查询规范

        Returns:
            实体DTO列表
        """
        json_spec = {
            "includes": self.get_default_includes(),
            "sorts": self.get_default_sorts()
        }

        # 合并额外的查询规范
        if additional_spec:
            json_spec.update(additional_spec)

        return await self.search_by_json_spec(json_spec)


class BaseAggregateQueryService(BaseQueryService[TEntity, TPO, TDTO]):
    """基础聚合查询服务

    专门针对聚合根的查询服务，提供软删除等聚合特有功能。
    """

    async def find_not_deleted(self, additional_filters: Optional[List[Dict[str, Any]]] = None) -> List[TDTO]:
        """查找未删除的实体

        Args:
            additional_filters: 额外的过滤条件

        Returns:
            未删除的实体DTO列表
        """
        filters = [{"field": "is_deleted",
                    "operator": "equals", "value": False}]
        if additional_filters:
            filters.extend(additional_filters)

        json_spec = {"filters": filters}
        return await self.search_by_json_spec(json_spec)

    async def find_by_version(self, version: int) -> List[TDTO]:
        """根据版本号查找实体

        Args:
            version: 版本号

        Returns:
            指定版本的实体DTO列表
        """
        json_spec = {
            "filters": [{"field": "version", "operator": "equals", "value": version}]
        }
        return await self.search_by_json_spec(json_spec)

    async def find_latest_version(self, group_by_field: str = "code") -> List[TDTO]:
        """查找每个分组的最新版本实体

        Args:
            group_by_field: 分组字段名，默认为"code"

        Returns:
            每个分组最新版本的实体DTO列表
        """
        json_spec = {
            "filters": [{"field": "is_deleted", "operator": "equals", "value": False}],
            "sorts": [{"field": "version", "direction": "desc"}],
            "group_by": group_by_field
        }
        return await self.search_by_json_spec(json_spec)

    async def find_all(self) -> List[TDTO]:
        """查找所有实体

        Returns:
            所有实体DTO列表
        """
        return await self.search_by_json_spec({})