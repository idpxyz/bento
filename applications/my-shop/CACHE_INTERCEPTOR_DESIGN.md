# 统一的缓存拦截器架构设计

## 🎯 设计原则

### DDD 框架应该：
1. ✅ **统一处理横切关注点** - 缓存是基础设施关注点
2. ✅ **保持应用层简洁** - 应用层只写业务逻辑
3. ✅ **架构一致性** - 所有拦截器使用相同模式
4. ✅ **可配置化** - 缓存策略通过配置管理

## 📐 架构设计

### 1. 扩展 OperationType

```python
# src/bento/persistence/interceptor/core/types.py

class OperationType(Enum):
    """扩展操作类型以支持聚合查询"""

    # 现有类型
    CREATE = auto()
    READ = auto()
    GET = auto()
    FIND = auto()
    QUERY = auto()
    UPDATE = auto()
    DELETE = auto()
    BATCH_CREATE = auto()
    BATCH_UPDATE = auto()
    BATCH_DELETE = auto()

    # ✅ 新增：聚合查询类型
    AGGREGATE = auto()       # sum, avg, min, max, count
    GROUP_BY = auto()        # group_by_field, group_by_date
    SORT_LIMIT = auto()      # find_first, find_last, find_top_n
    PAGINATE = auto()        # find_paginated
    RANDOM_SAMPLE = auto()   # find_random, find_sample

    # 新增：条件操作
    CONDITIONAL_UPDATE = auto()
    CONDITIONAL_DELETE = auto()
```

### 2. 增强 CacheInterceptor

