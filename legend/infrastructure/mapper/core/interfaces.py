"""映射器核心接口模块。

定义映射器的基础接口和契约。

Key Components:
- Mapper: 基础映射器接口
- BidirectionalMapper: 双向映射器接口
- ConfigurableMapper: 可配置映射器接口
- MapperBuilder: 映射器构建器接口
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Callable, Any, Dict, Type, Optional, Union

# 类型变量
S = TypeVar('S')  # 源类型
T = TypeVar('T')  # 目标类型

class MappingContext:
    """映射上下文接口
    
    用于在映射过程中传递上下文信息，处理循环引用等。
    具体实现在context.py中。
    """
    pass

class Mapper(Generic[S, T], ABC):
    """基础映射器接口
    
    定义从源对象到目标对象的单向映射功能。
    """
    
    @abstractmethod
    def map_to_target(self, source: S, mapping_context: Optional[MappingContext] = None) -> T:
        """将源对象映射到目标对象
        
        Args:
            source: 源对象
            mapping_context: 可选的映射上下文，用于处理循环引用等
            
        Returns:
            T: 映射后的目标对象
        """
        pass
    
    def map_to_targets(self, sources: List[S], max_workers: int = 10) -> List[T]:
        """批量将源对象映射到目标对象
        
        默认实现基于单个对象映射方法。
        
        Args:
            sources: 源对象列表
            max_workers: 最大并行工作线程数，用于并行处理大批量数据
            
        Returns:
            List[T]: 映射后的目标对象列表
        """
        if not sources:
            return []
        return [self.map_to_target(s) for s in sources if s is not None]


class BidirectionalMapper(Mapper[S, T], Generic[S, T], ABC):
    """双向映射器接口
    
    扩展基础映射器接口，增加从目标对象到源对象的反向映射功能。
    """
    
    @abstractmethod
    def map_to_source(self, target: T, mapping_context: Optional[MappingContext] = None) -> S:
        """将目标对象映射回源对象
        
        Args:
            target: 目标对象
            mapping_context: 可选的映射上下文，用于处理循环引用等
            
        Returns:
            S: 映射后的源对象
        """
        pass
    
    def map_to_sources(self, targets: List[T], max_workers: int = 10) -> List[S]:
        """批量将目标对象映射回源对象
        
        默认实现基于单个对象映射方法。
        
        Args:
            targets: 目标对象列表
            max_workers: 最大并行工作线程数，用于并行处理大批量数据
            
        Returns:
            List[S]: 映射后的源对象列表
        """
        if not targets:
            return []
        return [self.map_to_source(t) for t in targets if t is not None]


class ConfigurableMapper(Mapper[S, T], Generic[S, T], ABC):
    """可配置映射器接口
    
    定义可在运行时配置映射规则的映射器接口。
    """
    
    @abstractmethod
    def configure_mapping(self, source_path: str, target_path: str) -> None:
        """配置源路径到目标路径的映射
        
        Args:
            source_path: 源对象属性路径，支持点号分隔的嵌套路径
            target_path: 目标对象属性路径，支持点号分隔的嵌套路径
        """
        pass
    
    @abstractmethod
    def configure_custom_mapping(self, target_path: str, mapping_func: Callable[[S], Any]) -> None:
        """配置自定义映射函数
        
        Args:
            target_path: 目标对象属性路径
            mapping_func: 映射函数，接收源对象作为参数，返回映射后的值
        """
        pass


class NestedMapper(Mapper[S, T], Generic[S, T], ABC):
    """嵌套映射器接口
    
    定义支持嵌套对象映射的映射器接口。
    """
    
    @abstractmethod
    def configure_nested_mapper(self, source_path: str, target_path: str, mapper: Mapper) -> None:
        """配置嵌套对象映射器
        
        Args:
            source_path: 源对象中嵌套对象的属性路径
            target_path: 目标对象中嵌套对象的属性路径
            mapper: 用于映射嵌套对象的映射器
        """
        pass
    
    @abstractmethod
    def configure_collection_mapper(self, source_path: str, target_path: str, mapper: Mapper) -> None:
        """配置集合对象映射器
        
        Args:
            source_path: 源对象中集合的属性路径
            target_path: 目标对象中集合的属性路径
            mapper: 用于映射集合中元素的映射器
        """
        pass


class IMapperBuilder(Generic[S, T], ABC):
    """映射器构建器接口
    
    定义用于构建和配置映射器的构建器接口。
    """
    
    @abstractmethod
    def for_types(self, source_type: Type[S], target_type: Type[T]) -> 'IMapperBuilder[S, T]':
        """指定源类型和目标类型
        
        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
            
        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        pass
    
    @abstractmethod
    def map(self, source_path: str, target_path: str) -> 'IMapperBuilder[S, T]':
        """配置属性映射
        
        Args:
            source_path: 源对象属性路径
            target_path: 目标对象属性路径
            
        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        pass
    
    @abstractmethod
    def map_custom(self, target_path: str, mapping_func: Callable[[S], Any]) -> 'IMapperBuilder[S, T]':
        """配置自定义映射函数
        
        Args:
            target_path: 目标对象属性路径
            mapping_func: 映射函数，接收源对象作为参数，返回映射后的值
            
        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        pass
    
    @abstractmethod
    def map_nested(self, source_path: str, target_path: str, mapper: Mapper) -> 'IMapperBuilder[S, T]':
        """配置嵌套对象映射
        
        Args:
            source_path: 源对象中嵌套对象的属性路径
            target_path: 目标对象中嵌套对象的属性路径
            mapper: 用于映射嵌套对象的映射器
            
        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        pass
    
    @abstractmethod
    def map_collection(self, source_path: str, target_path: str, mapper: Mapper) -> 'IMapperBuilder[S, T]':
        """配置集合映射
        
        Args:
            source_path: 源对象中集合的属性路径
            target_path: 目标对象中集合的属性路径
            mapper: 用于映射集合中元素的映射器
            
        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        pass
    
    @abstractmethod
    def auto_map(self, exclude_paths: Optional[List[str]] = None) -> 'IMapperBuilder[S, T]':
        """配置自动映射
        
        自动映射名称相同的属性。
        
        Args:
            exclude_paths: 排除自动映射的属性路径列表
            
        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        pass
    
    @abstractmethod
    def build(self) -> Mapper[S, T]:
        """构建映射器
        
        Returns:
            Mapper: 根据配置构建的映射器实例
        """
        pass


class MapperRegistry(ABC):
    """映射器注册表接口
    
    定义用于管理和获取映射器实例的注册表接口。
    """
    
    @abstractmethod
    def register(self, source_type: Type, target_type: Type, mapper: Mapper) -> None:
        """注册映射器
        
        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
            mapper: 映射器实例
        """
        pass
    
    @abstractmethod
    def get(self, source_type: Type, target_type: Type) -> Optional[Mapper]:
        """获取映射器
        
        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
            
        Returns:
            Optional[Mapper]: 映射器实例，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def has(self, source_type: Type, target_type: Type) -> bool:
        """检查是否存在映射器
        
        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
            
        Returns:
            bool: 是否存在映射器
        """
        pass 