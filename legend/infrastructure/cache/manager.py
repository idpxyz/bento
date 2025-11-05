"""缓存管理器模块

提供统一的缓存管理接口，支持不同的缓存策略和后端。
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional, Union

from idp.framework.exception.code.cache import CacheErrorCode

from idp.framework.exception import InfrastructureException

from .backends import MemoryCache, RedisCache
from .core.config import CacheBackend, CacheConfig, CacheStrategy

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """简单的缓存统计"""
    hits: int = 0
    misses: int = 0
    total_operations: int = 0

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        get_operations = self.hits + self.misses
        return self.hits / get_operations if get_operations > 0 else 0.0

    def reset(self) -> None:
        """重置统计"""
        self.hits = 0
        self.misses = 0
        self.total_operations = 0


class CacheManager:
    """缓存管理器
    
    纯粹的基础设施组件，专注于缓存操作。
    生命周期管理应该由应用层负责。
    """

    def __init__(self, config: CacheConfig):
        """初始化缓存管理器
        
        Args:
            config: 缓存配置
        """
        self.config = config
        self._stats = CacheStats() if config.enable_stats else None
        
        # 创建缓存后端
        if config.backend == CacheBackend.REDIS:
            if not config.redis_url:
                raise ValueError("Redis URL is required for Redis backend")
            self._cache = RedisCache(config)
        else:
            self._cache = MemoryCache(config)

    async def initialize(self) -> None:
        """初始化缓存后端"""
        if hasattr(self._cache, 'initialize'):
            await self._cache.initialize()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.config.should_read_from_cache():
            return None
            
        if self._stats:
            self._stats.total_operations += 1

        try:
            # 确保缓存已初始化
            await self.initialize()
            value = await self._cache.get(key)

            if self._stats:
                if value is not None:
                    self._stats.hits += 1
                else:
                    self._stats.misses += 1

            return value
            
        except Exception as e:
            logger.error(f"Failed to get cache key '{key}': {str(e)}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """设置缓存值"""
        if not self.config.should_write_to_cache():
            return

        if self._stats:
            self._stats.total_operations += 1

        try:
            # 确保缓存已初始化
            await self.initialize()
            await self._cache.set(key, value, expire)
        except Exception as e:
            logger.error(f"Failed to set cache key '{key}': {str(e)}")

    async def delete(self, key: str) -> None:
        """删除缓存值"""
        try:
            # 确保缓存已初始化
            await self.initialize()
            await self._cache.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete cache key '{key}': {str(e)}")

    async def clear(self) -> None:
        """清除所有缓存"""
        try:
            # 确保缓存已初始化
            await self.initialize()
            await self._cache.clear()
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")

    async def delete_pattern(self, pattern: str) -> None:
        """删除匹配模式的所有缓存"""
        try:
            # 确保缓存已初始化
            await self.initialize()
            await self._cache.delete_pattern(pattern)
        except Exception as e:
            logger.error(f"Failed to delete cache pattern '{pattern}': {str(e)}")

    def get_stats(self) -> Optional[Dict[str, Union[int, float]]]:
        """获取缓存统计信息"""
        if not self._stats:
            return None
            
        return {
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "total_operations": self._stats.total_operations,
            "hit_rate": self._stats.hit_rate
        }