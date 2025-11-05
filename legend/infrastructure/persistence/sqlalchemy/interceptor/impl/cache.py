"""缓存拦截器实现

提供实体操作的缓存支持，包括：
- 读取操作的缓存
- 写入操作后的缓存清理
- 批量操作的缓存处理
"""

import asyncio
import logging
import time
from datetime import timedelta
from typing import (
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    Optional,
    Set,
    TypeVar,
    Union,
)

from idp.framework.infrastructure.cache import CacheManager
from idp.framework.infrastructure.cache.backends.redis import RedisCache
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core import (
    Interceptor,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.common import (
    OperationType,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.type import (
    InterceptorContext,
)
from idp.framework.infrastructure.persistence.sqlalchemy.po import BasePO

T = TypeVar('T', bound=BasePO)

logger = logging.getLogger(__name__)

class CacheInterceptor(Interceptor[T]):
    """缓存拦截器
    
    为实体操作提供缓存支持。
    
    特性：
    1. 自动缓存读取操作的结果
    2. 在写入操作后自动清理相关缓存
    3. 支持批量操作的缓存处理
    4. 可配置的缓存策略和过期时间
    """
    
    interceptor_type: ClassVar[str] = "cache"
    _instance: ClassVar[Optional["CacheInterceptor"]] = None
    _cache_manager: ClassVar[Optional[CacheManager]] = None
    _initialized: ClassVar[bool] = False
    _cleared_cache_keys: ClassVar[Set[str]] = set()
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _operation_context: ClassVar[Dict[str, Dict[str, Any]]] = {}
    _processed_operations: ClassVar[Set[str]] = set()
    _initialization_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _operation_cache_keys: ClassVar[Dict[str, str]] = {}
    _cleared_patterns: ClassVar[Set[str]] = set()
    _operation_locks: ClassVar[Dict[str, asyncio.Lock]] = {}
    _last_cleanup: ClassVar[float] = 0.0
    _key_set_name: ClassVar[str] = "cache_keys"
    
    def __new__(cls, *args, **kwargs) -> "CacheInterceptor[T]":
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, cache_manager: CacheManager):
        """初始化缓存拦截器
        
        Args:
            cache_manager: 缓存管理器实例
        """
        self.cache_manager = cache_manager
        self.config = cache_manager.config
        
    @property
    def is_redis_cache(self) -> bool:
        """检查是否使用Redis缓存后端"""
        return isinstance(self.cache_manager._cache, RedisCache)
    
    @property
    def enabled(self) -> bool:
        """是否启用缓存"""
        return self.config.enabled
    
    @property
    def ttl(self) -> int:
        """缓存过期时间"""
        return self.config.ttl
        
    @property
    def cleanup_interval(self) -> int:
        """缓存清理间隔"""
        return self.config.cleanup_interval
    
    def _get_duration_seconds(self, value: Union[int, timedelta]) -> int:
        """将时间值转换为秒数"""
        return int(value.total_seconds()) if isinstance(value, timedelta) else value

    def _get_ttl_seconds(self) -> int:
        """获取 TTL 秒数"""
        return self._get_duration_seconds(self.ttl)
        
    def _get_cleanup_interval_seconds(self) -> int:
        """获取清理间隔秒数"""
        return self._get_duration_seconds(self.cleanup_interval)

    def _log_cache_operation(self, operation: str, key: str, extra: str = "") -> None:
        """记录缓存操作日志
        
        根据不同的操作类型使用不同的日志级别:
        - hit/miss: DEBUG级别
        - set/delete: DEBUG级别
        - clear/error: INFO级别
        - warning: WARNING级别
        """
        # 根据操作类型决定日志级别
        log_level = logging.DEBUG  # 默认使用DEBUG级别
        
        # 关键操作提升到INFO级别
        if operation in ['clear pattern', 'invalidate', 'soft_delete', 'restore', 'delete', 'cleanup']:
            log_level = logging.INFO
        # 警告提升到WARNING级别
        elif operation.startswith('warn') or operation.startswith('skip'):
            log_level = logging.WARNING
        
        # 检查日志级别是否已启用
        if logger.isEnabledFor(log_level):
            message = f"Cache {operation}: {key}"
            if extra:
                message += f" ({extra})"
            logger.log(log_level, message)

    def _get_operation_id(self, ctx: InterceptorContext[T]) -> str:
        """获取操作的唯一标识符"""
        entity_id = self._get_entity_id(ctx)
        operation_parts = [
            ctx.entity_type.__name__,
            ctx.operation.name,
            entity_id
        ]
        
        query_params = self._extract_query_params(ctx)
        if query_params:
            operation_parts.append(str(hash(frozenset(query_params.items()))))
            
        return ':'.join(operation_parts)
        
    def _get_entity_id(self, ctx: InterceptorContext[T]) -> str:
        """获取实体ID"""
        if ctx.entity and hasattr(ctx.entity, 'id'):
            return str(ctx.entity.id)
        elif ctx.entities:
            entity_ids = sorted(
                str(getattr(e, 'id', id(e)))
                for e in ctx.entities
                if hasattr(e, 'id')
            )
            return ','.join(entity_ids) if entity_ids else str(id(ctx))
        return str(id(ctx))

    def _normalize_value(self, value: Any) -> str:
        """标准化值以用于缓存键"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (list, tuple)):
            return ",".join(sorted(str(x) for x in value))
        elif isinstance(value, dict):
            return ",".join(f"{k}:{self._normalize_value(v)}" 
                          for k, v in sorted(value.items()))
        return str(value)

    def _normalize_query_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        """标准化查询参数"""
        return {
            str(k): self._normalize_value(v)
            for k, v in params.items()
            if v is not None  # 忽略None值
        }

    def _extract_query_params(self, ctx: InterceptorContext[T]) -> Optional[Dict[str, Any]]:
        """从上下文中提取查询参数"""
        if not ctx.context_data:
            return None
            
        params = {}
        
        # 1. 处理标准查询参数
        if "query_params" in ctx.context_data:
            params.update(ctx.context_data["query_params"])
            
        # 2. 处理直接的查询参数
        special_keys = {
            "entity_id", "query_params", "filters", 
            "order_by", "sort_by", "sort_order",
            "page", "page_size", "limit", "offset",
            "include_count", "include_total"
        }
        direct_params = {
            k: v for k, v in ctx.context_data.items()
            if k not in special_keys and not k.startswith("_")
        }
        if direct_params:
            params.update(direct_params)
            
        # 3. 处理过滤条件
        if "filters" in ctx.context_data:
            filters = ctx.context_data["filters"]
            if isinstance(filters, dict):
                params["filters"] = filters
                
        # 4. 处理分页参数
        pagination_params = {}
        if "page" in ctx.context_data:
            page = ctx.context_data["page"]
            page_size = ctx.context_data.get("page_size", 10)
            if page is not None:
                pagination_params["page"] = page
                pagination_params["page_size"] = page_size
        elif "offset" in ctx.context_data:
            offset = ctx.context_data["offset"]
            limit = ctx.context_data.get("limit", 10)
            if offset is not None:
                pagination_params["offset"] = offset
                pagination_params["limit"] = limit
        if pagination_params:
            params["pagination"] = pagination_params
            
        # 5. 处理排序参数
        sort_params = {}
        if "order_by" in ctx.context_data:
            sort_params["order_by"] = ctx.context_data["order_by"]
        elif "sort_by" in ctx.context_data:
            sort_params["sort_by"] = ctx.context_data["sort_by"]
            sort_params["sort_order"] = ctx.context_data.get("sort_order", "asc")
        if sort_params:
            params["sort"] = sort_params
            
        return params if params else None

    def _get_list_cache_key(self, entity_type: str, params: Dict[str, Any]) -> str:
        """生成列表查询的缓存键"""
        # 不要在这里添加前缀，让_get_cache_key处理前缀
        key_parts = ["list"]  # 移除entity_type，因为它会在_get_cache_key中添加
        
        # 添加过滤条件
        if "filters" in params:
            filters_str = self._normalize_value(params["filters"])
            key_parts.append(f"filters:{filters_str}")
            
        # 添加分页参数
        if "pagination" in params:
            pagination = params["pagination"]
            if "page" in pagination:
                key_parts.append(f"page:{pagination['page']}:{pagination['page_size']}")
            else:
                key_parts.append(f"offset:{pagination['offset']}:{pagination['limit']}")
                
        # 添加排序参数
        if "sort" in params:
            sort = params["sort"]
            if "order_by" in sort:
                key_parts.append(f"order:{sort['order_by']}")
            else:
                key_parts.append(f"sort:{sort['sort_by']}:{sort['sort_order']}")
                
        # 添加其他查询参数
        other_params = {
            k: v for k, v in params.items()
            if k not in ["filters", "pagination", "sort"]
        }
        if other_params:
            normalized = self._normalize_query_params(other_params)
            if normalized:
                params_str = ",".join(f"{k}:{v}" for k, v in sorted(normalized.items()))
                key_parts.append(f"params:{params_str}")
                
        return ":".join(key_parts)  # 返回不带前缀的键部分

    def _get_query_cache_key(self, entity_type: str, params: Dict[str, Any]) -> str:
        """生成查询缓存键"""
        # 处理ID查询
        if "entity_id" in params:
            return f"id:{params['entity_id']}"
            
        normalized_params = self._normalize_query_params(params)
        if normalized_params:
            params_str = ",".join(f"{k}:{v}" for k, v in sorted(normalized_params.items()))
            return f"query:params:{params_str}"
        return "query"

    def _get_cache_key(self, ctx: InterceptorContext[T]) -> Optional[str]:
        """生成缓存键"""
        try:
            # 优先使用上下文中的自定义cache_key（如果存在）
            if "cache_key" in ctx.context_data:
                custom_key = ctx.context_data["cache_key"]
                self._log_cache_operation("custom_key", custom_key, "using custom key from context")
                return custom_key
        
            entity_type = ctx.entity_type.__name__.lower()
            if entity_type.endswith('po'):
                entity_type = entity_type[:-2]
            
            # 处理ID查询
            if "entity_id" in ctx.context_data:
                return f"{entity_type}:id:{ctx.context_data['entity_id']}"
                
            # 处理查询参数
            query_params = self._extract_query_params(ctx)
            if query_params:
                # 处理ID查询
                if "id" in query_params:
                    return f"{entity_type}:id:{query_params['id']}"
                    
                if self._is_list_query(ctx, query_params):
                    list_key = self._get_list_cache_key(entity_type, query_params)
                    return f"{entity_type}:{list_key}"
                    
                # 处理其他查询
                normalized_params = self._normalize_query_params(query_params)
                if normalized_params:
                    params_str = ",".join(f"{k}:{v}" for k, v in sorted(normalized_params.items()))
                    return f"{entity_type}:query:params:{params_str}"
                return f"{entity_type}:query"
                    
            # 处理实体操作
            if ctx.entity and hasattr(ctx.entity, 'id'):
                return f"{entity_type}:id:{ctx.entity.id}"
                    
            # 处理批量操作
            if ctx.is_batch_operation() and ctx.entities:
                entity_ids = sorted(str(e.id) for e in ctx.entities if hasattr(e, 'id'))
                if entity_ids:
                    return f"{entity_type}:batch:{','.join(entity_ids)}"
            
            return None
            
        except Exception as e:
            logger.warning(f"Error generating cache key: {str(e)}", exc_info=True)
            return None

    def _is_list_query(self, ctx: InterceptorContext[T], params: Dict[str, Any]) -> bool:
        """检查是否是列表查询"""
        return (
            "pagination" in params or
            ctx.operation == OperationType.QUERY or
            ctx.operation == OperationType.FIND or
            ctx.is_batch_operation()
        )

    async def _ensure_initialized(self) -> None:
        """确保缓存管理器已初始化"""
        if self.__class__._initialized:
            return
            
        async with self.__class__._initialization_lock:
            if self.__class__._initialized:
                return
                
            try:
                if not self.__class__._cache_manager:
                    self.__class__._cache_manager = self.cache_manager
                    
                # 验证缓存管理器是否可用
                test_key = "_cache_test_key"
                await self.__class__._cache_manager.set(test_key, "test", 1)
                await self.__class__._cache_manager.delete(test_key)
                
                self.__class__._initialized = True
                logger.info(
                    f"Cache interceptor initialized with "
                    f"TTL: {self._get_ttl_seconds()}s, "
                    f"cleanup interval: {self._get_cleanup_interval_seconds()}s"
                )
            except Exception as e:
                logger.error(f"Failed to initialize cache: {str(e)}")
                self.__class__._cache_manager = None
                self.__class__._initialized = False
                raise

    async def before_operation(
        self,
        ctx: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]]
    ) -> Any:
        """操作前处理"""
        if not self.enabled:
            return await next_interceptor(ctx)
            
        await self._ensure_initialized()
        
        try:
            async with self._get_operation_lock(ctx):
                if not self._should_cache_operation(ctx):
                    return await next_interceptor(ctx)
                    
                cache_key = self._get_cache_key(ctx)
                if not cache_key:
                    return await next_interceptor(ctx)
                    
                # 检查缓存
                cached_value = await self._check_and_return_cached(ctx, cache_key)
                if cached_value is not None:
                    # 如果命中缓存，直接返回缓存值，不再执行后续操作
                    ctx.result = cached_value
                    return cached_value
                    
                # 执行操作
                result = await next_interceptor(ctx)
                
                # 只有在读操作时才设置缓存
                if (
                    result is not None and
                    ctx.operation in [OperationType.READ, OperationType.QUERY, OperationType.FIND] and
                    cache_key not in self._cleared_cache_keys
                ):
                    # 检查实体是否被软删除
                    should_cache = True
                    
                    # 检查单个实体
                    if hasattr(result, 'is_deleted'):
                        if getattr(result, 'is_deleted') is True:
                            should_cache = False
                            self._log_cache_operation("skip_cache", cache_key, "entity is soft-deleted")
                    
                    # 检查实体列表
                    elif isinstance(result, list) and result and hasattr(result[0], 'is_deleted'):
                        # 对于列表，我们仍然缓存，因为列表可能包含未删除的实体
                        pass
                    
                    if should_cache:
                        # 记录键跟踪日志
                        if ":id:" in cache_key:
                            entity_id = cache_key.split(":id:")[1] if ":id:" in cache_key else "unknown"
                            self._log_cache_operation("tracking_id", cache_key, f"ID: {entity_id}")
                        
                        # 设置缓存
                        await self.cache_manager.set(
                            cache_key,
                            result,
                            self._get_ttl_seconds()
                        )
                        
                        # 添加到跟踪集合
                        await self._add_to_key_set(cache_key)
                        self._log_cache_operation("set", cache_key)
            
                return result
    
        except Exception as e:
            logger.error(f"Error in before_operation: {str(e)}", exc_info=True)
            return await next_interceptor(ctx)

    def _should_cache_operation(self, ctx: InterceptorContext[T]) -> bool:
        """检查是否应该缓存操作"""
        return (
            ctx.operation in [OperationType.READ, OperationType.QUERY, OperationType.FIND] and
            not self._is_operation_processed(ctx)
        )

    async def _check_and_return_cached(
        self,
        ctx: InterceptorContext[T],
        cache_key: str
    ) -> Optional[Any]:
        """检查并返回缓存的结果"""
        # 检查键是否已被清除
        if cache_key in self._cleared_cache_keys:
            self._log_cache_operation("miss", cache_key, "invalidated")
            return None
            
        # 检查模式是否已被清除
        for pattern in self._cleared_patterns:
            if pattern.rstrip('*') in cache_key:
                self._log_cache_operation("miss", cache_key, "pattern invalidated")
                return None
                    
        # 尝试从缓存获取
        cached_value = await self.cache_manager.get(cache_key)
        if cached_value is not None:
            self._log_cache_operation("hit", cache_key)
            return cached_value
            
        self._log_cache_operation("miss", cache_key)
        return None

    async def process_result(
        self,
        ctx: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[InterceptorContext[T], Any], Awaitable[Any]]
    ) -> Any:
        """处理操作结果"""
        if not self.enabled:
            return await next_interceptor(ctx, result)
            
        await self._ensure_initialized()
        
        try:
            async with self._get_operation_lock(ctx):
                if self._is_operation_processed(ctx):
                    return await next_interceptor(ctx, result)
                    
                self._mark_operation_processed(ctx)
                
                # 写操作：清理缓存
                if ctx.operation in [OperationType.UPDATE, OperationType.DELETE]:
                    await self._handle_write_result(ctx)
                    await self._maybe_cleanup_cache()
                    
                return await next_interceptor(ctx, result)
                
        finally:
            self._cleanup_operation(ctx)

    async def _handle_write_result(self, ctx: InterceptorContext[T]) -> None:
        """处理写入操作结果"""
        entity_type = ctx.entity_type.__name__.lower()
        if entity_type.endswith('po'):
            entity_type = entity_type[:-2]
            
        try:
            # 使用新的_invalidate_related_caches方法处理所有缓存清理逻辑
            await self._invalidate_related_caches(ctx)
                
        except Exception as e:
            logger.error(
                f"Failed to handle write result for {entity_type}: {str(e)}",
                exc_info=True
            )

    def _cleanup_operation(self, ctx: InterceptorContext[T]) -> None:
        """清理操作相关资源"""
        op_id = self._get_operation_id(ctx)
        
        if ctx.operation == OperationType.COMMIT:
            # 提交时清理操作锁和处理标记
            self.__class__._operation_locks.pop(op_id, None)
            self._clear_operation_processed(ctx)
            # 清理已处理的缓存模式
            self._cleared_patterns.clear()
        elif ctx.operation == OperationType.ROLLBACK:
            # 回滚时只清理操作锁和处理标记
            self.__class__._operation_locks.pop(op_id, None)
            self._clear_operation_processed(ctx)
            # 回滚时不清理缓存模式，保持缓存一致性

    async def handle_exception(
        self,
        ctx: InterceptorContext[T],
        error: Exception,
        next_interceptor: Callable[[InterceptorContext[T], Exception], Awaitable[Optional[Exception]]]
    ) -> Optional[Exception]:
        """处理异常"""
        if not self.enabled:
            return await next_interceptor(ctx, error)
            
        await self._ensure_initialized()
        
        try:
            # 发生异常时，标记当前操作需要回滚
            op_id = self._get_operation_id(ctx)
            self.__class__._operation_locks.pop(op_id, None)
            self._clear_operation_processed(ctx)
            
            # 记录错误日志
            logger.error(
                f"Cache operation failed for {ctx.entity_type.__name__}: {str(error)}",
                exc_info=True
            )
        except Exception as e:
            logger.error(f"Error handling cache exception: {str(e)}", exc_info=True)
            
        return await next_interceptor(ctx, error)

    def _get_operation_lock(self, ctx: InterceptorContext[T]) -> asyncio.Lock:
        """获取操作锁"""
        op_id = self._get_operation_id(ctx)
        if op_id not in self.__class__._operation_locks:
            self.__class__._operation_locks[op_id] = asyncio.Lock()
        return self.__class__._operation_locks[op_id]

    def _is_operation_processed(self, ctx: InterceptorContext[T]) -> bool:
        """检查操作是否已经处理过"""
        op_id = self._get_operation_id(ctx)
        return op_id in self.__class__._processed_operations

    def _mark_operation_processed(self, ctx: InterceptorContext[T]) -> None:
        """标记操作为已处理"""
        op_id = self._get_operation_id(ctx)
        self.__class__._processed_operations.add(op_id)

    def _clear_operation_processed(self, ctx: InterceptorContext[T]) -> None:
        """清除操作的处理标记"""
        op_id = self._get_operation_id(ctx)
        self.__class__._processed_operations.discard(op_id)

    async def _maybe_cleanup_cache(self) -> None:
        """按需清理缓存"""
        current_time = time.time()
        cleanup_interval_seconds = self._get_cleanup_interval_seconds()
            
        if current_time - self.__class__._last_cleanup < cleanup_interval_seconds:
            return
            
        try:
            # 清理已追踪的过期键
            ttl_seconds = self._get_ttl_seconds()
            expired_keys = {
                key for key in self.__class__._cleared_cache_keys
                if current_time - self._get_key_timestamp(key) > ttl_seconds
            }
            
            if expired_keys:
                for key in expired_keys:
                    self.__class__._cleared_cache_keys.discard(key)
                self._log_cache_operation("cleanup", str(len(expired_keys)), "tracked keys")
            
            # Redis特定的清理操作
            if self.is_redis_cache:
                await self._cleanup_redis_keys()
                
            self.__class__._last_cleanup = current_time
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {str(e)}", exc_info=True)

    async def _cleanup_redis_keys(self) -> None:
        """清理Redis过期键"""
        try:
            redis = self.cache_manager._cache._client
            cursor = b'0'
            batch_size = 100
            total_cleaned = 0
            
            while cursor:
                cursor, keys = await redis.scan(
                    cursor=cursor,
                    count=batch_size
                )
                
                if keys:
                    # 检查每个键的TTL
                    pipeline = redis.pipeline()
                    for key in keys:
                        pipeline.ttl(key)
                    ttls = await pipeline.execute()
                    
                    # 删除已过期的键
                    expired = [
                        key for key, ttl in zip(keys, ttls)
                        if ttl is not None and ttl <= 0
                    ]
                    
                    if expired:
                        pipeline = redis.pipeline()
                        for key in expired:
                            pipeline.delete(key)
                        await pipeline.execute()
                        total_cleaned += len(expired)
                
                # 转换为字符串
                cursor = cursor if isinstance(cursor, bytes) else str(cursor).encode()
                if cursor == b'0':
                    break
                    
            if total_cleaned > 0:
                self._log_cache_operation("cleanup", str(total_cleaned), "expired Redis keys")
                
        except Exception as e:
            logger.error(f"Error cleaning Redis keys: {str(e)}", exc_info=True)

    def _get_key_timestamp(self, key: str) -> float:
        """获取缓存键的时间戳"""
        return time.time()

    async def _add_to_key_set(self, cache_key: str) -> None:
        """将缓存键添加到跟踪集合
        
        注意：CacheManager的后端已经处理了前缀，我们只跟踪原始键
        """
        # 这个方法可以保留简单实现，因为使用Redis的内置集合管理跟踪集，这在RedisCache中没有完全实现
        if self.is_redis_cache:
            redis = self.cache_manager._cache._client
            await redis.sadd(self._key_set_name, cache_key)
            # 设置集合的过期时间
            await redis.expire(self._key_set_name, self._get_ttl_seconds())

    async def _remove_from_key_set(self, cache_key: str) -> None:
        """从跟踪集合中移除缓存键"""
        if self.is_redis_cache:
            redis = self.cache_manager._cache._client
            await redis.srem(self._key_set_name, cache_key)

    async def _get_matching_keys(self, pattern: str) -> set[str]:
        """获取匹配模式的所有缓存键"""
        matching_keys = set()
        if self.is_redis_cache:
            redis = self.cache_manager._cache._client
            # 获取前缀
            cache_prefix = getattr(self.cache_manager.config, 'prefix', '')
            # 构建完整模式
            full_pattern = f"{cache_prefix}{pattern}"
            self._log_cache_operation("match", pattern, f"Using full pattern: {full_pattern}")
            
            # 从集合中获取所有键
            all_keys = await redis.smembers(self._key_set_name)
            if not all_keys:
                return matching_keys
                
            # 在Python中进行模式匹配
            import fnmatch

            # 处理ID匹配的特殊情况
            if ':id:' in pattern:
                entity_id = pattern.split(':id:')[1]
                id_pattern = f"{cache_prefix}*:id:{entity_id}"
                
                for key in all_keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    if fnmatch.fnmatch(key_str, id_pattern) or fnmatch.fnmatch(key_str, full_pattern):
                        matching_keys.add(key_str)
                        self._log_cache_operation("matched", key_str, f"ID pattern: {pattern}")
            else:
                # 常规模式匹配
                for key in all_keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    if fnmatch.fnmatch(key_str, full_pattern):
                        matching_keys.add(key_str)
                        self._log_cache_operation("matched", key_str, f"Pattern: {pattern}")
                        
            self._log_cache_operation("match_result", pattern, f"Found {len(matching_keys)} matching keys")
        return matching_keys

    async def _clear_cache_pattern(self, ctx: InterceptorContext[T], pattern: str) -> None:
        """清除匹配指定模式的缓存
        
        直接使用CacheManager的delete_pattern方法，避免重复实现
        """
        try:
            # 如果模式已经被清理过，跳过，但不产生警告日志
            if pattern in self._cleared_patterns:
                # 只在DEBUG级别记录已跳过的模式，而不是警告级别
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Skip clearing cache pattern '{pattern}': already cleared")
                return
            
            # 记录清除模式
            self._log_cache_operation("clear pattern", pattern, f"operation: {ctx.operation.name}")
            
            # 使用CacheManager的delete_pattern方法删除匹配的缓存键
            await self.cache_manager.delete_pattern(pattern)
            
            # 标记模式为已清理，避免重复清理
            self._cleared_patterns.add(pattern)
            
        except Exception as e:
            logger.warning(f"Failed to clear cache pattern '{pattern}': {str(e)}", exc_info=True)

    async def _invalidate_related_caches(self, ctx: InterceptorContext[T]) -> None:
        """清除相关的缓存"""
        entity_type = ctx.entity_type.__name__.lower()
        if entity_type.endswith('po'):
            entity_type = entity_type[:-2]
        
        try:
            patterns_to_clear = set()  # 使用集合避免重复模式
            
            # 1. 获取实体ID和操作类型
            if ctx.entity and hasattr(ctx.entity, 'id'):
                entity_id = str(ctx.entity.id)
                
                # 检查操作类型
                is_soft_delete = (
                    ctx.operation == OperationType.UPDATE and 
                    ctx.context_data.get("soft_deleted") is True
                )
                is_restore = (
                    ctx.operation == OperationType.UPDATE and
                    ctx.context_data.get("soft_deleted") is False and
                    hasattr(ctx.entity, 'is_deleted') and
                    getattr(ctx.entity, 'is_deleted') is True  # 之前是删除状态
                )
                
                # 2. 根据操作类型确定需要清除的缓存模式
                
                # ID缓存 - 适用于所有操作，这是最重要的
                id_cache_key = f"{entity_type}:id:{entity_id}"
                patterns_to_clear.add(id_cache_key)
                
                # 对于不同操作类型，选择性地添加其他模式
                if is_soft_delete:
                    # 软删除：清理有限的相关缓存
                    patterns_to_clear.add(f"{entity_type}:query:id:{entity_id}")
                    self._log_cache_operation(
                        "soft_delete",
                        id_cache_key,
                        "state change only"
                    )
                elif is_restore:
                    # 恢复：清理列表缓存
                    patterns_to_clear.add(f"{entity_type}:query:id:{entity_id}")
                    patterns_to_clear.add(f"{entity_type}:list:*:params:is_deleted:*")
                    self._log_cache_operation(
                        "restore",
                        id_cache_key,
                        "state change affecting lists"
                    )
                elif ctx.operation == OperationType.DELETE:
                    # 硬删除：清理关键缓存
                    patterns_to_clear.add(f"{entity_type}:query:id:{entity_id}")
                    self._log_cache_operation(
                        "delete",
                        id_cache_key,
                        "hard delete"
                    )
                else:
                    # 普通更新：只清理ID缓存
                    self._log_cache_operation(
                        "update",
                        id_cache_key,
                        "normal update"
                    )
            
            # 3. 如果是批量操作，添加批量相关的缓存模式
            if ctx.is_batch_operation() and ctx.entities:
                entity_ids = [str(e.id) for e in ctx.entities if hasattr(e, 'id')]
                if entity_ids:
                    # 添加批量操作相关缓存模式（适度优化，只清理必要的键）
                    for eid in entity_ids:
                        patterns_to_clear.add(f"{entity_type}:id:{eid}")
            
            # 4. 执行缓存清理
            cleared_count = 0
            for pattern in patterns_to_clear:
                try:
                    # 使用封装好的方法清理缓存，避免代码重复
                    await self._clear_cache_pattern(ctx, pattern)
                    cleared_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to clear cache pattern '{pattern}': {str(e)}",
                        exc_info=True
                    )
            
            # 记录清理操作
            if cleared_count > 0 and ctx.entity and hasattr(ctx.entity, 'id'):
                self._log_cache_operation(
                    "invalidate",
                    f"{entity_type}:id:{ctx.entity.id}",
                    f"cleared {cleared_count} patterns"
                )
                
        except Exception as e:
            logger.error(
                f"Failed to invalidate caches for {entity_type}: {str(e)}",
                exc_info=True
            )