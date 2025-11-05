from abc import ABC, abstractmethod
from typing import Any, Dict

class ICachePolicy(ABC):
    """缓存策略接口"""
    
    @abstractmethod
    def should_evict(self, cache_size: int, max_size: int) -> bool:
        """判断是否需要淘汰
        
        Args:
            cache_size: 当前缓存大小
            max_size: 最大缓存大小
            
        Returns:
            是否需要淘汰
        """
        pass
    
    @abstractmethod
    def get_eviction_key(self, cache_data: Dict[str, Any]) -> str:
        """获取要淘汰的键
        
        Args:
            cache_data: 缓存数据
            
        Returns:
            要淘汰的键
        """
        pass 