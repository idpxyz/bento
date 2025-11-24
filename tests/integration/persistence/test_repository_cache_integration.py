"""Repository Mixins 缓存集成测试.

测试范围：
1. AggregateQueryMixin 的缓存
2. GroupByQueryMixin 的缓存
3. SortingLimitingMixin 的缓存
4. 缓存失效在实际仓库操作中的表现
"""

import pytest
import pytest_asyncio
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, sessionmaker

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory, SerializerType
from bento.persistence.interceptor import (
    CacheInterceptor,
    InterceptorChain,
    OperationType,
)
from bento.persistence.repository.sqlalchemy import BaseRepository

# ==================== 测试用的数据模型 ====================

Base = declarative_base()


class ProductPO(Base):
    """产品持久化对象"""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column()
    category: Mapped[str] = mapped_column(String)
    stock: Mapped[int] = mapped_column(default=0)


class ProductRepository(BaseRepository[ProductPO, str]):
    """产品仓库 - 继承所有 Mixins"""

    pass


# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def engine():
    """创建内存数据库引擎"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """创建数据库会话"""
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:  # type: ignore[misc]
        yield session


@pytest_asyncio.fixture
async def cache():
    """创建缓存实例"""
    return await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )


@pytest_asyncio.fixture
async def repository(session, cache):
    """创建带缓存的仓库"""
    cache_interceptor = CacheInterceptor(
        cache,
        ttl=60,
        enabled=True,
        ttl_config={
            OperationType.AGGREGATE: 300,
            OperationType.GROUP_BY: 600,
            OperationType.SORT_LIMIT: 300,
            OperationType.PAGINATE: 300,
        },
    )
    interceptor_chain = InterceptorChain([cache_interceptor])

    return ProductRepository(
        session=session,
        po_type=ProductPO,
        actor="test_user",
        interceptor_chain=interceptor_chain,
    )


@pytest_asyncio.fixture
async def sample_products(session):
    """创建示例数据"""
    products = [
        ProductPO(id="p1", name="iPhone 15", price=999.99, category="electronics", stock=50),
        ProductPO(id="p2", name="MacBook Pro", price=2499.99, category="electronics", stock=30),
        ProductPO(id="p3", name="T-Shirt", price=29.99, category="clothing", stock=100),
        ProductPO(id="p4", name="Jeans", price=79.99, category="clothing", stock=80),
        ProductPO(id="p5", name="Python Book", price=49.99, category="books", stock=200),
    ]

    for product in products:
        session.add(product)
    await session.commit()

    return products


# ==================== AggregateQueryMixin 缓存测试 ====================


@pytest.mark.asyncio
async def test_sum_field_cache_hit(repository, sample_products, cache):
    """测试 sum_field 缓存命中"""
    # 第一次查询 - 缓存未命中
    total1 = await repository.sum_field_po("price")
    assert total1 > 0

    # 第二次查询 - 应该从缓存读取
    total2 = await repository.sum_field_po("price")
    assert total2 == total1  # 结果相同

    # 验证两次查询结果一致（说明缓存生效）
    assert total1 == total2


@pytest.mark.asyncio
async def test_count_field_cache(repository, sample_products):
    """测试 count_field 缓存"""
    # 第一次计数
    count1 = await repository.count_field_po("id")
    assert count1 == 5

    # 第二次计数 - 应该从缓存读取
    count2 = await repository.count_field_po("id")
    assert count2 == 5
    assert count1 == count2


@pytest.mark.asyncio
async def test_avg_field_cache(repository, sample_products):
    """测试 avg_field 缓存"""
    # 第一次计算平均值
    avg1 = await repository.avg_field_po("price")
    assert avg1 > 0

    # 第二次计算 - 应该从缓存读取
    avg2 = await repository.avg_field_po("price")
    assert avg2 == avg1


@pytest.mark.asyncio
async def test_aggregate_cache_invalidation_on_create(repository, session, sample_products):
    """测试创建操作失效聚合查询缓存"""
    # 1. 预热缓存
    total1 = await repository.sum_field_po("price")
    count1 = await repository.count_field_po("id")

    # 2. 创建新产品
    new_product = ProductPO(
        id="p6", name="New Product", price=100.0, category="electronics", stock=10
    )
    await repository.create_po(new_product)
    await session.commit()

    # 3. 再次查询 - 缓存应该已失效，结果应该包含新产品
    total2 = await repository.sum_field_po("price")
    count2 = await repository.count_field_po("id")

    assert count2 == count1 + 1  # 数量增加
    assert total2 > total1  # 总价增加


# ==================== GroupByQueryMixin 缓存测试 ====================


@pytest.mark.asyncio
async def test_group_by_field_cache(repository, sample_products):
    """测试 group_by_field 缓存"""
    # 第一次分组查询
    groups1 = await repository.group_by_field_po("category")
    assert "electronics" in groups1
    assert "clothing" in groups1
    assert "books" in groups1

    # 第二次查询 - 应该从缓存读取
    groups2 = await repository.group_by_field_po("category")
    assert groups2 == groups1


@pytest.mark.asyncio
async def test_group_by_cache_invalidation(repository, session, sample_products):
    """测试分组查询缓存在数据变更后失效"""
    # 1. 预热缓存
    groups1 = await repository.group_by_field_po("category")
    electronics_count = groups1.get("electronics", 0)

    # 2. 添加新的电子产品
    new_product = ProductPO(id="p7", name="iPad", price=799.99, category="electronics", stock=20)
    await repository.create_po(new_product)
    await session.commit()

    # 3. 再次分组查询 - 缓存应该已失效
    groups2 = await repository.group_by_field_po("category")
    new_electronics_count = groups2.get("electronics", 0)

    assert new_electronics_count == electronics_count + 1  # 电子产品数量增加


# ==================== SortingLimitingMixin 缓存测试 ====================


@pytest.mark.asyncio
async def test_find_first_cache(repository, sample_products):
    """测试 find_first 缓存"""
    # 第一次查询最贵的产品
    first1 = await repository.find_first_po(order_by="-price")
    assert first1 is not None

    # 第二次查询 - 应该从缓存读取
    first2 = await repository.find_first_po(order_by="-price")
    assert first1.id == first2.id
    assert first1.price == first2.price


@pytest.mark.asyncio
async def test_find_top_n_cache(repository, sample_products):
    """测试 find_top_n 缓存"""
    # 第一次查询前3个最贵的产品
    top1 = await repository.find_top_n_po(3, order_by="-price")
    assert len(top1) == 3

    # 第二次查询 - 应该从缓存读取
    top2 = await repository.find_top_n_po(3, order_by="-price")
    assert len(top2) == 3
    assert top1[0].id == top2[0].id


@pytest.mark.asyncio
async def test_sort_limit_cache_invalidation(repository, session, sample_products):
    """测试排序查询缓存在数据变更后失效"""
    # 1. 预热缓存 - 查询最贵的产品
    first1 = await repository.find_first_po(order_by="-price")
    original_most_expensive_price = first1.price

    # 2. 添加更贵的产品
    new_product = ProductPO(
        id="p8", name="Super Expensive", price=9999.99, category="luxury", stock=1
    )
    await repository.create_po(new_product)
    await session.commit()

    # 3. 再次查询 - 缓存应该已失效
    first2 = await repository.find_first_po(order_by="-price")
    assert first2.price > original_most_expensive_price
    assert first2.id == "p8"


# ==================== 分页查询缓存测试 ====================


@pytest.mark.asyncio
async def test_find_paginated_cache(repository, sample_products):
    """测试分页查询缓存"""
    # 第一次查询第1页
    products1, total1 = await repository.find_paginated_po(page=1, page_size=2, order_by="name")
    assert len(products1) == 2
    assert total1 == 5

    # 第二次查询 - 应该从缓存读取
    products2, total2 = await repository.find_paginated_po(page=1, page_size=2, order_by="name")
    assert len(products2) == 2
    assert total2 == 5
    assert products1[0].id == products2[0].id


@pytest.mark.asyncio
async def test_different_pages_separate_cache(repository, sample_products):
    """测试不同页码使用不同缓存"""
    # 查询第1页
    page1, _ = await repository.find_paginated_po(page=1, page_size=2, order_by="name")

    # 查询第2页
    page2, _ = await repository.find_paginated_po(page=2, page_size=2, order_by="name")

    # 两页的数据应该不同
    assert page1[0].id != page2[0].id


@pytest.mark.asyncio
async def test_paginate_cache_invalidation(repository, session, sample_products):
    """测试分页缓存在数据变更后失效"""
    # 1. 预热缓存
    _, total1 = await repository.find_paginated_po(page=1, page_size=10, order_by="name")
    assert total1 == 5

    # 2. 添加新产品
    new_product = ProductPO(id="p9", name="Another Product", price=99.99, category="misc", stock=5)
    await repository.create_po(new_product)
    await session.commit()

    # 3. 再次查询 - 缓存应该已失效
    _, total2 = await repository.find_paginated_po(page=1, page_size=10, order_by="name")
    assert total2 == 6  # 总数增加


# ==================== 更新和删除操作的缓存失效测试 ====================


@pytest.mark.asyncio
async def test_cache_invalidation_on_update(repository, session, sample_products):
    """测试更新操作失效所有相关缓存"""
    # 1. 预热各种缓存
    total_before = await repository.sum_field_po("price")
    # groups_before = await repository.group_by_field_po("category")
    # first_before = await repository.find_first_po(order_by="-price")

    # 2. 更新产品价格
    product = sample_products[0]
    product.price = 9999.99
    await repository.update_po(product)
    await session.commit()

    # 3. 验证缓存已失效 - 查询结果应该反映更新
    total_after = await repository.sum_field_po("price")
    first_after = await repository.find_first_po(order_by="-price")

    assert total_after > total_before  # 总价增加
    assert first_after.id == product.id  # 更新后的产品成为最贵的


@pytest.mark.asyncio
async def test_cache_invalidation_on_delete(repository, session, sample_products):
    """测试删除操作失效所有相关缓存"""
    # 1. 预热缓存
    count_before = await repository.count_field_po("id")
    # groups_before = await repository.group_by_field_po("category")

    # 2. 删除产品
    product_to_delete = sample_products[0]
    await repository.delete_po(product_to_delete)
    await session.commit()

    # 3. 验证缓存已失效
    count_after = await repository.count_field_po("id")
    assert count_after == count_before - 1  # 数量减少


# ==================== 复杂场景测试 ====================


@pytest.mark.asyncio
async def test_multiple_operations_cache_consistency(repository, session, sample_products):
    """测试多次操作后缓存的一致性"""
    # 1. 初始状态
    total_initial = await repository.sum_field_po("price")
    count_initial = await repository.count_field_po("id")

    # 2. 执行多个操作
    # 创建
    new1 = ProductPO(id="p10", name="Product 10", price=100.0, category="test", stock=10)
    await repository.create_po(new1)
    await session.commit()

    # 更新
    sample_products[0].price += 100
    await repository.update_po(sample_products[0])
    await session.commit()

    # 创建
    new2 = ProductPO(id="p11", name="Product 11", price=200.0, category="test", stock=20)
    await repository.create_po(new2)
    await session.commit()

    # 删除
    await repository.delete_po(sample_products[1])
    await session.commit()

    # 3. 验证最终状态
    total_final = await repository.sum_field_po("price")
    count_final = await repository.count_field_po("id")

    # 数量：5 + 1 + 1 - 1 = 6
    assert count_final == count_initial + 1

    # 总价应该反映所有变更
    expected_total = (
        total_initial
        - sample_products[1].price  # 删除的产品
        + 100.0  # 新产品1
        + 100.0  # 更新增加的价格
        + 200.0  # 新产品2
    )
    # 由于浮点数精度，使用近似比较
    assert abs(total_final - expected_total) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
