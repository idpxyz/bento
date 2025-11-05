"""增强版查询处理器基类

提供统一的查询处理器基类，集成映射器支持和通用映射方法。

设计目标：
- 减少子类重复代码
- 统一映射策略
- 提供类型安全的映射接口
- 支持多种映射场景
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Protocol, Type, TypeVar

from idp.framework.application.mapper import ApplicationMapper, create_pydantic_mapper
from idp.framework.domain.model.aggregate import AggregateRoot

# 定义泛型变量
TQuery = TypeVar('TQuery')      # 查询对象类型 (例如 GetUserByIdQuery)
TResult = TypeVar('TResult')    # 查询结果DTO类型 (例如 UserDTO)
TEntity = TypeVar('TEntity', bound=AggregateRoot)  # 聚合根实体类型
TDetailEntity = TypeVar('TDetailEntity')  # 详情实体类型
TDetailDTO = TypeVar('TDetailDTO')  # 详情DTO类型


class IQueryHandler(Protocol, Generic[TQuery, TResult]):
    """
    查询处理器接口协议。

    它定义了一个单一的 handle 方法，作为所有查询用例的统一入口点。
    这是CQRS（命令查询责任分离）模式中"查询"部分的典型实现。
    """

    async def handle(self, query: TQuery) -> TResult:
        """
        处理给定的查询对象。

        Args:
            query: 封装了查询参数的查询对象。

        Returns:
            查询结果，通常是一个DTO或DTO列表。
        """
        ...


class BaseQueryHandler(ABC, Generic[TQuery, TResult]):
    """
    查询处理器抽象基类。

    提供了一个抽象的 handle 方法，强制子类实现业务逻辑。
    继承此类可以帮助确保所有处理器都遵循统一的结构。
    """
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """
        处理给定的查询对象。

        Args:
            query: 封装了查询参数的查询对象。

        Returns:
            查询结果，通常是一个DTO或DTO列表。
        """
        raise NotImplementedError


class MappedQueryHandler(BaseQueryHandler[TQuery, TResult], Generic[TQuery, TResult, TEntity]):
    """
    带映射功能的查询处理器基类。

    提供通用的映射功能，减少子类的重复代码。

    类型参数:
        TQuery: 查询对象类型
        TResult: 查询结果DTO类型
        TEntity: 聚合根实体类型
    """

    def __init__(
        self,
        entity_type: Type[TEntity],
        result_type: Type[TResult],
        mapper: Optional[ApplicationMapper[TEntity, TResult]] = None
    ):
        """初始化带映射功能的查询处理器

        Args:
            entity_type: 聚合根实体类型
            result_type: 查询结果DTO类型
            mapper: 可选的自定义映射器，如果不提供则使用默认Pydantic映射器
        """
        self._entity_type = entity_type
        self._result_type = result_type

        # 初始化映射器
        if mapper is not None:
            self._mapper = mapper
        else:
            # 使用默认的 Pydantic 映射器
            self._mapper = create_pydantic_mapper(entity_type, result_type)

    def map_entity_to_dto(self, entity: TEntity) -> TResult:
        """将聚合根实体映射为DTO

        Args:
            entity: 聚合根实体

        Returns:
            映射后的DTO对象
        """
        return self._mapper.map_entity_to_dto(entity)

    def map_entities_to_dtos(self, entities: List[TEntity]) -> List[TResult]:
        """批量将聚合根实体映射为DTO列表

        Args:
            entities: 聚合根实体列表

        Returns:
            映射后的DTO列表
        """
        return self._mapper.map_entities_to_dtos(entities)

    def map_optional_entity_to_dto(self, entity: Optional[TEntity]) -> Optional[TResult]:
        """将可选的聚合根实体映射为可选的DTO

        Args:
            entity: 可选的聚合根实体

        Returns:
            映射后的DTO对象，如果实体为None则返回None
        """
        if entity is None:
            return None
        return self.map_entity_to_dto(entity)

    @property
    def mapper(self) -> ApplicationMapper[TEntity, TResult]:
        """获取映射器实例"""
        return self._mapper


class DetailMappedQueryHandler(MappedQueryHandler[TQuery, TResult, TEntity],
                               Generic[TQuery, TResult, TEntity, TDetailEntity, TDetailDTO]):
    """
    带详情映射功能的查询处理器基类。

    支持聚合根和详情实体的双重映射，适用于包含详情列表的查询场景。

    类型参数:
        TQuery: 查询对象类型
        TResult: 查询结果DTO类型（包含详情列表）
        TEntity: 聚合根实体类型
        TDetailEntity: 详情实体类型
        TDetailDTO: 详情DTO类型
    """

    def __init__(
        self,
        entity_type: Type[TEntity],
        result_type: Type[TResult],
        detail_entity_type: Type[TDetailEntity],
        detail_dto_type: Type[TDetailDTO],
        entity_mapper: Optional[ApplicationMapper[TEntity, TResult]] = None,
        detail_mapper: Optional[ApplicationMapper[TDetailEntity,
                                                  TDetailDTO]] = None
    ):
        """初始化带详情映射功能的查询处理器

        Args:
            entity_type: 聚合根实体类型
            result_type: 查询结果DTO类型
            detail_entity_type: 详情实体类型
            detail_dto_type: 详情DTO类型
            entity_mapper: 可选的主实体映射器
            detail_mapper: 可选的详情映射器
        """
        super().__init__(entity_type, result_type, entity_mapper)

        self._detail_entity_type = detail_entity_type
        self._detail_dto_type = detail_dto_type

        # 初始化详情映射器
        if detail_mapper is not None:
            self._detail_mapper = detail_mapper
        else:
            # 使用默认的 Pydantic 映射器
            self._detail_mapper = create_pydantic_mapper(
                detail_entity_type, detail_dto_type)

    def map_detail_entities_to_dtos(self, detail_entities: List[TDetailEntity]) -> List[TDetailDTO]:
        """将详情实体列表映射为详情DTO列表

        Args:
            detail_entities: 详情实体列表

        Returns:
            映射后的详情DTO列表
        """
        return self._detail_mapper.map_entities_to_dtos(detail_entities)

    def map_entity_with_details_to_dto(
        self,
        entity: TEntity,
        details_attr: str = "details"
    ) -> TResult:
        """将包含详情列表的聚合根实体映射为包含详情DTO的DTO

        Args:
            entity: 聚合根实体
            details_attr: 详情列表属性名，默认为"details"

        Returns:
            包含详情DTO的DTO对象
        """
        # 映射主实体
        entity_dto = self.map_entity_to_dto(entity)

        # 获取详情列表
        detail_entities = getattr(entity, details_attr, [])

        # 映射详情列表
        detail_dtos = self.map_detail_entities_to_dtos(detail_entities)

        # 创建包含详情的DTO
        # 注意：这里假设 result_type 有 details 字段
        # 如果结构不同，子类可以重写此方法
        if hasattr(entity_dto, 'model_dump'):
            # Pydantic 模型
            dto_data = entity_dto.model_dump()
            dto_data[details_attr] = detail_dtos
            return self._result_type(**dto_data)
        else:
            # 普通对象
            result = self._result_type()
            for attr, value in entity_dto.__dict__.items():
                setattr(result, attr, value)
            setattr(result, details_attr, detail_dtos)
            return result

    @property
    def detail_mapper(self) -> ApplicationMapper[TDetailEntity, TDetailDTO]:
        """获取详情映射器实例"""
        return self._detail_mapper


# 便捷的工厂函数
def create_mapped_query_handler(
    entity_type: Type[TEntity],
    result_type: Type[TResult],
    mapper: Optional[ApplicationMapper[TEntity, TResult]] = None
) -> Type[MappedQueryHandler[TQuery, TResult, TEntity]]:
    """创建带映射功能的查询处理器类

    Args:
        entity_type: 聚合根实体类型
        result_type: 查询结果DTO类型
        mapper: 可选的自定义映射器

    Returns:
        配置好的查询处理器类
    """
    class ConfiguredHandler(MappedQueryHandler[TQuery, TResult, TEntity]):
        def __init__(self):
            super().__init__(entity_type, result_type, mapper)

    return ConfiguredHandler


def create_detail_mapped_query_handler(
    entity_type: Type[TEntity],
    result_type: Type[TResult],
    detail_entity_type: Type[TDetailEntity],
    detail_dto_type: Type[TDetailDTO],
    entity_mapper: Optional[ApplicationMapper[TEntity, TResult]] = None,
    detail_mapper: Optional[ApplicationMapper[TDetailEntity,
                                              TDetailDTO]] = None
) -> Type[DetailMappedQueryHandler[TQuery, TResult, TEntity, TDetailEntity, TDetailDTO]]:
    """创建带详情映射功能的查询处理器类

    Args:
        entity_type: 聚合根实体类型
        result_type: 查询结果DTO类型
        detail_entity_type: 详情实体类型
        detail_dto_type: 详情DTO类型
        entity_mapper: 可选的主实体映射器
        detail_mapper: 可选的详情映射器

    Returns:
        配置好的查询处理器类
    """
    class ConfiguredDetailHandler(DetailMappedQueryHandler[TQuery, TResult, TEntity, TDetailEntity, TDetailDTO]):
        def __init__(self):
            super().__init__(
                entity_type, result_type, detail_entity_type, detail_dto_type,
                entity_mapper, detail_mapper
            )

    return ConfiguredDetailHandler
