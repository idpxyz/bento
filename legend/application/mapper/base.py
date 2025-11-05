"""应用层映射器基础架构

提供应用层统一的 Entity → DTO 映射器基础类和接口。

设计目标：
- 统一应用层映射器标准
- 简化 QueryService 中的映射逻辑
- 提供类型安全的映射接口
- 支持多种映射策略（Pydantic、Framework Mapper等）
- 保持架构分层的清晰性

架构原则：
- 应用层映射器专注于 Entity → DTO 转换
- 不依赖基础设施层的具体实现
- 提供可扩展的映射策略接口
- 支持批量映射和性能优化
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from idp.framework.domain.model.aggregate import AggregateRoot

# 类型变量定义
TEntity = TypeVar('TEntity', bound=AggregateRoot)  # 聚合根实体类型
TDTO = TypeVar('TDTO')  # 数据传输对象类型


class ApplicationMapper(Generic[TEntity, TDTO], ABC):
    """应用层映射器接口

    定义应用层 Entity → DTO 映射的标准接口。

    类型参数:
        TEntity: 聚合根实体类型
        TDTO: 数据传输对象类型

    职责:
        - 提供类型安全的映射接口
        - 支持单个和批量映射
        - 处理空值和异常情况
        - 提供映射性能监控点
    """

    @abstractmethod
    def map_entity_to_dto(self, entity: TEntity) -> TDTO:
        """将实体映射为DTO

        Args:
            entity: 聚合根实体

        Returns:
            TDTO: 映射后的DTO对象

        Raises:
            MappingException: 映射过程中发生错误时
        """
        pass

    def map_entities_to_dtos(self, entities: List[TEntity]) -> List[TDTO]:
        """批量将实体映射为DTO列表

        Args:
            entities: 聚合根实体列表

        Returns:
            List[TDTO]: 映射后的DTO列表

        Note:
            默认实现使用循环调用单个映射方法，子类可以重写以提供优化实现
        """
        if not entities:
            return []

        return [self.map_entity_to_dto(entity) for entity in entities]

    def map_optional_entity_to_dto(self, entity: Optional[TEntity]) -> Optional[TDTO]:
        """将可选实体映射为可选DTO

        Args:
            entity: 可选的聚合根实体

        Returns:
            Optional[TDTO]: 映射后的DTO对象，如果实体为None则返回None
        """
        if entity is None:
            return None
        return self.map_entity_to_dto(entity)

    def get_entity_type(self) -> type:
        """获取实体类型

        Returns:
            type: 实体类型

        Note:
            子类可以重写此方法提供运行时类型信息
        """
        # 通过泛型参数获取类型信息
        import typing
        if hasattr(self, '__orig_bases__'):
            for base in self.__orig_bases__:
                if hasattr(base, '__args__') and len(base.__args__) >= 1:
                    return base.__args__[0]
        return object

    def get_dto_type(self) -> type:
        """获取DTO类型

        Returns:
            type: DTO类型

        Note:
            子类可以重写此方法提供运行时类型信息
        """
        # 通过泛型参数获取类型信息
        import typing
        if hasattr(self, '__orig_bases__'):
            for base in self.__orig_bases__:
                if hasattr(base, '__args__') and len(base.__args__) >= 2:
                    return base.__args__[1]
        return object


class BaseApplicationMapper(ApplicationMapper[TEntity, TDTO], Generic[TEntity, TDTO]):
    """应用层映射器基础实现

    提供应用层映射器的通用基础实现，支持多种映射策略。

    特点:
        - 基于 Pydantic 的高性能映射
        - 类型安全的泛型支持
        - 统一的错误处理
        - 可扩展的映射策略

    使用示例:
        ```python
        class OptionCategoryMapper(BaseApplicationMapper[OptionCategory, OptionCategoryDTO]):
            pass

        mapper = OptionCategoryMapper()
        dto = mapper.map_entity_to_dto(entity)
        ```
    """

    def __init__(self, entity_type: type, dto_type: type):
        """初始化基础应用映射器

        Args:
            entity_type: 实体类型
            dto_type: DTO类型
        """
        self._entity_type = entity_type
        self._dto_type = dto_type

    def map_entity_to_dto(self, entity: TEntity) -> TDTO:
        """将实体映射为DTO

        使用 Pydantic 的 model_validate 方法进行高效映射。

        Args:
            entity: 聚合根实体

        Returns:
            TDTO: 映射后的DTO对象

        Raises:
            ValueError: 当实体为None时
            ValidationError: 当映射过程中发生验证错误时
        """
        if entity is None:
            raise ValueError("Entity cannot be None")

        try:
            # 使用 Pydantic 的 from_attributes 功能进行映射
            return self._dto_type.model_validate(entity, from_attributes=True)
        except Exception as e:
            # 包装异常，提供更好的错误信息
            raise ValueError(
                f"Failed to map {self._entity_type.__name__} to {self._dto_type.__name__}: {str(e)}"
            ) from e

    def get_entity_type(self) -> type:
        """获取实体类型"""
        return self._entity_type

    def get_dto_type(self) -> type:
        """获取DTO类型"""
        return self._dto_type


class PydanticApplicationMapper(BaseApplicationMapper[TEntity, TDTO]):
    """基于 Pydantic 的应用层映射器

    专门针对 Pydantic DTO 优化的映射器实现。

    特点:
        - 充分利用 Pydantic 的 from_attributes 功能
        - 高性能的批量映射
        - 自动类型验证和转换
        - 支持复杂嵌套对象映射

    适用场景:
        - DTO 基于 Pydantic BaseModel
        - 需要自动类型验证
        - 实体属性名与 DTO 字段名一致
        - 需要高性能映射
    """

    def map_entities_to_dtos(self, entities: List[TEntity]) -> List[TDTO]:
        """批量映射实体为DTO列表

        针对 Pydantic 优化的批量映射实现。

        Args:
            entities: 聚合根实体列表

        Returns:
            List[TDTO]: 映射后的DTO列表
        """
        if not entities:
            return []

        # 对于 Pydantic，单个映射已经足够高效
        # 未来可以考虑并行映射优化
        return [self.map_entity_to_dto(entity) for entity in entities]


def create_pydantic_mapper(entity_type: type, dto_type: type) -> PydanticApplicationMapper:
    """创建 Pydantic 应用映射器的工厂函数

    Args:
        entity_type: 实体类型
        dto_type: DTO类型

    Returns:
        PydanticApplicationMapper: 配置好的映射器实例

    Example:
        ```python
        mapper = create_pydantic_mapper(OptionCategory, OptionCategoryDTO)
        dto = mapper.map_entity_to_dto(entity)
        ```
    """
    return PydanticApplicationMapper(entity_type, dto_type)


# 便捷的类型别名
EntityToDTOMapper = ApplicationMapper
