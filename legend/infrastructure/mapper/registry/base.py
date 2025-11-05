"""映射器注册表基础实现模块。

提供映射器注册表的基础实现。

Key Components:
- MapperRegistryImpl: 映射器注册表实现
"""

from typing import Dict, Optional, Tuple, Type

from ..core.interfaces import Mapper, MapperRegistry


class MapperRegistryImpl(MapperRegistry):
    """映射器注册表实现

    管理和获取映射器实例。
    """

    def __init__(self):
        """初始化映射器注册表"""
        self._mappers: Dict[Tuple[Type, Type], Mapper] = {}

    def register(self, source_type: Type, target_type: Type, mapper: Mapper) -> None:
        """注册映射器

        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
            mapper: 映射器实例
        """
        key = (source_type, target_type)
        self._mappers[key] = mapper

    def get(self, source_type: Type, target_type: Type) -> Optional[Mapper]:
        """获取映射器

        Args:
            source_type: 源对象类型
            target_type: 目标对象类型

        Returns:
            Optional[Mapper]: 映射器实例，如果不存在则返回None
        """
        if not source_type or not target_type:
            raise idp_exception_factory.infrastructure_exception(
                message="Source type and target type cannot be None",
                code=InfrastructureExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": str(
                    source_type), "target_type": str(target_type)}
            )

        key = (source_type, target_type)
        mapper = self._mappers.get(key)

        if not mapper:
            # 返回None而不是抛出异常，因为这是一个查询操作
            return None

        return mapper

    def has(self, source_type: Type, target_type: Type) -> bool:
        """检查是否存在映射器

        Args:
            source_type: 源对象类型
            target_type: 目标对象类型

        Returns:
            bool: 是否存在映射器
        """
        if not source_type or not target_type:
            raise idp_exception_factory.infrastructure_exception(
                message="Source type and target type cannot be None",
                code=InfrastructureExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": str(
                    source_type), "target_type": str(target_type)}
            )

        key = (source_type, target_type)
        return key in self._mappers

    def remove(self, source_type: Type, target_type: Type) -> None:
        """移除映射器

        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
        """
        if not source_type or not target_type:
            raise idp_exception_factory.infrastructure_exception(
                message="Source type and target type cannot be None",
                code=InfrastructureExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": str(
                    source_type), "target_type": str(target_type)}
            )

        key = (source_type, target_type)
        if key in self._mappers:
            del self._mappers[key]

    def clear(self) -> None:
        """清空注册表"""
        self._mappers.clear()

    def get_all(self) -> Dict[Tuple[Type, Type], Mapper]:
        """获取所有映射器

        Returns:
            Dict[Tuple[Type, Type], Mapper]: 所有注册的映射器
        """
        return self._mappers.copy()
