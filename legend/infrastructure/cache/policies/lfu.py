from typing import Any, Dict
from collections import defaultdict
from .base import ICachePolicy

class LFUPolicy(ICachePolicy):
    """LFU（最少使用频率）策略实现"""
    
    def __init__(self):
        self._access_counts = defaultdict(int)
    
    def should_evict(self, cache_size: int, max_size: int) -> bool:
        """判断是否需要淘汰"""
        return cache_size >= max_size
    
    def get_eviction_key(self, cache_data: Dict[str, Any]) -> str:
        """获取要淘汰的键
        
        选择访问次数最少的键淘汰，如果有多个访问次数相同的，选择最早的一个
        """
        # 清理已经不在缓存中的键的访问计数
        self._access_counts = defaultdict(
            int,
            {k: v for k, v in self._access_counts.items() if k in cache_data}
        )
        
        # 如果是新的键（还没有访问记录），初始化为0
        for key in cache_data:
            if key not in self._access_counts:
                self._access_counts[key] = 0
        
        # 返回访问次数最少的键
        return min(
            cache_data.keys(),
            key=lambda k: (self._access_counts[k], k)
        )
    
    def increment_access(self, key: str) -> None:
        """增加键的访问计数"""
        self._access_counts[key] += 1 