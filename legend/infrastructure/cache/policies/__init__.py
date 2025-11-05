from .base import ICachePolicy
from .lru import LRUPolicy
from .lfu import LFUPolicy
from .adaptive import AdaptivePolicy

__all__ = [
    'ICachePolicy',
    'LRUPolicy',
    'LFUPolicy',
    'AdaptivePolicy',
    'create_policy'
]

def create_policy(policy_type: str, window_size: int = 1000) -> ICachePolicy:
    """创建缓存策略实例
    
    Args:
        policy_type: 策略类型，可选值：lru, lfu, adaptive
        window_size: 观察窗口大小，用于自适应策略
        
    Returns:
        缓存策略实例
        
    Raises:
        ValueError: 不支持的策略类型
        
    Examples:
        # 创建LRU策略
        policy = create_policy("lru")
        
        # 创建自适应策略
        policy = create_policy("adaptive", window_size=1000)
    """
    policies = {
        "lru": LRUPolicy,
        "lfu": LFUPolicy,
        "adaptive": lambda: AdaptivePolicy(window_size=window_size)
    }
    
    policy_class = policies.get(policy_type.lower())
    if not policy_class:
        raise ValueError(f"不支持的策略类型: {policy_type}")
    
    return policy_class() 