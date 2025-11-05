"""Cache configuration module

This module defines all cache-related configuration classes and enums.
"""

from datetime import timedelta
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CacheStrategy(str, Enum):
    """缓存读写策略
    
    定义了不同的缓存读写模式：
    - NONE: 不使用缓存
    - READ_WRITE: 读写缓存（默认）
    - READ_ONLY: 只读缓存，不写入
    - WRITE_ONLY: 只写入缓存，不读取
    - WRITE_THROUGH: 同时写入缓存和数据库
    - WRITE_BEHIND: 先写入缓存，异步写入数据库
    - WRITE_AROUND: 写入数据库，成功后再写入缓存
    - REFRESH_AHEAD: 在缓存过期前自动刷新
    """
    NONE = "none"           # 不使用缓存
    READ_WRITE = "rw"       # 读写缓存
    READ_ONLY = "ro"        # 只读缓存
    WRITE_ONLY = "wo"       # 只写缓存
    WRITE_THROUGH = "wt"    # 同时写入缓存和数据库
    WRITE_BEHIND = "wb"     # 写后缓存
    WRITE_AROUND = "wa"     # 绕过缓存写数据库，成功后更新缓存
    REFRESH_AHEAD = "ra"    # 在缓存过期前预刷新


class CacheBackend(str, Enum):
    """缓存后端类型"""
    MEMORY = "memory"  # 内存缓存
    REDIS = "redis"    # Redis缓存

class EvictionPolicy(str, Enum):
    """缓存淘汰策略
    
    定义了不同的缓存淘汰算法：
    - LRU: 最近最少使用（默认）
    - LFU: 最少使用频率
    - ADAPTIVE: 自适应策略（根据访问模式自动在LRU和LFU之间切换）
    """
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最少使用频率
    ADAPTIVE = "adaptive"  # 自适应策略

class SerializerType(str, Enum):
    """序列化类型"""
    JSON = "json"      # JSON序列化
    PICKLE = "pickle"  # Pickle序列化
    MSGPACK = "msgpack"  # MessagePack序列化

class CacheConfig(BaseModel):
    """缓存配置
    
    完整的缓存配置模型，包含所有缓存相关的设置。
    
    Attributes:
        backend: 缓存后端类型
        strategy: 缓存读写策略
        eviction_policy: 缓存淘汰策略
        max_size: 最大缓存条目数
        enable_stats: 是否启用统计
        ttl: 默认过期时间
        prefix: 缓存键前缀
        serializer: 序列化方式
        compression: 是否启用压缩
        redis_url: Redis连接URL
        policy_window_size: 自适应策略的观察窗口大小
        write_behind_delay: 写后延迟时间
        write_behind_batch_size: 写后批处理大小
        cleanup_interval: 缓存清理间隔
        enabled: 是否启用缓存
    
    Examples:
        # 内存缓存示例
        config = CacheConfig(
            backend="memory",
            max_size=1000,
            strategy=CacheStrategy.READ_WRITE,
            eviction_policy=EvictionPolicy.LRU,
            ttl=timedelta(hours=1)
        )
    """
    # 基础配置
    backend: CacheBackend = Field(
        default=CacheBackend.MEMORY,
        description="缓存后端类型，默认为内存缓存"
    )
    strategy: CacheStrategy = Field(
        default=CacheStrategy.READ_WRITE,
        description="缓存读写策略，默认为读写缓存"
    )
    eviction_policy: EvictionPolicy = Field(
        default=EvictionPolicy.LRU,
        description="缓存淘汰策略，默认为LRU"
    )
    
    # 容量和性能配置
    max_size: int = Field(
        default=10000,
        ge=1,
        description="最大缓存条目数，默认10000"
    )
    # 过期时间
    ttl: Union[int, timedelta] = Field(
        default=timedelta(hours=1),
        description="默认过期时间，支持整数(秒)或timedelta，默认1小时"
    )
    # 是否启用统计
    enable_stats: bool = Field(
        default=True,
        description="是否启用统计，默认启用"
    )
    
    # 键和序列化配置
    prefix: str = Field(
        default="cache:",
        description="缓存键前缀，默认为'cache:'"
    )
    # 序列化方式
    serializer: SerializerType = Field(
        default=SerializerType.PICKLE,
        description="序列化方式，默认为Pickle"
    )
    # 是否启用压缩
    compression: bool = Field(
        default=False,
        description="是否启用压缩，默认不启用"
    )
    
    # Redis特定配置
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis连接URL，仅在使用Redis后端时需要"
    )
    
    # 高级配置
    policy_window_size: int = Field(
        default=1000,
        ge=100,
        description="自适应策略的观察窗口大小，默认1000"
    )
    write_behind_delay: Union[int, timedelta] = Field(
        default=timedelta(seconds=5),
        description="写后延迟时间，支持整数(秒)或timedelta，默认5秒"
    )
    write_behind_batch_size: int = Field(
        default=100,
        ge=1,
        description="写后批处理大小，默认100"
    )
    
    # 拦截器配置
    cleanup_interval: Union[int, timedelta] = Field(
        default=timedelta(minutes=5),
        description="缓存清理间隔，支持整数(秒)或timedelta，默认5分钟"
    )
    enabled: bool = Field(
        default=True,
        description="是否启用缓存，默认启用"
    )
    
    @field_validator('redis_url')
    def validate_redis_url(cls, v: str) -> str:
        """验证Redis URL"""
        if cls.model_fields['backend'].default == CacheBackend.REDIS and not v:
            raise ValueError("Redis URL is required when using Redis backend")
        return v
    
    @field_validator('ttl', 'write_behind_delay', 'cleanup_interval')
    def validate_time_fields(cls, v: Union[int, timedelta]) -> int:
        """验证并转换时间字段为秒
        
        支持整数(秒)或timedelta输入，统一转换为秒
        """
        if isinstance(v, int):
            if v < 0:
                raise ValueError("Time value cannot be negative")
            return v
        elif isinstance(v, timedelta):
            seconds = int(v.total_seconds())
            if seconds < 0:
                raise ValueError("Time value cannot be negative")
            return seconds
        raise ValueError("Time value must be an integer or timedelta")
    
    def should_read_from_cache(self) -> bool:
        """是否应该从缓存读取"""
        return self.enabled and self.strategy in (
            CacheStrategy.READ_WRITE,
            CacheStrategy.READ_ONLY,
            CacheStrategy.REFRESH_AHEAD
        )
    
    def should_write_to_cache(self) -> bool:
        """是否应该写入缓存"""
        return self.enabled and self.strategy in (
            CacheStrategy.READ_WRITE,
            CacheStrategy.WRITE_ONLY,
            CacheStrategy.WRITE_THROUGH,
            CacheStrategy.WRITE_BEHIND,
            CacheStrategy.WRITE_AROUND
        )