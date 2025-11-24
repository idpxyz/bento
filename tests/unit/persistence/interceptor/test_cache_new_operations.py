"""测试新增操作类型的缓存支持.

测试范围：
1. AGGREGATE 操作类型的缓存
2. GROUP_BY 操作类型的缓存
3. SORT_LIMIT 操作类型的缓存
4. PAGINATE 操作类型的缓存
5. 缓存失效机制
"""

from unittest.mock import Mock

import pytest

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory, SerializerType
from bento.persistence.interceptor import (
    CacheInterceptor,
    InterceptorChain,
    InterceptorContext,
    OperationType,
)


class ProductPO:
    """测试用的 PO 类"""

    def __init__(self, id: str, name: str, price: float, category: str):
        self.id = id
        self.name = name
        self.price = price
        self.category = category


# ==================== AGGREGATE 操作测试 ====================


@pytest.mark.asyncio
async def test_aggregate_sum_cache_miss_then_hit():
    """测试聚合查询的缓存：首次未命中，后续命中"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    interceptor = CacheInterceptor(cache, ttl=60, enabled=True)
    chain = InterceptorChain([interceptor])

    # 第一次查询 - 缓存未命中
    ctx = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.AGGREGATE,
        actor="tester",
        context_data={
            "aggregate_method": "sum",
            "field": "price",
            "specification": None,
        },
    )

    result = await chain.execute_before(ctx)
    assert result is None  # 缓存未命中

    # 模拟查询结果
    query_result = 9999.99
    await chain.process_result(ctx, query_result)

    # 第二次查询 - 缓存命中
    ctx2 = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.AGGREGATE,
        actor="tester",
        context_data={
            "aggregate_method": "sum",
            "field": "price",
            "specification": None,
        },
    )

    cached_result = await chain.execute_before(ctx2)
    assert cached_result == 9999.99  # ✅ 缓存命中


@pytest.mark.asyncio
async def test_aggregate_with_different_fields_separate_cache():
    """测试不同字段的聚合查询使用不同的缓存键"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    # 聚合 price 字段
    ctx_price = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.AGGREGATE,
        actor="tester",
        context_data={
            "aggregate_method": "sum",
            "field": "price",
            "specification": None,
        },
    )
    await chain.process_result(ctx_price, 9999.99)

    # 聚合 stock 字段
    ctx_stock = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.AGGREGATE,
        actor="tester",
        context_data={
            "aggregate_method": "sum",
            "field": "stock",
            "specification": None,
        },
    )
    await chain.process_result(ctx_stock, 500)

    # 验证两个缓存独立
    price_cached = await chain.execute_before(ctx_price)
    stock_cached = await chain.execute_before(ctx_stock)

    assert price_cached == 9999.99
    assert stock_cached == 500


@pytest.mark.asyncio
async def test_aggregate_count_cache():
    """测试 count 聚合的缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.AGGREGATE,
        actor="tester",
        context_data={
            "aggregate_method": "count",
            "field": "id",
            "specification": None,
        },
    )

    # 设置缓存
    await chain.process_result(ctx, 100)

    # 验证缓存
    cached = await chain.execute_before(ctx)
    assert cached == 100


# ==================== GROUP_BY 操作测试 ====================


@pytest.mark.asyncio
async def test_group_by_field_cache():
    """测试分组查询的缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.GROUP_BY,
        actor="tester",
        context_data={
            "group_method": "field",
            "field": "category",
            "specification": None,
        },
    )

    # 模拟分组结果
    group_result = {
        "electronics": 50,
        "clothing": 30,
        "books": 20,
    }

    # 首次查询
    result = await chain.execute_before(ctx)
    assert result is None  # 缓存未命中

    # 设置缓存
    await chain.process_result(ctx, group_result)

    # 再次查询
    cached = await chain.execute_before(ctx)
    assert cached == group_result  # ✅ 缓存命中


