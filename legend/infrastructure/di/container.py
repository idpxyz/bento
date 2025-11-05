# idp/core/infrastructure/di/container.py
from typing import Dict, Any, Type, Callable, Optional, List, Set
import inspect

class DependencyContainer:
    """
    依赖注入容器
    
    管理应用程序的依赖关系
    """
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[['DependencyContainer'], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def register(self, service_type: Type, implementation: Any = None) -> None:
        """
        注册服务
        
        Args:
            service_type: 服务类型
            implementation: 实现类或实例
        """
        if implementation is None:
            implementation = service_type
            
        self._services[service_type] = implementation
    
    def register_factory(self, service_type: Type, factory: Callable[['DependencyContainer'], Any]) -> None:
        """
        注册工厂
        
        Args:
            service_type: 服务类型
            factory: 工厂函数
        """
        self._factories[service_type] = factory
    
    def register_singleton(self, service_type: Type, instance: Any = None) -> None:
        """
        注册单例
        
        Args:
            service_type: 服务类型
            instance: 单例实例
        """
        if instance is not None:
            self._singletons[service_type] = instance
        else:
            self._services[service_type] = service_type
    
    def resolve(self, service_type: Type) -> Any:
        """
        解析服务
        
        Args:
            service_type: 服务类型
            
        Returns:
            服务实例
        """
        # 检查单例
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        # 检查工厂
        if service_type in self._factories:
            instance = self._factories[service_type](self)
            self._singletons[service_type] = instance
            return instance
        
        # 检查服务
        if service_type in self._services:
            implementation = self._services[service_type]
            
            # 如果是类，创建实例
            if inspect.isclass(implementation):
                instance = self._create_instance(implementation)
                self._singletons[service_type] = instance
                return instance
            
            # 如果是实例，直接返回
            return implementation
        
        # 如果是具体类，尝试创建实例
        if inspect.isclass(service_type) and not inspect.isabstract(service_type):
            instance = self._create_instance(service_type)
            self._singletons[service_type] = instance
            return instance
        
        raise ValueError(f"无法解析服务类型: {service_type}")
    
    def _create_instance(self, cls: Type) -> Any:
        """
        创建实例
        
        Args:
            cls: 类
            
        Returns:
            实例
        """
        # 获取构造函数参数
        signature = inspect.signature(cls.__init__)
        parameters = signature.parameters
        
        # 跳过self参数
        args = {}
        kwargs = {}
        for name, param in parameters.items():
            # 跳过 self、*args、**kwargs

            if name == 'self' or param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD
            ):
                continue
                
            # 获取参数类型
             # 如果没注解但有默认值，用默认值，跳过注入
            if param.annotation is inspect.Parameter.empty:
                if param.default is not inspect.Parameter.empty:
                    continue
                raise ValueError(f"参数 {name} 缺少类型注解")

            # 有注解，就按类型去 resolve
            kwargs[name] = self.resolve(param.annotation)
        # 创建实例
        return cls(**kwargs)