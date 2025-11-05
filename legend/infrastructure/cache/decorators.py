"""缓存装饰器模块

提供易用的缓存装饰器，支持多种缓存策略和自定义键生成。
"""

import inspect
import logging
from datetime import timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Union

from idp.framework.exception import ErrorCode, InfrastructureException
from idp.framework.infrastructure.cache.core.config import CacheStrategy

logger = logging.getLogger(__name__)



def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """生成缓存键
    
    Args:
        prefix: 键前缀
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        str: 生成的缓存键
    """
    key_parts = [prefix]
    
    # 处理位置参数
    if args:
        key_parts.extend(str(arg) for arg in args)
        
    # 处理关键字参数
    if kwargs:
        # 过滤掉None值和内部参数
        filtered_kwargs = {
            k: v for k, v in sorted(kwargs.items())
            if v is not None and not k.startswith('_')
        }
        key_parts.extend(f"{k}:{v}" for k, v in filtered_kwargs.items())
        
    return ":".join(key_parts)

def cached(
    ttl: Optional[Union[int, timedelta]] = 300,
    strategy: CacheStrategy = CacheStrategy.READ_WRITE,
    prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None,
    condition: Optional[Callable] = None
):
    """缓存装饰器
    
    为任何异步方法添加缓存支持。
    
    Args:
        ttl: 缓存过期时间（秒或timedelta）
        strategy: 缓存策略
        prefix: 缓存键前缀
        key_builder: 自定义缓存键生成函数
        condition: 条件函数，返回True时才使用缓存
        
    Examples:
        @cached(ttl=300)
        async def get_user(self, user_id: int):
            return await self.db.fetch_user(user_id)
            
        @cached(
            ttl=timedelta(hours=1),
            key_builder=lambda self, user_id, **kw: f"user:{user_id}:profile"
        )
        async def get_user_profile(self, user_id: int):
            return await self.db.fetch_profile(user_id)
    """
    def decorator(method: Callable):
        # 获取方法签名以便更好的错误提示
        sig = inspect.signature(method)
        
        @wraps(method)
        async def wrapper(self, *args, **kwargs):
            # 检查是否有缓存管理器
            if not hasattr(self, '_cache_manager'):
                logger.warning(
                    f"No cache manager found for {method.__name__}, "
                    "cache decorator will be ignored"
                )
                return await method(self, *args, **kwargs)
                
            # 检查是否应该使用缓存
            if strategy == CacheStrategy.NONE or (
                condition and not condition(self, *args, **kwargs)
            ):
                return await method(self, *args, **kwargs)
            
            try:
                # 构建缓存键
                if key_builder:
                    cache_key = key_builder(self, *args, **kwargs)
                else:
                    method_prefix = prefix or f"{self.__class__.__name__}:{method.__name__}"
                    cache_key = generate_cache_key(method_prefix, *args, **kwargs)
                
                # 尝试从缓存获取
                if strategy in (CacheStrategy.READ_WRITE, CacheStrategy.READ_ONLY):
                    try:
                        cached_value = await self._cache_manager.get(cache_key)
                        if cached_value is not None:
                            return cached_value
                    except Exception as e:
                        logger.warning(
                            f"Failed to read from cache for {method.__name__}: {str(e)}"
                        )
                
                # 执行方法
                result = await method(self, *args, **kwargs)
                
                # 写入缓存
                if strategy in (CacheStrategy.READ_WRITE, CacheStrategy.WRITE_ONLY):
                    if result is not None:  # 不缓存None值
                        try:
                            expire = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl
                            await self._cache_manager.set(cache_key, result, expire=expire)
                        except Exception as e:
                            logger.warning(
                                f"Failed to write to cache for {method.__name__}: {str(e)}"
                            )
                
                return result
                
            except Exception as e:
                # 处理所有其他异常
                logger.error(
                    f"Cache operation failed for {method.__name__}: {str(e)}",
                    exc_info=True
                )
                raise InfrastructureException(
                    message=f"Cache operation failed: {str(e)}",
                    error_code=ErrorCode.CACHE_OPERATION_ERROR
                ) from e
                
        return wrapper
    return decorator 