```python
# src/bento/persistence/interceptor/impl/cache.py

class EnhancedCacheInterceptor(Interceptor[T]):
    """增强的缓存拦截器 - 支持所有查询类型"""

    # 缓存策略配置
    DEFAULT_TTL_CONFIG = {
        # 基础查询 - 短期缓存
        OperationType.GET: 300,           # 5分钟
        OperationType.FIND: 300,          # 5分钟
        OperationType.QUERY: 300,         # 5分钟

        # 聚合查询 - 中期缓存
        OperationType.AGGREGATE: 600,     # 10分钟

        # 分组统计 - 长期缓存
        OperationType.GROUP_BY: 3600,     # 1小时

        # 排序查询 - 短期缓存
        OperationType.SORT_LIMIT: 300,    # 5分钟

        # 分页 - 短期缓存
        OperationType.PAGINATE: 180,      # 3分钟

        # 随机采样 - 不缓存
        OperationType.RANDOM_SAMPLE: 0,   # 禁用缓存
    }

    def __init__(
        self,
        cache: Cache,
        *,
        ttl_config: dict[OperationType, int] | None = None,
        enabled: bool = True,
        prefix: str = "",
    ):
        self._cache = cache
        self._ttl_config = ttl_config or self.DEFAULT_TTL_CONFIG
        self._enabled = enabled
        self._prefix = prefix

    def _is_cacheable(self, op: OperationType) -> bool:
        """判断操作是否可缓存"""
        return op in (
            OperationType.GET,
            OperationType.FIND,
            OperationType.QUERY,
            OperationType.AGGREGATE,      # ✅
            OperationType.GROUP_BY,       # ✅
            OperationType.SORT_LIMIT,     # ✅
            OperationType.PAGINATE,       # ✅
        )

    def _get_cache_key(self, context: InterceptorContext[T]) -> str | None:
        """生成缓存键"""
        entity_type = context.entity_type.__name__
        op = context.operation

        # 聚合查询
        if op == OperationType.AGGREGATE:
            method = context.get_context_value("aggregate_method")  # sum/avg/min/max/count
            field = context.get_context_value("field")
            spec_hash = self._get_spec_hash(context)
            return f"{entity_type}:agg:{method}:{field}:{spec_hash}"

        # 分组统计
        if op == OperationType.GROUP_BY:
            fields = context.get_context_value("group_fields")
            period = context.get_context_value("period", "")  # day/week/month
            spec_hash = self._get_spec_hash(context)
            fields_str = ":".join(fields) if isinstance(fields, list) else fields
            return f"{entity_type}:group:{fields_str}:{period}:{spec_hash}"

        # 排序限制
        if op == OperationType.SORT_LIMIT:
            method = context.get_context_value("method")  # first/last/top_n
            order_by = context.get_context_value("order_by", "")
            limit = context.get_context_value("limit", "")
            spec_hash = self._get_spec_hash(context)
            return f"{entity_type}:sort:{method}:{order_by}:{limit}:{spec_hash}"

        # 分页
        if op == OperationType.PAGINATE:
            page = context.get_context_value("page")
            page_size = context.get_context_value("page_size")
            order_by = context.get_context_value("order_by", "")
            spec_hash = self._get_spec_hash(context)
            return f"{entity_type}:page:{page}:{page_size}:{order_by}:{spec_hash}"

        # 现有逻辑 (GET, FIND, QUERY)
        return self._get_basic_cache_key(context)

    def _get_spec_hash(self, context: InterceptorContext[T]) -> str:
        """获取 Specification 的哈希值"""
        spec = context.get_context_value("specification")
        if spec is None:
            return "none"
        # 使用 spec 的字符串表示生成哈希
        import hashlib
        spec_str = str(spec)
        return hashlib.md5(spec_str.encode()).hexdigest()[:8]

    def _get_ttl(self, operation: OperationType) -> int:
        """获取操作类型的 TTL"""
        return self._ttl_config.get(operation, 300)

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]],
    ) -> Any:
        """操作前检查缓存"""
        if not self._enabled or not self._is_cacheable(context.operation):
            return await next_interceptor(context)

        key = self._get_cache_key(context)
        if not key:
            return await next_interceptor(context)

        # 尝试从缓存获取
        cached = await self._cache.get(self._full_key(key))
        if cached is not None:
            # 记录缓存命中
            context.set_context_value("cache_hit", True)
            return cached

        # 缓存未命中，继续执行
        context.set_context_value("cache_hit", False)
        return await next_interceptor(context)

    async def process_result(
        self,
        context: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[InterceptorContext[T], Any], Awaitable[Any]],
    ) -> Any:
        """处理结果，写入缓存"""
        if not self._enabled:
            return await next_interceptor(context, result)

        # 如果是可缓存的操作且未命中缓存
        if self._is_cacheable(context.operation):
            if not context.get_context_value("cache_hit", False):
                key = self._get_cache_key(context)
                if key and result is not None:
                    ttl = self._get_ttl(context.operation)
                    await self._cache.set(self._full_key(key), result, ttl=ttl)

        # 如果是写操作，失效相关缓存
        if self._is_write(context.operation):
            await self._invalidate_related(context)

        return await next_interceptor(context, result)

    async def _invalidate_related(self, context: InterceptorContext[T]) -> None:
        """失效相关缓存"""
        entity_type = context.entity_type.__name__

        # 失效所有聚合查询缓存
        await self._cache.delete_pattern(f"{self._prefix}{entity_type}:agg:*")

        # 失效所有分组统计缓存
        await self._cache.delete_pattern(f"{self._prefix}{entity_type}:group:*")

        # 失效排序查询缓存
        await self._cache.delete_pattern(f"{self._prefix}{entity_type}:sort:*")

        # 失效分页缓存
        await self._cache.delete_pattern(f"{self._prefix}{entity_type}:page:*")

        # 失效基础查询缓存
        await self._cache.delete_pattern(f"{self._prefix}{entity_type}:query:*")
```

### 3. Repository Mixin 触发拦截器

```python
# src/bento/persistence/repository/sqlalchemy/mixins/aggregate_queries.py

class AggregateQueriesMixin:
    """聚合查询 Mixin - 通过拦截器链执行"""

    async def sum_field(
        self,
        field: str,
        spec: Specification | None = None
    ) -> float:
        """求和 - 自动缓存"""
        # 构建拦截器上下文
        context = InterceptorContext(
            session=self.session,
            entity_type=self._entity_type,
            operation=OperationType.AGGREGATE,  # ✅ 新类型
            context_data={
                "aggregate_method": "sum",
                "field": field,
                "specification": spec,
            }
        )

        # 定义实际执行函数
        async def execute():
            query = select(func.sum(getattr(self._po_class, field)))
            if spec:
                query = query.where(spec.to_sqlalchemy())
            result = await self.session.execute(query)
            return result.scalar() or 0.0

        # ✅ 通过拦截器链执行（缓存自动处理）
        return await self._execute_with_interceptors(context, execute)

    async def avg_field(self, field: str, spec=None) -> float:
        """平均值 - 自动缓存"""
        context = InterceptorContext(
            session=self.session,
            entity_type=self._entity_type,
            operation=OperationType.AGGREGATE,
            context_data={
                "aggregate_method": "avg",
                "field": field,
                "specification": spec,
            }
        )
        # ... 类似实现

    # count_field, min_field, max_field 类似...
```

