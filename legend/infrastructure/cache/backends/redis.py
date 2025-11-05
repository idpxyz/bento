"""Redis cache backend implementation."""

import json
import pickle
from datetime import timedelta
from typing import Any, Optional, Set, Union

from redis.asyncio import Redis

from ..core.base import ICache
from ..core.config import CacheConfig, EvictionPolicy, SerializerType

try:
    import msgpack
except ImportError:
    msgpack = None

import logging

logger = logging.getLogger(__name__)

class RedisCache(ICache):
    """Redis缓存实现"""

    def __init__(self, config: CacheConfig):
        """初始化Redis缓存
        
        Args:
            config: 缓存配置
        """
        self.config = config
        self._client: Optional[Redis] = None
        # 设置序列化器
        self._serializer = self._get_serializer(config.serializer)
        self._key_set_name = f"{config.prefix}__keys__"
    
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
        """初始化Redis连接"""
        if not self.config.redis_url:
            raise ValueError("Redis URL is required")
            
        try:
            self._client = Redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=False  # 因为我们使用自定义序列化
            )
            
            # 配置淘汰策略
            if self.config.eviction_policy == EvictionPolicy.LRU:
                await self._client.config_set('maxmemory-policy', 'allkeys-lru')
            elif self.config.eviction_policy == EvictionPolicy.LFU:
                await self._client.config_set('maxmemory-policy', 'allkeys-lfu')
            elif self.config.eviction_policy == EvictionPolicy.ADAPTIVE:
                # 自适应策略使用LFU并动态调整
                await self._client.config_set('maxmemory-policy', 'allkeys-lfu')
                await self._client.config_set('lfu-decay-time', str(self.config.policy_window_size))

            # 设置最大内存
            if self.config.max_size:
                # 转换为字节 (粗略估计)
                max_memory = self.config.max_size * 1024  # 假设每个条目1KB
                await self._client.config_set('maxmemory', str(max_memory))
                
            # 测试连接
            await self._client.ping()
        except Exception as e:
            self._client = None
            raise RuntimeError(f"Failed to connect to Redis: {str(e)}")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self._client:
            raise RuntimeError("Redis client not initialized")
            
        key = f"{self.config.prefix}{key}"
        data = await self._client.get(key)
        
        if data is None:
            return None
            
        return self._deserialize(data)

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """设置缓存值"""
        if not self._client:
            raise RuntimeError("Redis client not initialized")
            
        key = f"{self.config.prefix}{key}"
        data = self._serialize(value)
        
        async with self._client.pipeline(transaction=True) as pipe:
            # 添加键到跟踪集合
            await pipe.sadd(self._key_set_name, key)
            
            if expire:
                if isinstance(expire, timedelta):
                    expire = int(expire.total_seconds())
                await pipe.setex(key, expire, data)
                # 设置跟踪集合中键的过期时间
                await pipe.expire(key, expire)
            else:
                await pipe.set(key, data, ex=self.config.ttl)
                if self.config.ttl:
                    await pipe.expire(key, self.config.ttl)
            
            await pipe.execute()

    async def delete(self, key: str) -> None:
        """删除缓存值"""
        if not self._client:
            raise RuntimeError("Redis client not initialized")
            
        key = f"{self.config.prefix}{key}"
        async with self._client.pipeline(transaction=True) as pipe:
            await pipe.delete(key)
            await pipe.srem(self._key_set_name, key)
            await pipe.execute()

    async def clear(self) -> None:
        """清空缓存"""
        if not self._client:
            raise RuntimeError("Redis client not initialized")
            
        # 获取所有键并批量删除
        all_keys = await self._client.smembers(self._key_set_name)
        if all_keys:
            async with self._client.pipeline(transaction=True) as pipe:
                await pipe.delete(*all_keys)
                await pipe.delete(self._key_set_name)
                await pipe.execute()

    async def delete_pattern(self, pattern: str) -> None:
        """删除符合模式的缓存键

        使用跟踪集合来可靠地查找和删除匹配的键。
        支持以下模式:
        - 实体ID缓存: {entity}:id:{id}
        - 列表缓存: {entity}:list:*
        - 参数查询缓存: {entity}:list:params:{param}:{value}
        - 查询缓存: {entity}:query:*
        
        Args:
            pattern: 匹配模式，支持 Redis 通配符 (*, ?)
        """
        if not self._client:
            raise RuntimeError("Redis client not initialized")
            
        # 获取配置中的前缀
        prefix = self.config.prefix
        # 记录前缀信息
        logger.debug(f"Cache prefix: '{prefix}', original pattern: '{pattern}'")
        
        # 处理完整模式（带前缀）
        full_pattern = f"{prefix}{pattern}"
        logger.debug(f"Using full pattern for matching: '{full_pattern}'")
        
        # 性能优化：对于包含通配符的模式，限制扫描数量避免卡住
        if '*' in pattern or '?' in pattern:
            # 使用scan命令安全地查找匹配键
            matching_keys = set()  # 使用集合避免重复键
            cursor = b'0'
            max_scan_iterations = 50  # 增加扫描迭代次数上限
            max_keys = 5000          # 增加匹配键的最大数量
            scan_count = 0
            
            try:
                while cursor != b'0' or scan_count == 0:
                    scan_count += 1
                    if scan_count > max_scan_iterations:
                        logger.warning(f"Reached maximum scan iterations ({max_scan_iterations}) for pattern: {full_pattern}")
                        break
                    
                    cursor, keys = await self._client.scan(
                        cursor=cursor, 
                        match=full_pattern,
                        count=500  # 每次扫描更多的键以提高效率
                    )
                    
                    if keys:
                        # 转换并添加到集合中，自动去重
                        for key in keys:
                            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                            matching_keys.add(key_str)
                        logger.debug(f"Found {len(keys)} keys in scan iteration {scan_count}, total unique: {len(matching_keys)}")
                        
                    if len(matching_keys) >= max_keys:
                        logger.warning(f"Reached maximum keys limit ({max_keys}) for pattern: {full_pattern}")
                        break
                        
                    if cursor == b'0':
                        break
            except Exception as e:
                logger.error(f"Error scanning for keys with pattern {full_pattern}: {str(e)}")
            
            if matching_keys:
                try:
                    # 批量执行删除和从跟踪集合中移除
                    batch_size = 200  # 增加批次大小
                    for i in range(0, len(matching_keys), batch_size):
                        batch = list(matching_keys)[i:i + batch_size]
                        async with self._client.pipeline(transaction=True) as pipe:
                            # 删除键
                            await pipe.delete(*batch)
                            # 从跟踪集合中移除
                            await pipe.srem(self._key_set_name, *batch)
                            await pipe.execute()
                    
                    logger.debug(f"Deleted {len(matching_keys)} keys matching pattern: '{full_pattern}'")
                except Exception as e:
                    logger.error(f"Error deleting keys for pattern {full_pattern}: {str(e)}")
            else:
                logger.debug(f"No keys found matching pattern: '{full_pattern}'")
                
        # 精确匹配模式 (没有通配符)，直接使用 key 命令
        else:
            exact_key = full_pattern
            try:
                exists = await self._client.exists(exact_key)
                if exists:
                    async with self._client.pipeline(transaction=True) as pipe:
                        await pipe.delete(exact_key)
                        await pipe.srem(self._key_set_name, exact_key)
                        await pipe.execute()
                    logger.debug(f"Deleted exact key: '{exact_key}'")
            except Exception as e:
                logger.error(f"Error deleting exact key {exact_key}: {str(e)}")

    async def close(self) -> None:
        """关闭Redis连接"""
        if self._client:
            await self._client.aclose()
            self._client = None 

