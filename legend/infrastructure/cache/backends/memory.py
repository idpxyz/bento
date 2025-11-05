from dataclasses import dataclass
from typing import Any, Dict, Optional, Union, Tuple
from datetime import datetime, timedelta
import asyncio
import time
import json
import pickle
from collections import OrderedDict
import logging

from ..core.config import CacheConfig, SerializerType, EvictionPolicy
from ..core.base import ICache
from ..policies import create_policy, LFUPolicy, AdaptivePolicy

try:
    import msgpack
except ImportError:
    msgpack = None

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata for eviction policies."""
    value: Any
    expires_at: float
    access_count: int = 0
    last_access: float = 0.0
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() > self.expires_at
        
    def access(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_access = time.time()


class MemoryCache(ICache):
    """内存缓存实现"""

    def __init__(self, config: CacheConfig):
        """初始化内存缓存
        
        Args:
            config: 缓存配置
        """
        self.config = config
        self._cache: OrderedDict[str, tuple[Any, Optional[float]]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._policy = create_policy(config.eviction_policy, config.policy_window_size)
        
        # 设置序列化器
        self._serializer = self._get_serializer(config.serializer)
    
    def _get_serializer(self, serializer_type: SerializerType):
        """获取序列化器"""
        serializers = {
            SerializerType.JSON: json,
            SerializerType.PICKLE: pickle
        }
        
        if msgpack is not None:
            serializers[SerializerType.MSGPACK] = msgpack
            
        serializer = serializers.get(serializer_type)
        if serializer is None:
            if serializer_type == SerializerType.MSGPACK and msgpack is None:
                raise ImportError(
                    "msgpack is not installed. Please install it with 'pip install msgpack'"
                )
            # 如果找不到序列化器，默认使用JSON
            serializer = json
            
        return serializer
    
    def _serialize(self, value: Any) -> bytes:
        """序列化值"""
        try:
            if self.config.serializer == SerializerType.JSON:
                return json.dumps(value).encode('utf-8')
            elif self.config.serializer == SerializerType.PICKLE:
                return pickle.dumps(value)
            else:  # MSGPACK
                return msgpack.packb(value)
        except Exception as e:
            raise ValueError(f"Failed to serialize value: {str(e)}")
    
    def _deserialize(self, data: bytes) -> Any:
        """反序列化值"""
        try:
            if self.config.serializer == SerializerType.JSON:
                return json.loads(data.decode('utf-8'))
            elif self.config.serializer == SerializerType.PICKLE:
                return pickle.loads(data)
            else:  # MSGPACK
                return msgpack.unpackb(data)
        except Exception as e:
            raise ValueError(f"Failed to deserialize value: {str(e)}")

    async def initialize(self) -> None:
        """初始化缓存"""
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            key = f"{self.config.prefix}{key}"
            if key not in self._cache:
                return None
            
            value, expire_at = self._cache[key]
            if expire_at and time.time() > expire_at:
                del self._cache[key]
                return None
                
            # 更新LRU顺序
            self._cache.move_to_end(key)
            
            # 更新策略状态
            if isinstance(self._policy, (LFUPolicy, AdaptivePolicy)):
                if isinstance(self._policy, LFUPolicy):
                    self._policy.increment_access(key)
                else:
                    self._policy.record_access(key)
                    
            # 反序列化值
            return self._deserialize(value) if isinstance(value, bytes) else value

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """设置缓存值"""
        async with self._lock:
            key = f"{self.config.prefix}{key}"
            
            # 检查是否需要淘汰
            if (
                self.config.max_size
                and key not in self._cache
                and self._policy.should_evict(len(self._cache), self.config.max_size)
            ):
                # 获取要淘汰的键
                evict_key = self._policy.get_eviction_key(self._cache)
                self._cache.pop(evict_key, None)
            
            # 计算过期时间
            expire_at = None
            if expire:
                if isinstance(expire, timedelta):
                    expire = expire.total_seconds()
                expire_at = time.time() + expire
            elif self.config.ttl:
                expire_at = time.time() + self.config.ttl
            
            # 序列化值
            serialized_value = self._serialize(value)
            
            self._cache[key] = (serialized_value, expire_at)
            # 更新LRU顺序
            self._cache.move_to_end(key)
            
            # 如果是自适应策略，记录访问
            if isinstance(self._policy, AdaptivePolicy):
                self._policy.record_access(key)

    async def delete(self, key: str) -> None:
        """删除缓存值"""
        async with self._lock:
            key = f"{self.config.prefix}{key}"
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()

    async def delete_pattern(self, pattern: str) -> None:
        """删除符合模式的缓存键"""
        async with self._lock:
            pattern = pattern.replace("*", "")
            keys_to_delete = [
                key for key in list(self._cache.keys())
                if pattern in key
            ]
            for key in keys_to_delete:
                del self._cache[key]

    async def close(self) -> None:
        """关闭缓存"""
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        await self.clear()

    async def _cleanup_loop(self) -> None:
        """定期清理过期的缓存项"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                async with self._lock:
                    current_time = time.time()
                    expired_keys = [
                        key for key, (_, expire_at) in self._cache.items()
                        if expire_at and current_time > expire_at
                    ]
                    for key in expired_keys:
                        del self._cache[key]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(5)  # 错误时避免频繁重试

    async def _evict_if_needed(self) -> None:
        """Evict entries based on policy if cache is full."""
        if len(self._cache) < self.config.max_size:
            return
            
        # Number of entries to evict (10% of max size)
        num_to_evict = max(1, self.config.max_size // 10)
        
        if self.config.eviction_policy == EvictionPolicy.LRU:
            # Sort by last access time
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1][1]
            )
            for key, _ in sorted_entries[:num_to_evict]:
                del self._cache[key]
                
        elif self.config.eviction_policy == EvictionPolicy.LFU:
            # Sort by access count
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1][0].access_count
            )
            for key, _ in sorted_entries[:num_to_evict]:
                del self._cache[key]
                
        elif self.config.eviction_policy == EvictionPolicy.ADAPTIVE:
            # Use LFU for frequently accessed entries and LRU for others
            threshold = sum(
                entry[0].access_count for entry in self._cache.values()
            ) / len(self._cache)
            
            entries_to_evict = []
            for key, (entry, expire_at) in self._cache.items():
                if entry.access_count > threshold:
                    # For frequently accessed entries, use LRU
                    score = expire_at
                else:
                    # For less frequently accessed entries, use LFU
                    score = entry.access_count
                entries_to_evict.append((key, score))
                
            sorted_entries = sorted(entries_to_evict, key=lambda x: x[1])
            for key, _ in sorted_entries[:num_to_evict]:
                del self._cache[key]