### 4. 配置化管理

```python
# config/cache_config.py

from bento.persistence.interceptor import EnhancedCacheInterceptor
from bento.adapters.cache import RedisCache

# 缓存后端
cache = RedisCache(host="localhost", port=6379)

# 自定义 TTL 策略
CUSTOM_TTL_CONFIG = {
    OperationType.AGGREGATE: 900,      # 聚合查询缓存15分钟
    OperationType.GROUP_BY: 7200,      # 分组统计缓存2小时
    OperationType.SORT_LIMIT: 600,     # 排序查询缓存10分钟
    OperationType.PAGINATE: 300,       # 分页缓存5分钟
}

# 创建缓存拦截器
cache_interceptor = EnhancedCacheInterceptor(
    cache=cache,
    ttl_config=CUSTOM_TTL_CONFIG,
    enabled=True,
    prefix="myapp:"
)

# 注册到 Repository
repository_config = RepositoryConfig(
    interceptors=[
        audit_interceptor,
        cache_interceptor,       # ✅ 统一处理缓存
        soft_delete_interceptor,
        optimistic_lock_interceptor,
    ]
)
```

### 5. 应用层完全透明

```python
# ✅ 应用层代码非常简洁
class OrderAnalyticsService:
    """不需要关心缓存，框架自动处理"""

    def __init__(self, order_repo: OrderRepository):
        self._repo = order_repo

    # ✅ 无需装饰器，框架自动缓存
    async def get_total_revenue(self) -> float:
        return await self._repo.sum_field("total")

    # ✅ 无需装饰器，框架自动缓存
    async def get_revenue_stats(self) -> dict:
        return {
            "total": await self._repo.sum_field("total"),
            "avg": await self._repo.avg_field("total"),
            "min": await self._repo.min_field("total"),
            "max": await self._repo.max_field("total"),
        }

    # ✅ 无需装饰器，框架自动缓存
    async def get_category_distribution(self) -> dict[str, int]:
        return await self._repo.group_by_field("category_id")
```

## 🎯 优势总结

### 1. DDD 原则
- ✅ **关注点分离** - 应用层只关注业务逻辑
- ✅ **基础设施责任** - 缓存由 Infrastructure 层处理
- ✅ **领域纯粹性** - Domain/Application 层不知道缓存存在

### 2. 框架一致性
- ✅ 所有横切关注点统一处理（审计、缓存、软删除、锁）
- ✅ 配置化管理，易于调整
- ✅ 开发者体验一致

### 3. 可维护性
- ✅ 缓存策略集中管理
- ✅ 易于调试和监控
- ✅ 减少重复代码

### 4. 性能优化
- ✅ 所有查询自动获得缓存能力
- ✅ 智能缓存失效
- ✅ 可配置的 TTL 策略

## 📋 实施计划

### Phase 1: 核心扩展
1. 扩展 `OperationType` 枚举
2. 增强 `CacheInterceptor`
3. 添加缓存键生成逻辑

### Phase 2: Mixin 集成
1. 修改所有 Mixin 方法通过拦截器链执行
2. 添加必要的上下文信息
3. 确保 Specification 可序列化

### Phase 3: 测试和文档
1. 单元测试
2. 集成测试
3. 性能测试
4. 使用文档

### Phase 4: 配置和监控
1. 默认配置
2. 缓存统计
3. 监控面板

## 💡 使用示例

```python
# 开发者只需要：

# 1. 配置缓存拦截器
cache_interceptor = EnhancedCacheInterceptor(cache)

# 2. 正常使用 Repository
result = await repo.sum_field("price")  # ✅ 自动缓存
stats = await repo.group_by_field("category")  # ✅ 自动缓存

# 3. 写操作自动失效缓存
await repo.save(product)  # ✅ 相关缓存自动失效
```

---

**结论**：作为 DDD 框架，应该在拦截器层统一处理缓存，保持应用层简洁和架构一致性。
