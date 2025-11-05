"""缓存模块

提供简单高效的缓存实现，支持内存和Redis后端。

基本用法:
    from xyz.infrastructure.cache import CacheManager, CacheConfig, cached
    
    # 创建缓存管理器
    config = CacheConfig(
        backend="memory",
        max_size=1000
    )
    cache = CacheManager(config)
    
    # 使用缓存装饰器
    @cached(ttl=3600)
    async def get_user(self, user_id: int):
        return await self.db.fetch_user(user_id)
"""

from idp.framework.infrastructure.cache.core.config import CacheConfig, CacheBackend, EvictionPolicy
from idp.framework.infrastructure.cache.manager import CacheManager
from idp.framework.infrastructure.cache.decorators import cached, CacheStrategy, generate_cache_key

__all__ = [
    'CacheConfig',
    'CacheBackend',
    'EvictionPolicy',
    'CacheManager',
    'cached',
    'CacheStrategy',
    'generate_cache_key'
]
