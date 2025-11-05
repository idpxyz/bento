from typing import Dict, List, Callable, Any, Optional
from idp.core.infrastructure.dependency_injection.container import DependencyContainer

class ContextRegistry:
    """上下文注册表 - 管理有界上下文的注册和配置"""
    
    def __init__(self, container: DependencyContainer):
        self.container = container
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.configurators: Dict[str, List[Callable]] = {}
    
    def register_context(self, name: str, description: str = "") -> None:
        """注册上下文"""
        if name in self.contexts:
            raise ValueError(f"Context '{name}' already registered")
            
        self.contexts[name] = {
            "name": name,
            "description": description,
            "configured": False
        }
        self.configurators[name] = []
    
    def add_configurator(self, context_name: str, configurator: Callable) -> None:
        """添加上下文配置器"""
        if context_name not in self.contexts:
            raise ValueError(f"Context '{context_name}' not registered")
            
        self.configurators[context_name].append(configurator)
    
    def configure_context(self, context_name: str) -> None:
        """配置上下文"""
        if context_name not in self.contexts:
            raise ValueError(f"Context '{context_name}' not registered")
            
        if self.contexts[context_name]["configured"]:
            return
            
        for configurator in self.configurators[context_name]:
            configurator(self.container)
            
        self.contexts[context_name]["configured"] = True
    
    def configure_all_contexts(self) -> None:
        """配置所有上下文"""
        for context_name in self.contexts:
            self.configure_context(context_name)
    
    def is_context_configured(self, context_name: str) -> bool:
        """检查上下文是否已配置"""
        if context_name not in self.contexts:
            raise ValueError(f"Context '{context_name}' not registered")
            
        return self.contexts[context_name]["configured"]
