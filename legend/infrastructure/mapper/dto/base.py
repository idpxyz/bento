"""数据传输对象映射器基类模块。

提供数据传输对象映射器的基类实现。

Key Components:
- DTOMapper: 数据传输对象映射器基类
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Generic, get_type_hints

from ..core.mapper import GenericMapper
from ..registry import dto_mapper_registry

# 类型变量
D = TypeVar('D')  # 领域对象类型
T = TypeVar('T')  # 数据传输对象类型


class DTOMapper(GenericMapper[D, T], Generic[D, T]):
    """数据传输对象映射器基类
    
    提供领域对象和数据传输对象之间的映射功能。
    """
    
    def __init__(self, domain_type: Type[D], dto_type: Type[T], auto_map: bool = True, exclude_paths: Optional[List[str]] = None):
        """初始化数据传输对象映射器
        
        Args:
            domain_type: 领域对象类型
            dto_type: 数据传输对象类型
            auto_map: 是否启用自动映射
            exclude_paths: 排除自动映射的属性路径列表
        """
        super().__init__(domain_type, dto_type, auto_map, exclude_paths)
        
        # 注册到全局注册表
        dto_mapper_registry.register_domain_to_dto(domain_type, dto_type, self)
    
    def to_dto(self, domain: D) -> T:
        """将领域对象映射到数据传输对象
        
        Args:
            domain: 领域对象
            
        Returns:
            T: 映射后的数据传输对象
        """
        return self.map_to_target(domain)
    
    def to_domain(self, dto: T) -> D:
        """将数据传输对象映射到领域对象
        
        Args:
            dto: 数据传输对象
            
        Returns:
            D: 映射后的领域对象
        """
        return self.map_to_source(dto)
    
    def to_dtos(self, domains: List[D]) -> List[T]:
        """批量将领域对象映射到数据传输对象
        
        Args:
            domains: 领域对象列表
            
        Returns:
            List[T]: 映射后的数据传输对象列表
        """
        return self.map_to_targets(domains)
    
    def to_domains(self, dtos: List[T]) -> List[D]:
        """批量将数据传输对象映射到领域对象
        
        Args:
            dtos: 数据传输对象列表
            
        Returns:
            List[D]: 映射后的领域对象列表
        """
        return self.map_to_sources(dtos) 