"""应用启动时的缓存配置集成.

集成所有上下文的缓存关联配置，并注册到事件系统。
"""

from bento.application.ports.cache import Cache
from bento.persistence.interceptor.auto_cache_invalidation import (
    CacheInvalidationConfig,
    DomainEventCacheInvalidator,
)

# 导入各个上下文的配置
from contexts.ordering.config.cache_relations import configure_ordering_cache_relations


def create_unified_cache_config() -> CacheInvalidationConfig:
    """创建统一的缓存失效配置.

    集成所有 Bounded Context 的缓存关联关系。
    """
    # 创建基础配置
    config = CacheInvalidationConfig()

    # 集成 Ordering 上下文
    ordering_config = configure_ordering_cache_relations()
    for relations in ordering_config._relations.values():
        for relation in relations:
            config.add_relation(relation)

    # 未来可以继续添加其他上下文
    # catalog_config = configure_catalog_cache_relations()
    # for relations in catalog_config._relations.values():
    #     for relation in relations:
    #         config.add_relation(relation)

    return config


def setup_cache_invalidation(cache: Cache, event_bus) -> DomainEventCacheInvalidator:
    """设置自动缓存失效.

    在应用启动时调用此函数，注册缓存失效处理器到事件总线。

    Args:
        cache: 缓存实例（Redis/Memory）
        event_bus: 事件总线实例

    Returns:
        DomainEventCacheInvalidator 实例

    Example:
        ```python
        # 在 app.py 或 main.py 中
        async def startup():
            cache = RedisCache(host="localhost", port=6379)
            event_bus = create_event_bus()

            # 设置自动缓存失效
            invalidator = setup_cache_invalidation(cache, event_bus)

            # 注册到事件总线
            event_bus.subscribe_all(invalidator.on_domain_event)
        ```
    """
    # 创建统一配置
    config = create_unified_cache_config()

    # 创建失效处理器
    invalidator = DomainEventCacheInvalidator(cache, config)

    # 打印配置摘要（可选，用于调试）
    print("✅ 缓存失效配置已加载：")
    for entity_type, relations in config._relations.items():
        print(f"  - {entity_type}: {len(relations)} 个关联关系")

    return invalidator


# ==================== 完整使用示例 ====================

"""
完整的应用启动流程：

```python
# app.py - FastAPI 应用示例

from fastapi import FastAPI
from bento.adapters.cache import RedisCache
from bento.adapters.messaging.inprocess import InProcessMessageBus
from config.cache_setup import setup_cache_invalidation

app = FastAPI()

@app.on_event("startup")
async def startup():
    # 1. 创建缓存
    cache = RedisCache(
        host="localhost",
        port=6379,
        db=0
    )

    # 2. 创建事件总线
    event_bus = InProcessMessageBus()

    # 3. 设置自动缓存失效 ✅
    invalidator = setup_cache_invalidation(cache, event_bus)

    # 4. 注册到事件总线
    await event_bus.subscribe(invalidator.on_domain_event)

    print("✅ 应用启动完成")
    print("✅ 自动缓存失效已启用")


# ==================== 之后使用 ====================

class OrderService:
    async def create_order(self, order_data):
        # 创建订单
        order = Order(...)
        await self._order_repo.save(order)

        # ✅ 完全不需要关心缓存失效！
        # 框架已经自动处理了：
        # - Order 缓存失效（拦截器）
        # - Customer 缓存失效（配置的关联）
        # - Product 缓存失效（配置的关联）


class CustomerService:
    async def get_customer_orders(self, customer_id: str):
        # 第一次：查询数据库
        orders = await self._order_repo.group_by_field("status")

        # 第二次：从缓存读取
        orders = await self._order_repo.group_by_field("status")  # ⚡ 快

        # 当有新订单时：
        # await order_repo.save(new_order)
        # ✅ 缓存自动失效，下次查询会重新计算


class ProductService:
    async def get_product_sales(self, product_id: str):
        # 查询产品销量
        sales = await self._product_repo.sum_field("quantity")

        # ✅ 当订单创建/取消时，缓存自动失效
        # ✅ 不需要手动处理
```

测试验证：
```python
@pytest.mark.asyncio
async def test_order_creation_invalidates_customer_cache():
    # 1. 预热客户缓存
    customer_orders = await customer_service.get_orders("c123")
    assert cache_hit

    # 2. 创建订单
    order = Order(customer_id="c123", ...)
    await order_repo.save(order)

    # 3. 验证缓存已失效
    customer_orders = await customer_service.get_orders("c123")
    assert cache_miss  # ✅ 缓存已自动失效
```
"""
