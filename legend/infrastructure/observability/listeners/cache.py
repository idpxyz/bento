"""
缓存监听器
用于监控缓存操作性能和进行链路追踪
"""
import functools
import inspect
import logging
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from typing import cast as type_cast

from ..core import IMetricsRecorder, ITracer, SpanKind
from ..core.metadata import StandardMetrics

logger = logging.getLogger(__name__)

# 类型变量定义
F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])


class CacheListener:
    """缓存监听器，用于监控缓存操作"""

    def __init__(
        self,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
        cache_name: str = "default",
    ):
        """初始化缓存监听器

        Args:
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            cache_name: 缓存名称，用于标识不同的缓存实例
        """
        self.metrics_recorder = metrics_recorder
        self.tracer = tracer
        self.cache_name = cache_name

    def instrument_method(
        self, operation: str, is_hit_method: bool = False
    ) -> Callable[[F], F]:
        """装饰同步缓存方法，添加监控

        Args:
            operation: 操作名称，如 get, set, delete
            is_hit_method: 是否是命中判断方法

        Returns:
            Callable: 方法装饰器
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                hit = None
                key = self._extract_key_from_args(args, kwargs, func)
                span = None

                try:
                    # 创建 span
                    if self.tracer:
                        span_name = f"cache.{operation}"
                        span_attributes = {
                            "cache.operation": operation,
                            "cache.name": self.cache_name
                        }
                        if key:
                            span_attributes["cache.key"] = str(key)

                        span = self.tracer.start_span(
                            name=span_name,
                            kind=SpanKind.CLIENT,
                            attributes=span_attributes
                        )

                    # 执行原始方法
                    result = func(*args, **kwargs)

                    # 判断是否命中（仅针对获取操作）
                    if is_hit_method:
                        hit = bool(result)

                    return result
                except Exception as e:
                    # 记录异常
                    error_type = type(e).__name__

                    if span:
                        span.record_exception(e)
                        span.set_attribute("error", True)
                        span.set_attribute("error.type", error_type)

                    # 记录错误指标
                    self.metrics_recorder.increment_counter(
                        "cache_errors_total",
                        1.0,
                        {"operation": operation, "error": error_type,
                            "cache": self.cache_name}
                    )

                    raise
                finally:
                    # 计算执行时间
                    duration = time.time() - start_time

                    # 记录耗时指标
                    self.metrics_recorder.observe_histogram(
                        StandardMetrics.CACHE_OPERATION_DURATION.name,
                        duration,
                        {"operation": operation, "cache": self.cache_name}
                    )

                    # 记录命中/未命中指标
                    if hit is not None:
                        if hit:
                            self.metrics_recorder.increment_counter(
                                StandardMetrics.CACHE_HITS.name,
                                1.0,
                                {"cache": self.cache_name}
                            )
                        else:
                            self.metrics_recorder.increment_counter(
                                StandardMetrics.CACHE_MISSES.name,
                                1.0,
                                {"cache": self.cache_name}
                            )

                    # 结束 span
                    if span:
                        # 添加命中信息
                        if hit is not None:
                            span.set_attribute("cache.hit", hit)

                        # 结束 span
                        if hasattr(span, "_end_span"):
                            span._end_span()

            return type_cast(F, wrapper)

        return decorator

    def instrument_async_method(
        self, operation: str, is_hit_method: bool = False
    ) -> Callable[[AsyncF], AsyncF]:
        """装饰异步缓存方法，添加监控

        Args:
            operation: 操作名称，如 get, set, delete
            is_hit_method: 是否是命中判断方法

        Returns:
            Callable: 方法装饰器
        """
        def decorator(func: AsyncF) -> AsyncF:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                hit = None
                key = self._extract_key_from_args(args, kwargs, func)
                span = None

                try:
                    # 创建 span
                    if self.tracer:
                        span_name = f"cache.{operation}"
                        span_attributes = {
                            "cache.operation": operation,
                            "cache.name": self.cache_name
                        }
                        if key:
                            span_attributes["cache.key"] = str(key)

                        span = await self.tracer.start_span(
                            name=span_name,
                            kind=SpanKind.CLIENT,
                            attributes=span_attributes
                        )

                    # 执行原始方法
                    result = await func(*args, **kwargs)

                    # 判断是否命中（仅针对获取操作）
                    if is_hit_method:
                        hit = bool(result)

                    return result
                except Exception as e:
                    # 记录异常
                    error_type = type(e).__name__

                    if span:
                        span.record_exception(e)
                        span.set_attribute("error", True)
                        span.set_attribute("error.type", error_type)

                    # 记录错误指标
                    await self.metrics_recorder.increment_counter(
                        "cache_errors_total",
                        1.0,
                        {"operation": operation, "error": error_type,
                            "cache": self.cache_name}
                    )

                    raise
                finally:
                    # 计算执行时间
                    duration = time.time() - start_time

                    # 记录耗时指标
                    await self.metrics_recorder.observe_histogram(
                        StandardMetrics.CACHE_OPERATION_DURATION.name,
                        duration,
                        {"operation": operation, "cache": self.cache_name}
                    )

                    # 记录命中/未命中指标
                    if hit is not None:
                        if hit:
                            await self.metrics_recorder.increment_counter(
                                StandardMetrics.CACHE_HITS.name,
                                1.0,
                                {"cache": self.cache_name}
                            )
                        else:
                            await self.metrics_recorder.increment_counter(
                                StandardMetrics.CACHE_MISSES.name,
                                1.0,
                                {"cache": self.cache_name}
                            )

                    # 结束 span
                    if span:
                        # 添加命中信息
                        if hit is not None:
                            span.set_attribute("cache.hit", hit)

                        # 结束 span
                        if hasattr(span, "_end_span"):
                            span._end_span()

            return type_cast(AsyncF, wrapper)

        return decorator

    def _extract_key_from_args(
        self, args: tuple, kwargs: dict, func: Callable
    ) -> Optional[str]:
        """从参数中提取缓存键

        Args:
            args: 位置参数
            kwargs: 关键字参数
            func: 原始函数

        Returns:
            Optional[str]: 缓存键，无法提取时返回None
        """
        try:
            # 获取参数信息
            sig = inspect.signature(func)
            params = list(sig.parameters.values())

            # 跳过第一个self/cls参数
            if params and params[0].name in ('self', 'cls'):
                params = params[1:]

            # 尝试获取名为 key 的参数
            for i, param in enumerate(params):
                if param.name == 'key':
                    if i < len(args):
                        return str(args[i])
                    elif 'key' in kwargs:
                        return str(kwargs['key'])

            # 如果没有名为 key 的参数，尝试获取第一个参数
            if params and len(args) > 1:  # 跳过self/cls
                return str(args[1])
        except Exception:
            pass

        return None

    def instrument_redis_client(self, client: Any) -> Any:
        """监控Redis客户端

        Args:
            client: Redis客户端实例

        Returns:
            Any: 装饰后的Redis客户端
        """
        # 同步方法
        for method_name in ['get', 'hget', 'hmget', 'hgetall', 'smembers', 'lrange']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_method(
                    method_name, is_hit_method=True)(original_method)
                setattr(client, method_name, instrumented_method)

        for method_name in ['set', 'hset', 'hmset', 'sadd', 'lpush', 'rpush']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_method(
                    method_name)(original_method)
                setattr(client, method_name, instrumented_method)

        for method_name in ['delete', 'expire', 'hdel', 'srem', 'lrem']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_method(
                    method_name)(original_method)
                setattr(client, method_name, instrumented_method)

        # 异步方法
        for method_name in ['aget', 'ahget', 'ahmget', 'ahgetall', 'asmembers', 'alrange']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_async_method(
                    method_name.lstrip('a'), is_hit_method=True)(original_method)
                setattr(client, method_name, instrumented_method)

        for method_name in ['aset', 'ahset', 'ahmset', 'asadd', 'alpush', 'arpush']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_async_method(
                    method_name.lstrip('a'))(original_method)
                setattr(client, method_name, instrumented_method)

        for method_name in ['adelete', 'aexpire', 'ahdel', 'asrem', 'alrem']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_async_method(
                    method_name.lstrip('a'))(original_method)
                setattr(client, method_name, instrumented_method)

        return client

    def instrument_memcached_client(self, client: Any) -> Any:
        """监控Memcached客户端

        Args:
            client: Memcached客户端实例

        Returns:
            Any: 装饰后的Memcached客户端
        """
        # 同步方法
        for method_name in ['get', 'gets']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_method(
                    method_name, is_hit_method=True)(original_method)
                setattr(client, method_name, instrumented_method)

        for method_name in ['set', 'add', 'replace', 'append', 'prepend']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_method(
                    method_name)(original_method)
                setattr(client, method_name, instrumented_method)

        for method_name in ['delete', 'touch', 'incr', 'decr']:
            if hasattr(client, method_name):
                original_method = getattr(client, method_name)
                instrumented_method = self.instrument_method(
                    method_name)(original_method)
                setattr(client, method_name, instrumented_method)

        return client

    @classmethod
    def install(
        cls,
        client: Any,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
        cache_name: str = "default",
        client_type: Optional[str] = None,
    ) -> "CacheListener":
        """便捷安装方法

        Args:
            client: 缓存客户端实例
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            cache_name: 缓存名称
            client_type: 客户端类型，如果为None则自动检测

        Returns:
            CacheListener: 监听器实例
        """
        listener = cls(metrics_recorder, tracer, cache_name)

        # 自动检测客户端类型
        if client_type is None:
            if hasattr(client, 'get') and hasattr(client, 'set') and hasattr(client, 'delete'):
                # 检查客户端名称
                client_class_name = client.__class__.__name__.lower()
                if 'redis' in client_class_name:
                    client_type = 'redis'
                elif 'memcached' in client_class_name or 'pylibmc' in client_class_name:
                    client_type = 'memcached'
                else:
                    client_type = 'generic'
            else:
                raise ValueError("Unsupported cache client type")

        # 应用监控
        if client_type == 'redis':
            listener.instrument_redis_client(client)
        elif client_type == 'memcached':
            listener.instrument_memcached_client(client)
        elif client_type == 'generic':
            # 通用缓存客户端
            for method_name in ['get']:
                if hasattr(client, method_name):
                    original_method = getattr(client, method_name)
                    instrumented_method = (
                        listener.instrument_async_method if inspect.iscoroutinefunction(original_method)
                        else listener.instrument_method
                    )(method_name, is_hit_method=True)(original_method)
                    setattr(client, method_name, instrumented_method)

            for method_name in ['set', 'delete']:
                if hasattr(client, method_name):
                    original_method = getattr(client, method_name)
                    instrumented_method = (
                        listener.instrument_async_method if inspect.iscoroutinefunction(original_method)
                        else listener.instrument_method
                    )(method_name)(original_method)
                    setattr(client, method_name, instrumented_method)
        else:
            raise ValueError(f"Unsupported client_type: {client_type}")

        return listener


# 使用示例
"""
# Redis
import redis
from redis import Redis

redis_client = Redis(host='localhost', port=6379, db=0)
listener = CacheListener.install(
    redis_client,
    metrics_recorder,
    tracer,
    cache_name="main-redis"
)

# 异步Redis
import aioredis

async def setup_redis():
    redis = await aioredis.create_redis_pool('redis://localhost')
    listener = CacheListener.install(
        redis,
        metrics_recorder,
        tracer,
        cache_name="async-redis"
    )
    return redis

# Memcached
import pylibmc

memcached_client = pylibmc.Client(["127.0.0.1"], binary=True)
listener = CacheListener.install(
    memcached_client,
    metrics_recorder,
    tracer,
    cache_name="memcached"
)
"""
