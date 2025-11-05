"""值对象映射器注册表模块。

提供值对象映射器的注册表实现。

Key Components:
- VOMapperRegistry: 值对象映射器注册表
"""

from typing import Dict, Optional, Tuple, Type

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.mapper import MapperExceptionCode

from ..core.interfaces import Mapper
from .base import MapperRegistryImpl


class VOMapperRegistry(MapperRegistryImpl):
    """值对象映射器注册表
    
    管理领域对象和值对象之间的映射器。
    """
    
    def __init__(self):
        """初始化值对象映射器注册表"""
        super().__init__()
    
    def register_domain_to_vo(self, domain_type: Type, vo_type: Type, mapper: Mapper) -> None:
        """注册领域对象到值对象的映射器
        
        Args:
            domain_type: 领域对象类型
            vo_type: 值对象类型
            mapper: 映射器实例
        """            
        try:
            self.register(domain_type, vo_type, mapper)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to register domain to VO mapper: {str(e)}",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"domain_type": str(domain_type), "vo_type": str(vo_type)},
                cause=e
            )
    
    def get_domain_to_vo(self, domain_type: Type, vo_type: Type) -> Optional[Mapper]:
        """获取领域对象到值对象的映射器
        
        Args:
            domain_type: 领域对象类型
            vo_type: 值对象类型
            
        Returns:
            Optional[Mapper]: 映射器实例，如果不存在则返回None
        """
        if not domain_type or not vo_type:
            raise idp_exception_factory.infrastructure_exception(
                message="Domain type and VO type cannot be None",
                code=InfrastructureExceptionCode.MAPPER_CONFIG_INVALID,
                details={"domain_type": str(domain_type), "vo_type": str(vo_type)}
            )
            
        try:
            mapper = self.get(domain_type, vo_type)
            if not mapper:
                # 返回None而不是抛出异常，因为这是一个查询操作
                return None
            return mapper
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to get domain to VO mapper: {str(e)}",
                code=MapperExceptionCode.MAPPER_NOT_FOUND,
                details={"domain_type": str(domain_type), "vo_type": str(vo_type)},
                cause=e
            )
    
    def has_domain_to_vo(self, domain_type: Type, vo_type: Type) -> bool:
        """检查是否存在领域对象到值对象的映射器
        
        Args:
            domain_type: 领域对象类型
            vo_type: 值对象类型
            
        Returns:
            bool: 是否存在映射器
        """
        if not domain_type or not vo_type:
            raise idp_exception_factory.infrastructure_exception(
                message="Domain type and VO type cannot be None",
                code=InfrastructureExceptionCode.MAPPER_CONFIG_INVALID,
                details={"domain_type": str(domain_type), "vo_type": str(vo_type)}
            )
            
        try:
            return self.has(domain_type, vo_type)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to check domain to VO mapper: {str(e)}",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"domain_type": str(domain_type), "vo_type": str(vo_type)},
                cause=e
            ) 