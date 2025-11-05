from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ConfigProvider(ABC):
    """配置提供器接口，负责从特定源加载配置"""
    
    @abstractmethod
    def get_namespace(self) -> str:
        """获取提供器的命名空间
        
        Returns:
            str: 命名空间名称
        """
        pass
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """加载配置数据
        
        Returns:
            Dict[str, Any]: 加载的配置数据
        """
        pass
    
    @abstractmethod
    def reload(self) -> Dict[str, Any]:
        """重新加载配置数据
        
        Returns:
            Dict[str, Any]: 重新加载的配置数据
        """
        pass
    
    @abstractmethod
    def supports_hot_reload(self) -> bool:
        """是否支持热重载
        
        Returns:
            bool: 是否支持热重载
        """
        pass

class ProviderRegistry:
    """配置提供器注册表"""
    
    def __init__(self):
        self._providers: Dict[str, ConfigProvider] = {}
    
    def register(self, provider: ConfigProvider) -> None:
        """注册配置提供器
        
        Args:
            provider: 配置提供器实例
        """
        namespace = provider.get_namespace()
        self._providers[namespace] = provider
    
    def get_provider(self, namespace: str) -> Optional[ConfigProvider]:
        """获取指定命名空间的提供器
        
        Args:
            namespace: 命名空间
            
        Returns:
            Optional[ConfigProvider]: 提供器实例，如果不存在则返回None
        """
        return self._providers.get(namespace)
    
    def get_providers(self) -> List[ConfigProvider]:
        """获取所有提供器
        
        Returns:
            List[ConfigProvider]: 所有提供器列表
        """
        return list(self._providers.values()) 