@pytest.mark.asyncio
async def test_group_by_date_cache():
    """测试按日期分组的缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.GROUP_BY,
        actor="tester",
        context_data={
            "group_method": "date",
            "date_field": "created_at",
            "granularity": "month",
            "specification": None,
        },
    )

    date_result = {
        "2024-01": 100,
        "2024-02": 150,
        "2024-03": 200,
    }

    await chain.process_result(ctx, date_result)
    cached = await chain.execute_before(ctx)
    assert cached == date_result


# ==================== SORT_LIMIT 操作测试 ====================


@pytest.mark.asyncio
async def test_sort_limit_first_cache():
    """测试 find_first 的缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.SORT_LIMIT,
        actor="tester",
        context_data={
            "method": "first",
            "order_by": "-price",
            "limit": 1,
            "specification": None,
        },
    )

    # 模拟最贵的产品
    first_product = ProductPO("p1", "iPhone", 999.99, "electronics")

    await chain.process_result(ctx, first_product)
    cached = await chain.execute_before(ctx)

    assert cached.id == "p1"
    assert cached.price == 999.99


@pytest.mark.asyncio
async def test_sort_limit_top_n_cache():
    """测试 find_top_n 的缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.SORT_LIMIT,
        actor="tester",
        context_data={
            "method": "top_n",
            "order_by": "-price",
            "limit": 10,
            "specification": None,
        },
    )

    # 模拟前10个产品
    top_products = [
        ProductPO(f"p{i}", f"Product {i}", 1000 - i * 10, "electronics") for i in range(10)
    ]

    await chain.process_result(ctx, top_products)
    cached = await chain.execute_before(ctx)

    assert len(cached) == 10
    assert cached[0].price == 1000


@pytest.mark.asyncio
async def test_sort_limit_different_order_separate_cache():
    """测试不同排序方式使用不同缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    # 按价格降序
    ctx_price_desc = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.SORT_LIMIT,
        actor="tester",
        context_data={
            "method": "first",
            "order_by": "-price",
            "limit": 1,
            "specification": None,
        },
    )

    # 按名称升序
    ctx_name_asc = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.SORT_LIMIT,
        actor="tester",
        context_data={
            "method": "first",
            "order_by": "name",
            "limit": 1,
            "specification": None,
        },
    )

    product1 = ProductPO("p1", "Z Product", 999.99, "electronics")
    product2 = ProductPO("p2", "A Product", 99.99, "books")

    await chain.process_result(ctx_price_desc, product1)
    await chain.process_result(ctx_name_asc, product2)

    cached1 = await chain.execute_before(ctx_price_desc)
    cached2 = await chain.execute_before(ctx_name_asc)

    assert cached1.id == "p1"
    assert cached2.id == "p2"


# ==================== PAGINATE 操作测试 ====================


@pytest.mark.asyncio
async def test_paginate_cache():
    """测试分页查询的缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.PAGINATE,
        actor="tester",
        context_data={
            "page": 1,
            "page_size": 20,
            "order_by": "-created_at",
            "specification": None,
        },
    )

    # 模拟分页结果
    products = [ProductPO(f"p{i}", f"Product {i}", 10.0 * i, "electronics") for i in range(20)]
    total = 100
    paginate_result = (products, total)

    await chain.process_result(ctx, paginate_result)
    cached = await chain.execute_before(ctx)

    assert len(cached[0]) == 20
    assert cached[1] == 100


@pytest.mark.asyncio
async def test_paginate_different_pages_separate_cache():
    """测试不同页码使用不同缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    # 第1页
    ctx_page1 = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.PAGINATE,
        actor="tester",
        context_data={
            "page": 1,
            "page_size": 20,
            "order_by": "name",
            "specification": None,
        },
    )

    # 第2页
    ctx_page2 = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.PAGINATE,
        actor="tester",
        context_data={
            "page": 2,
            "page_size": 20,
            "order_by": "name",
            "specification": None,
        },
    )

    page1_products = [ProductPO(f"p{i}", f"Product {i}", 10.0, "electronics") for i in range(20)]
    page2_products = [
        ProductPO(f"p{i}", f"Product {i}", 10.0, "electronics") for i in range(20, 40)
    ]

    await chain.process_result(ctx_page1, (page1_products, 100))
    await chain.process_result(ctx_page2, (page2_products, 100))

    cached1 = await chain.execute_before(ctx_page1)
    cached2 = await chain.execute_before(ctx_page2)

    assert cached1[0][0].id == "p0"
    assert cached2[0][0].id == "p20"


