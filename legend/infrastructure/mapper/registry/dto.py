"""数据传输对象映射器注册表模块。

提供数据传输对象映射器的注册表实现。

Key Components:
- DTOMapperRegistry: 数据传输对象映射器注册表
"""

from typing import Dict, Optional, Tuple, Type

from ..core.interfaces import Mapper
from .base import MapperRegistryImpl


class DTOMapperRegistry(MapperRegistryImpl):
    """数据传输对象映射器注册表
    
    管理领域对象和数据传输对象之间的映射器。
    """
    
    def __init__(self):
        """初始化数据传输对象映射器注册表"""
        super().__init__()
    
    def register_domain_to_dto(self, domain_type: Type, dto_type: Type, mapper: Mapper) -> None:
        """注册领域对象到数据传输对象的映射器
        
        Args:
            domain_type: 领域对象类型
            dto_type: 数据传输对象类型
            mapper: 映射器实例
        """
        self.register(domain_type, dto_type, mapper)
    
    def get_domain_to_dto(self, domain_type: Type, dto_type: Type) -> Optional[Mapper]:
        """获取领域对象到数据传输对象的映射器
        
        Args:
            domain_type: 领域对象类型
            dto_type: 数据传输对象类型
            
        Returns:
            Optional[Mapper]: 映射器实例，如果不存在则返回None
        """
        return self.get(domain_type, dto_type)
    
    def has_domain_to_dto(self, domain_type: Type, dto_type: Type) -> bool:
        """检查是否存在领域对象到数据传输对象的映射器
        
        Args:
            domain_type: 领域对象类型
            dto_type: 数据传输对象类型
            
        Returns:
            bool: 是否存在映射器
        """
        return self.has(domain_type, dto_type) 