from typing import Any, Dict
from .base import ICachePolicy

class LRUPolicy(ICachePolicy):
    """LRU（最近最少使用）策略实现"""
    
    def should_evict(self, cache_size: int, max_size: int) -> bool:
        """判断是否需要淘汰"""
        return cache_size >= max_size
    
    def get_eviction_key(self, cache_data: Dict[str, Any]) -> str:
        """获取要淘汰的键
        
        注意：由于使用OrderedDict实现，实际的LRU逻辑在MemoryCache中处理
        这里只是为了满足接口要求
        """
        # 返回第一个键（最早访问的）
        return next(iter(cache_data)) 