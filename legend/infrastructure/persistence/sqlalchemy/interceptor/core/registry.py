"""SQLAlchemy拦截器注册表

提供拦截器的注册和管理功能。
支持按实体类型注册和获取拦截器。
"""

from typing import Dict, List, Type, TypeVar, ClassVar
from .base import Interceptor

T = TypeVar('T')

class InterceptorRegistry:
    """拦截器注册表
    
    管理实体类型与其关联的拦截器。
    支持动态注册和获取拦截器。
    
    Examples:
        >>> # 注册拦截器
        >>> InterceptorRegistry.register(UserPO, OptimisticLockInterceptor())
        >>> 
        >>> # 获取实体的所有拦截器
        >>> interceptors = InterceptorRegistry.get_interceptors(UserPO)
    """
    
    _registry: ClassVar[Dict[Type, List[Interceptor]]] = {}
    
    @classmethod
    def register(cls, entity_type: Type[T], interceptor: Interceptor[T]) -> None:
        """注册拦截器
        
        将拦截器注册到指定的实体类型。
        如果实体类型不存在，会创建新的拦截器列表。
        
        Args:
            entity_type: 实体类型
            interceptor: 要注册的拦截器
        """
        if entity_type not in cls._registry:
            cls._registry[entity_type] = []
        cls._registry[entity_type].append(interceptor)
    
    @classmethod
    def get_interceptors(cls, entity_type: Type[T]) -> List[Interceptor[T]]:
        """获取实体类型的所有拦截器
        
        返回指定实体类型的所有已注册拦截器，按优先级排序。
        
        Args:
            entity_type: 实体类型
            
        Returns:
            按优先级排序的拦截器列表
        """
        return sorted(
            cls._registry.get(entity_type, []),
            key=lambda x: x.priority
        )
    
    @classmethod
    def clear(cls) -> None:
        """清空注册表
        
        移除所有已注册的拦截器。
        通常用于测试或重置注册表。
        """
        cls._registry.clear()
    
    @classmethod
    def remove(cls, entity_type: Type[T], interceptor: Interceptor[T]) -> None:
        """移除指定实体类型的拦截器
        
        Args:
            entity_type: 实体类型
            interceptor: 要移除的拦截器
        """
        if entity_type in cls._registry:
            cls._registry[entity_type] = [
                i for i in cls._registry[entity_type]
                if i is not interceptor
            ]
            
    @classmethod
    def get_registered_types(cls) -> List[Type]:
        """获取所有已注册的实体类型
        
        Returns:
            已注册的实体类型列表
        """
        return list(cls._registry.keys())