# ==================== 缓存失效测试 ====================


@pytest.mark.asyncio
async def test_cache_invalidation_on_create():
    """测试创建操作失效缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    # 1. 先缓存一个聚合查询
    ctx_agg = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.AGGREGATE,
        actor="tester",
        context_data={
            "aggregate_method": "count",
            "field": "id",
            "specification": None,
        },
    )
    await chain.process_result(ctx_agg, 100)

    # 验证缓存存在
    cached = await chain.execute_before(ctx_agg)
    assert cached == 100

    # 2. 执行创建操作（应该失效缓存）
    ctx_create = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.CREATE,
        actor="tester",
        entity=ProductPO("p1", "New Product", 100.0, "electronics"),
    )

    # 模拟创建操作的 process_result
    await chain.process_result(ctx_create, ProductPO("p1", "New Product", 100.0, "electronics"))

    # 3. 验证缓存已失效
    cached_after = await chain.execute_before(ctx_agg)
    assert cached_after is None  # ✅ 缓存已失效


@pytest.mark.asyncio
async def test_cache_invalidation_on_update():
    """测试更新操作失效缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    # 1. 缓存分组查询
    ctx_group = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.GROUP_BY,
        actor="tester",
        context_data={
            "group_method": "field",
            "field": "category",
            "specification": None,
        },
    )
    await chain.process_result(ctx_group, {"electronics": 50})

    # 2. 执行更新操作
    ctx_update = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.UPDATE,
        actor="tester",
        entity=ProductPO("p1", "Updated Product", 200.0, "clothing"),
    )
    await chain.process_result(ctx_update, ProductPO("p1", "Updated Product", 200.0, "clothing"))

    # 3. 验证缓存已失效
    cached = await chain.execute_before(ctx_group)
    assert cached is None


@pytest.mark.asyncio
async def test_cache_invalidation_on_delete():
    """测试删除操作失效缓存"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    # 1. 缓存排序查询
    ctx_sort = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.SORT_LIMIT,
        actor="tester",
        context_data={
            "method": "top_n",
            "order_by": "-price",
            "limit": 10,
            "specification": None,
        },
    )
    top_products = [
        ProductPO(f"p{i}", f"Product {i}", 1000 - i * 10, "electronics") for i in range(10)
    ]
    await chain.process_result(ctx_sort, top_products)

    # 2. 执行删除操作
    ctx_delete = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.DELETE,
        actor="tester",
        entity=ProductPO("p1", "Product 1", 1000, "electronics"),
    )
    await chain.process_result(ctx_delete, None)

    # 3. 验证缓存已失效
    cached = await chain.execute_before(ctx_sort)
    assert cached is None


# ==================== TTL 配置测试 ====================


@pytest.mark.asyncio
async def test_custom_ttl_per_operation():
    """测试不同操作类型使用不同的 TTL"""
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )

    # 配置不同操作类型的 TTL
    ttl_config = {
        OperationType.AGGREGATE: 600,  # 聚合查询缓存10分钟
        OperationType.GROUP_BY: 3600,  # 分组查询缓存1小时
        OperationType.SORT_LIMIT: 300,  # 排序查询缓存5分钟
        OperationType.PAGINATE: 300,  # 分页查询缓存5分钟
    }

    interceptor = CacheInterceptor(cache, ttl=60, enabled=True, ttl_config=ttl_config)
    chain = InterceptorChain([interceptor])

    # 测试聚合查询使用自定义 TTL
    ctx_agg = InterceptorContext(
        session=Mock(),
        entity_type=ProductPO,
        operation=OperationType.AGGREGATE,
        actor="tester",
        context_data={
            "aggregate_method": "sum",
            "field": "price",
            "specification": None,
        },
    )

    await chain.process_result(ctx_agg, 9999.99)

    # 验证缓存存在（通过重新查询）
    cached = await chain.execute_before(ctx_agg)
    assert cached == 9999.99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
