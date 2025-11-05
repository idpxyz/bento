"""值对象映射器基类模块。

提供值对象映射器的基类实现。

Key Components:
- VOMapper: 值对象映射器基类
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Generic, get_type_hints

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.mapper import MapperExceptionCode

from ..core.mapper import GenericMapper
from ..registry import vo_mapper_registry

# 类型变量
D = TypeVar('D')  # 领域对象类型
V = TypeVar('V')  # 值对象类型


class VOMapper(GenericMapper[D, V], Generic[D, V]):
    """值对象映射器基类
    
    提供领域对象和值对象之间的映射功能。
    """
    
    def __init__(self, domain_type: Type[D], vo_type: Type[V], auto_map: bool = True, exclude_paths: Optional[List[str]] = None):
        """初始化值对象映射器
        
        Args:
            domain_type: 领域对象类型
            vo_type: 值对象类型
            auto_map: 是否启用自动映射
            exclude_paths: 排除自动映射的属性路径列表
        """
        if not domain_type or not vo_type:
            raise idp_exception_factory.infrastructure_exception(
                message="Domain type and VO type cannot be None",
                code=InfrastructureExceptionCode.MAPPER_CONFIG_INVALID,
                details={"domain_type": str(domain_type), "vo_type": str(vo_type)}
            )
            
        try:
            super().__init__(domain_type, vo_type, auto_map, exclude_paths)
            
            # 注册到全局注册表
            vo_mapper_registry.register_domain_to_vo(domain_type, vo_type, self)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to initialize VO mapper: {str(e)}",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"domain_type": str(domain_type), "vo_type": str(vo_type)},
                cause=e
            )
    
    def to_vo(self, domain: D) -> V:
        """将领域对象映射到值对象
        
        Args:
            domain: 领域对象
            
        Returns:
            V: 映射后的值对象
        """
        if domain is None:
            return None
            
        try:
            return self.map_to_target(domain)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to map domain object to value object: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"domain_type": type(domain).__name__, "vo_type": str(self.target_type)},
                cause=e
            )
    
    def to_domain(self, vo: V) -> D:
        """将值对象映射到领域对象
        
        Args:
            vo: 值对象
            
        Returns:
            D: 映射后的领域对象
        """
        if vo is None:
            return None
            
        try:
            return self.map_to_source(vo)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to map value object to domain object: {str(e)}",
                code=MapperExceptionCode.MAPPER_REVERSE_CONFIG_INVALID,
                details={"vo_type": type(vo).__name__, "domain_type": str(self.source_type)},
                cause=e
            )
    
    def to_vos(self, domains: List[D]) -> List[V]:
        """批量将领域对象映射到值对象
        
        Args:
            domains: 领域对象列表
            
        Returns:
            List[V]: 映射后的值对象列表
        """
        if domains is None:
            return []
            
        try:
            return self.map_to_targets(domains)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to map domain objects to value objects: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"domains_count": len(domains), "vo_type": str(self.target_type)},
                cause=e
            )
    
    def to_domains(self, vos: List[V]) -> List[D]:
        """批量将值对象映射到领域对象
        
        Args:
            vos: 值对象列表
            
        Returns:
            List[D]: 映射后的领域对象列表
        """
        if vos is None:
            return []
            
        try:
            return self.map_to_sources(vos)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to map value objects to domain objects: {str(e)}",
                code=MapperExceptionCode.MAPPER_REVERSE_CONFIG_INVALID,
                details={"vos_count": len(vos), "domain_type": str(self.source_type)},
                cause=e
            ) 