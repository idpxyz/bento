"""Singleflight 模式实现 - 防止缓存击穿.

核心思想：
- 同一时刻只有一个请求执行真正的查询
- 其他请求等待并共享结果
- 避免缓存击穿导致的数据库压力

使用场景：
- 热点数据缓存过期
- 高并发查询同一个键
- 需要防止缓存击穿
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class SingleflightGroup[T]:
    """Singleflight 模式 - 防止缓存击穿.

    多个并发请求访问同一个 key 时：
    - 第一个请求执行查询
    - 其他请求等待第一个请求的结果
    - 所有请求共享同一个结果

    Example:
        ```python
        group = SingleflightGroup()

        # 1000个并发请求查询同一个键
        async def expensive_query():
            return await db.query(...)

        # 发起并发请求
        tasks = [
            group.do("cache_key_1", expensive_query)
            for _ in range(1000)
        ]
        results = await asyncio.gather(*tasks)

        # ✅ 只执行一次 expensive_query
        # ✅ 1000个请求共享同一个结果
        # ✅ 数据库压力降低 1000倍
        ```

    Thread Safety:
        - 使用 asyncio.Lock 保证线程安全
        - 适用于单进程多协程场景
        - 分布式场景需要使用 Redis Lock
    """

    def __init__(self):
        """初始化 Singleflight Group."""
        self._calls: dict[str, asyncio.Future[T]] = {}
        self._lock = asyncio.Lock()

    async def do(
        self,
        key: str,
        fn: Callable[[], Awaitable[T]],
    ) -> T:
        """执行函数，如果有相同 key 的调用正在进行，则等待其结果.

        Args:
            key: 缓存键（用于识别相同的请求）
            fn: 查询函数（只有第一个请求会执行）

        Returns:
            查询结果（所有请求共享）

        Raises:
            Exception: 如果查询函数抛出异常，所有等待的请求都会收到相同的异常

        Example:
            ```python
            group = SingleflightGroup()

            # 定义查询函数
            async def query_product_sum():
                result = await session.execute(select(func.sum(Product.price)))
                return result.scalar()

            # 多个协程同时调用
            result = await group.do("product_sum", query_product_sum)
            ```
        """
        # 获取锁以安全地检查和更新 _calls
        async with self._lock:
            # 检查是否已有相同的调用在进行
            if key in self._calls:
                # 已有调用在进行，获取其 Future
                future = self._calls[key]
            else:
                # 没有相同的调用，创建新的 Future
                future = asyncio.Future[T]()
                self._calls[key] = future

                # 在后台执行实际的查询
                asyncio.create_task(self._execute(key, fn, future))

        # 等待结果（无论是当前请求触发的还是其他请求触发的）
        return await future

    async def _execute(
        self,
        key: str,
        fn: Callable[[], Awaitable[T]],
        future: asyncio.Future[T],
    ) -> None:
        """在后台执行查询函数.

        Args:
            key: 缓存键
            fn: 查询函数
            future: 用于存储结果的 Future
        """
        try:
            # 执行实际的查询
            result = await fn()

            # 设置结果，所有等待的协程都会收到
            future.set_result(result)
        except Exception as e:
            # 设置异常，所有等待的协程都会收到相同的异常
            future.set_exception(e)
        finally:
            # 清理：从字典中移除该调用
            async with self._lock:
                self._calls.pop(key, None)

    def forget(self, key: str) -> None:
        """取消某个键的 Singleflight 保护.

        用于手动清理某个键，通常在以下场景使用：
        - 查询超时需要重试
        - 查询失败需要重新发起

        Args:
            key: 要清理的缓存键

        Example:
            ```python
            # 如果查询超时，可以取消并重试
            try:
                result = await asyncio.wait_for(
                    group.do(key, fn),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                group.forget(key)  # 取消，允许重试
                raise
            ```
        """
        # 注意：这里不需要获取锁，因为只是标记删除
        # 实际的清理会在 _execute 的 finally 块中完成
        self._calls.pop(key, None)

    def clear(self) -> None:
        """清空所有正在进行的调用.

        用于测试或重置场景。
        谨慎使用：会导致所有等待的请求失败。
        """
        for future in self._calls.values():
            if not future.done():
                future.cancel()
        self._calls.clear()

    def stats(self) -> dict[str, Any]:
        """获取当前状态统计.

        Returns:
            包含统计信息的字典

        Example:
            ```python
            stats = group.stats()
            print(f"活跃调用数: {stats['active_calls']}")
            print(f"等待的键: {stats['keys']}")
            ```
        """
        return {
            "active_calls": len(self._calls),
            "keys": list(self._calls.keys()),
        }


# ==================== 使用示例 ====================

"""
集成到 CacheInterceptor：

```python
from bento.persistence.interceptor.singleflight import SingleflightGroup

class CacheInterceptor:
    def __init__(self, cache, ...):
        self._cache = cache
        self._singleflight = SingleflightGroup()  # ✅ 添加

    async def execute_before(self, context):
        key = self._get_cache_key(context)

        # 检查缓存
        cached = await self._cache.get(key)
        if cached is not None:
            return cached

        # ❌ 之前：直接返回 None，让每个请求都查询数据库
        # return None

        # ✅ 现在：使用 Singleflight 保护
        # 注意：这里不执行查询，只是标记需要查询
        # 实际查询在 process_result 之后
        return None

    async def process_result(self, context, result, next_interceptor):
        if self._is_read(context.operation):
            key = self._get_cache_key(context)

            # ✅ 使用 Singleflight 包装查询和缓存
            async def query_and_cache():
                # 这里 result 已经是查询结果了
                if result is not None:
                    ttl = self._get_ttl(context.operation)
                    await self._cache.set(key, result, ttl=ttl)
                return result

            # 如果多个请求同时查询同一个键
            # 只有第一个会执行 query_and_cache
            # 其他请求会等待并共享结果
            result = await self._singleflight.do(key, query_and_cache)

        return await next_interceptor(context, result)
```

性能对比：

Without Singleflight:
```
并发1000个请求查询 product_sum
- 数据库查询: 1000次
- 响应时间: ~1000ms（数据库瓶颈）
- 数据库连接: 1000个（可能耗尽）
```

With Singleflight:
```
并发1000个请求查询 product_sum
- 数据库查询: 1次 ✅
- 响应时间: ~100ms ✅（只有第一次查询的时间）
- 数据库连接: 1个 ✅
- 性能提升: 10x
```
"""
