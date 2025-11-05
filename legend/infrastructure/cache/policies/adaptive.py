from typing import Any, Dict
from collections import defaultdict
import time
from .base import ICachePolicy
from .lru import LRUPolicy
from .lfu import LFUPolicy

class AdaptivePolicy(ICachePolicy):
    """自适应缓存策略实现
    
    根据访问模式自动在LRU和LFU之间切换：
    - 当短时间内重复访问率高时使用LFU
    - 当访问模式较为随机时使用LRU
    """
    
    def __init__(self, window_size: int = 1000):
        """初始化自适应策略
        
        Args:
            window_size: 观察窗口大小（访问次数）
        """
        self._lru_policy = LRUPolicy()
        self._lfu_policy = LFUPolicy()
        self._window_size = window_size
        self._access_history = []  # 记录最近的访问
        self._current_policy = self._lru_policy  # 默认使用LRU
        self._access_counts = defaultdict(int)  # 全局访问计数
        self._last_access_time = {}  # 记录最后访问时间
        
    def should_evict(self, cache_size: int, max_size: int) -> bool:
        """判断是否需要淘汰"""
        return cache_size >= max_size
    
    def get_eviction_key(self, cache_data: Dict[str, Any]) -> str:
        """获取要淘汰的键
        
        综合考虑访问频率和最近访问时间：
        1. 计算每个键的综合得分（访问频率 * 时间衰减）
        2. 选择得分最低的键淘汰
        """
        if not cache_data:
            return None
        
        current_time = time.time()
        scores = {}
        
        for key in cache_data:
            # 访问频率得分
            freq_score = self._access_counts[key]
            
            # 时间衰减因子 (最近访问的得分更高)
            time_factor = 1.0
            last_access = self._last_access_time.get(key, 0)
            if last_access > 0:
                # 计算时间衰减，最大衰减为0.1
                time_elapsed = current_time - last_access
                time_factor = max(0.1, 1.0 - (time_elapsed / 3600))  # 1小时内衰减到0.1
            
            # 综合得分 = 频率 * 时间因子
            scores[key] = freq_score * time_factor
        
        # 返回得分最低的键
        return min(cache_data.keys(), key=lambda k: scores[k])
    
    def record_access(self, key: str) -> None:
        """记录访问并更新策略"""
        current_time = time.time()
        self._access_history.append((key, current_time))
        self._access_counts[key] += 1
        self._last_access_time[key] = current_time
        
        # 保持窗口大小
        while len(self._access_history) > self._window_size:
            old_key, _ = self._access_history.pop(0)
            # 更新访问计数
            remaining_count = sum(1 for k, _ in self._access_history if k == old_key)
            if remaining_count == 0:
                self._access_counts[old_key] = 0
                self._last_access_time.pop(old_key, None)
        
        # 计算访问模式
        if len(self._access_history) >= self._window_size // 4:
            window_counts = defaultdict(int)
            for k, _ in self._access_history[-self._window_size // 4:]:
                window_counts[k] += 1
            
            # 计算重复访问指标
            total_accesses = len(self._access_history)
            max_freq = max(window_counts.values())
            
            # 如果某个键的访问频率超过阈值，切换到LFU
            should_use_lfu = max_freq >= 3  # 至少被访问3次
            
            if should_use_lfu and self._current_policy is not self._lfu_policy:
                self._current_policy = self._lfu_policy
            elif not should_use_lfu and self._current_policy is not self._lru_policy:
                self._current_policy = self._lru_policy 