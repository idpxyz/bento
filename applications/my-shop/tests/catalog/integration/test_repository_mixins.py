"""Integration tests for Repository Mixins functionality in my-shop

测试 Repository Mixins 在实际应用中的功能
"""

import pytest
from bento.core.ids import ID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from contexts.catalog.domain.product import Product
from contexts.catalog.infrastructure.models.product_po import ProductPO
from contexts.catalog.infrastructure.repositories.product_repository_impl import ProductRepository


@pytest.fixture
async def setup_test_db():
    """设置测试数据库"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(ProductPO.metadata.create_all)

    yield engine, async_session_maker

    await engine.dispose()


@pytest.fixture
async def product_repo(setup_test_db):
    """创建产品仓储"""
    _, async_session_maker = setup_test_db

    async with async_session_maker() as session:
        repo = ProductRepository(session, actor="test-user")

        # 创建测试数据（使用增强的 Product 模型）
        test_products = []
        for i in range(1, 11):
            product = Product(
                id=ID(f"test-p{i}"),
                name=f"测试产品 {i}",
                description=f"这是测试产品 {i} 的描述",
                price=float(100 + i * 50),
                sku=f"SKU-{i:03d}",
                brand=f"Brand-{(i - 1) % 2 + 1}",  # 2个品牌
                stock=100 + i * 10,
                is_active=i % 5 != 0,  # 每5个有1个不活跃
                sales_count=i * 100,  # 销量
                category_id=ID(f"cat-{(i - 1) % 3 + 1}"),  # 3个类别
            )
            test_products.append(product)
            await repo.save(product)

        yield repo


class TestP0BasicEnhancements:
    """P0: 基础增强功能测试"""

    @pytest.mark.asyncio
    async def test_get_by_ids(self, product_repo):
        """测试批量获取"""
        product_ids = [ID("test-p1"), ID("test-p2"), ID("test-p3")]
        products = await product_repo.get_by_ids(product_ids)

        assert len(products) == 3
        assert all(isinstance(p, Product) for p in products)
        # ID 可能是 ID 对象或字符串
        product_id_values = {str(p.id) if hasattr(p.id, "value") else p.id for p in products}
        assert product_id_values == {"test-p1", "test-p2", "test-p3"}

    @pytest.mark.asyncio
    async def test_exists_by_id(self, product_repo):
        """测试ID存在性检查"""
        # 存在的ID
        exists = await product_repo.exists_by_id(ID("test-p1"))
        assert exists is True

        # 不存在的ID
        exists = await product_repo.exists_by_id(ID("non-existent"))
        assert exists is False

    @pytest.mark.asyncio
    async def test_find_by_field(self, product_repo):
        """测试通过字段查找"""
        product = await product_repo.find_by_field("name", "测试产品 5")

        assert product is not None
        assert product.name == "测试产品 5"
        product_id = str(product.id) if hasattr(product.id, "value") else product.id
        assert product_id == "test-p5"

    @pytest.mark.asyncio
    async def test_find_all_by_field(self, product_repo):
        """测试批量字段查找"""
        products = await product_repo.find_all_by_field("category_id", "cat-1")

        # cat-1 应该有产品 1, 4, 7, 10 (每3个一个周期)
        assert len(products) >= 3
        assert all(p.category_id.value == "cat-1" for p in products)

    @pytest.mark.asyncio
    async def test_is_unique_sku(self, product_repo):
        """测试 SKU 唯一性验证"""
        # 已存在的 SKU
        is_unique = await product_repo.is_unique("sku", "SKU-001")
        assert is_unique is False

        # 不存在的 SKU
        is_unique = await product_repo.is_unique("sku", "SKU-999")
        assert is_unique is True

    @pytest.mark.asyncio
    async def test_find_by_sku(self, product_repo):
        """测试通过 SKU 查找产品"""
        product = await product_repo.find_by_field("sku", "SKU-005")

        assert product is not None
        assert product.sku == "SKU-005"
        assert product.name == "测试产品 5"


class TestP1AggregateQueries:
    """P1: 聚合查询测试"""

    @pytest.mark.asyncio
    async def test_sum_field(self, product_repo):
        """测试求和"""
        total_price = await product_repo.sum_field("price")

        # 产品价格: 150, 200, 250, ..., 600
        # 总和 = 150 + 200 + ... + 600
        expected = sum(100 + i * 50 for i in range(1, 11))
        assert abs(total_price - expected) < 0.01

    @pytest.mark.asyncio
    async def test_avg_field(self, product_repo):
        """测试平均值"""
        avg_price = await product_repo.avg_field("price")

        expected_avg = sum(100 + i * 50 for i in range(1, 11)) / 10
        assert abs(avg_price - expected_avg) < 0.01

    @pytest.mark.asyncio
    async def test_min_field(self, product_repo):
        """测试最小值"""
        min_price = await product_repo.min_field("price")
        assert min_price == 150.0  # 第一个产品

    @pytest.mark.asyncio
    async def test_max_field(self, product_repo):
        """测试最大值"""
        max_price = await product_repo.max_field("price")
        assert max_price == 600.0  # 最后一个产品

    @pytest.mark.asyncio
    async def test_count_field(self, product_repo):
        """测试计数"""
        count = await product_repo.count_field("id")
        assert count == 10

    @pytest.mark.asyncio
    async def test_count_field_distinct(self, product_repo):
        """测试唯一值计数"""
        unique_categories = await product_repo.count_field("category_id", distinct=True)
        assert unique_categories == 3  # 3个不同的类别


class TestP1SortingLimiting:
    """P1: 排序和限制测试"""

    @pytest.mark.asyncio
    async def test_find_first(self, product_repo):
        """测试查找第一个"""
        first = await product_repo.find_first(order_by="price")

        assert first is not None
        assert first.price == 150.0  # 最低价格

    @pytest.mark.asyncio
    async def test_find_last(self, product_repo):
        """测试查找最后一个"""
        last = await product_repo.find_last(order_by="price")

        assert last is not None
        assert last.price == 600.0  # 最高价格

    @pytest.mark.asyncio
    async def test_find_top_n(self, product_repo):
        """测试前N个"""
        top_3 = await product_repo.find_top_n(3, order_by="price")

        assert len(top_3) == 3
        prices = [p.price for p in top_3]
        assert prices == [150.0, 200.0, 250.0]

    @pytest.mark.asyncio
    async def test_find_top_n_descending(self, product_repo):
        """测试前N个（降序）"""
        top_3 = await product_repo.find_top_n(3, order_by="-price")

        assert len(top_3) == 3
        prices = [p.price for p in top_3]
        assert prices == [600.0, 550.0, 500.0]

    @pytest.mark.asyncio
    async def test_find_paginated(self, product_repo):
        """测试分页"""
        products, total = await product_repo.find_paginated(page=1, page_size=3, order_by="price")

        assert len(products) == 3
        assert total == 10
        assert products[0].price == 150.0

    @pytest.mark.asyncio
    async def test_find_paginated_second_page(self, product_repo):
        """测试第二页"""
        products, total = await product_repo.find_paginated(page=2, page_size=3, order_by="price")

        assert len(products) == 3
        assert total == 10
        assert products[0].price == 300.0


class TestP2GroupByQueries:
    """P2: 分组查询测试"""

    @pytest.mark.asyncio
    async def test_group_by_field(self, product_repo):
        """测试按字段分组"""
        category_dist = await product_repo.group_by_field("category_id")

        # 应该有3个类别
        assert len(category_dist) == 3
        assert "cat-1" in category_dist
        assert "cat-2" in category_dist
        assert "cat-3" in category_dist

        # 每个类别应该有几个产品
        total = sum(category_dist.values())
        assert total == 10

    @pytest.mark.asyncio
    async def test_group_by_brand(self, product_repo):
        """测试按品牌分组"""
        brand_dist = await product_repo.group_by_field("brand")

        # 应该有2个品牌
        assert len(brand_dist) == 2
        assert "Brand-1" in brand_dist
        assert "Brand-2" in brand_dist

        # 验证总数
        total = sum(brand_dist.values())
        assert total == 10

    @pytest.mark.asyncio
    async def test_group_by_multiple_fields(self, product_repo):
        """测试多字段分组（类别 + 品牌）"""
        matrix = await product_repo.group_by_multiple_fields(["category_id", "brand"])

        # 应该有多个组合
        assert len(matrix) > 0

        # 验证数据结构
        for key in matrix.keys():
            assert isinstance(key, tuple)
            assert len(key) == 2  # (category_id, brand)

        # 验证总数
        total = sum(matrix.values())
        assert total == 10


class TestP3RandomSampling:
    """P3: 随机采样测试"""

    @pytest.mark.asyncio
    async def test_find_random(self, product_repo):
        """测试随机获取一个"""
        random_product = await product_repo.find_random()

        assert random_product is not None
        assert isinstance(random_product, Product)

    @pytest.mark.asyncio
    async def test_find_random_n(self, product_repo):
        """测试随机获取N个"""
        random_products = await product_repo.find_random_n(5)

        assert len(random_products) == 5
        assert all(isinstance(p, Product) for p in random_products)

        # 确保是不同的产品
        ids = {str(p.id) if hasattr(p.id, "value") else p.id for p in random_products}
        assert len(ids) == 5

    @pytest.mark.asyncio
    async def test_sample_percentage(self, product_repo):
        """测试百分比采样"""
        # 采样50% = 5个产品
        sample = await product_repo.sample_percentage(50.0)

        assert len(sample) == 5
        assert all(isinstance(p, Product) for p in sample)


class TestCombinedScenarios:
    """综合场景测试"""

    @pytest.mark.asyncio
    async def test_dashboard_stats(self, product_repo):
        """测试获取统计面板数据"""
        # 模拟获取管理后台统计数据
        stats = {
            "total_products": await product_repo.count_field("id"),
            "total_value": await product_repo.sum_field("price"),
            "avg_price": await product_repo.avg_field("price"),
            "min_price": await product_repo.min_field("price"),
            "max_price": await product_repo.max_field("price"),
            "unique_categories": await product_repo.count_field("category_id", distinct=True),
            "category_distribution": await product_repo.group_by_field("category_id"),
        }

        assert stats["total_products"] == 10
        assert stats["total_value"] > 0
        assert stats["avg_price"] > 0
        assert stats["min_price"] == 150.0
        assert stats["max_price"] == 600.0
        assert stats["unique_categories"] == 3
        assert len(stats["category_distribution"]) == 3

    @pytest.mark.asyncio
    async def test_product_recommendations(self, product_repo):
        """测试产品推荐场景"""
        # 获取推荐产品
        featured = await product_repo.find_random_n(3)

        # 获取最新产品
        latest = await product_repo.find_top_n(3, order_by="-created_at")

        # 获取价格最高的产品
        premium = await product_repo.find_top_n(3, order_by="-price")

        assert len(featured) == 3
        assert len(latest) == 3
        assert len(premium) == 3

        # 验证价格排序
        assert premium[0].price >= premium[1].price >= premium[2].price

    @pytest.mark.asyncio
    async def test_batch_operations(self, product_repo):
        """测试批量操作场景"""
        # 模拟购物车：批量获取产品
        cart_product_ids = [ID(f"test-p{i}") for i in [1, 3, 5, 7, 9]]
        cart_products = await product_repo.get_by_ids(cart_product_ids)

        assert len(cart_products) == 5

        # 验证所有产品都存在
        for product_id in cart_product_ids:
            exists = await product_repo.exists_by_id(product_id)
            assert exists is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
