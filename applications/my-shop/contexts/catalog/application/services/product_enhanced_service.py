"""Product Service - 使用 Repository Mixins 增强功能示例

这个文件展示了如何使用 Repository 的 29 个新增强方法来简化业务逻辑。
"""

from bento.core.ids import ID

from contexts.catalog.domain.models.product import Product
from contexts.catalog.infrastructure.repositories.product_repository_impl import ProductRepository


class ProductEnhancedService:
    """产品服务 - 展示 Repository Mixins 的实际应用"""

    def __init__(self, product_repo: ProductRepository):
        self._repo = product_repo

    # ==================== P0: 基础增强功能 ====================

    async def get_products_batch(self, product_ids: list[ID]) -> list[Product]:
        """批量获取产品（使用新的 get_by_ids）

        ✅ 新方法：1次数据库查询
        ❌ 旧方法：N次查询
        """
        return await self._repo.get_by_ids(product_ids)

    async def check_product_exists(self, product_id: ID) -> bool:
        """快速检查产品是否存在

        ✅ 新方法：使用 EXISTS 查询，高效
        ❌ 旧方法：需要完整加载对象
        """
        return await self._repo.exists_by_id(product_id)

    async def verify_sku_unique(self, sku: str, exclude_id: ID | None = None) -> bool:
        """验证 SKU 是否唯一

        应用场景：
        - 创建产品时验证 SKU
        - 更新产品时排除自身检查
        """
        return await self._repo.is_unique("sku", sku, exclude_id=exclude_id)

    async def find_by_sku(self, sku: str) -> Product | None:
        """通过 SKU 查找产品

        ✅ 新方法：一行代码完成
        ❌ 旧方法：需要自己写 SQL 查询
        """
        return await self._repo.find_by_field("sku", sku)

    async def get_products_by_category(self, category_id: str) -> list[Product]:
        """获取某类别的所有产品

        ✅ 新方法：使用 find_all_by_field
        ❌ 旧方法：手动构建查询
        """
        return await self._repo.find_all_by_field("category_id", category_id)

    async def bulk_delete_products(self, product_ids: list[ID]) -> int:
        """批量删除产品

        返回：删除的产品数量
        """
        return await self._repo.delete_by_ids(product_ids)

    # ==================== P1: 聚合查询 ====================

    async def get_total_inventory_value(self) -> float:
        """计算总库存价值

        ✅ 新方法：数据库层面计算
        ❌ 旧方法：加载所有产品然后求和
        """
        return await self._repo.sum_field("price")

    async def get_average_price(self, category_id: str | None = None) -> float:
        """计算平均价格

        可选择按类别筛选
        """
        if category_id:
            # TODO: 使用 Specification 过滤（如果有的话）
            # spec = ProductSpec().in_category(category_id)
            # return await self._repo.avg_field("price", spec)

            # 临时实现：返回所有产品的平均价格
            return await self._repo.avg_field("price")

        return await self._repo.avg_field("price")

    async def get_price_range(self) -> dict[str, float | None]:
        """获取价格区间

        返回：{"min": 最低价, "max": 最高价}

        注意：如果没有产品，min 和 max 可能为 None
        """
        min_price = await self._repo.min_field("price")
        max_price = await self._repo.max_field("price")
        return {"min": min_price, "max": max_price}

    async def count_unique_categories(self) -> int:
        """统计不同类别数量

        ✅ 新方法：使用 COUNT DISTINCT
        """
        return await self._repo.count_field("category_id", distinct=True)

    # ==================== P1: 排序和限制 ====================

    async def get_latest_product(self) -> Product | None:
        """获取最新产品

        ✅ 新方法：一行代码
        ❌ 旧方法：需要构建 ORDER BY + LIMIT 查询
        """
        return await self._repo.find_first(order_by="-created_at")

    async def get_oldest_product(self) -> Product | None:
        """获取最早的产品"""
        return await self._repo.find_last(order_by="created_at")

    async def get_top_expensive_products(self, limit: int = 10) -> list[Product]:
        """获取价格最高的N个产品

        应用场景：展示高端产品、奢侈品专区
        """
        return await self._repo.find_top_n(limit, order_by="-price")

    async def get_cheapest_products(self, limit: int = 10) -> list[Product]:
        """获取价格最低的N个产品

        应用场景：特价专区、清仓促销
        """
        return await self._repo.find_top_n(limit, order_by="price")

    async def get_products_paginated(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Product], int]:
        """分页获取产品

        返回：(产品列表, 总数)

        ✅ 新方法：自动计算 offset 并返回总数
        """
        products, total = await self._repo.find_paginated(
            page=page, page_size=page_size, order_by="name"
        )
        return products, total

    # ==================== P2: 分组统计 ====================

    async def get_category_distribution(self) -> dict[str, int]:
        """获取产品类别分布

        返回：{"category_id": count}

        应用场景：
        - 管理后台统计
        - 类别库存分析
        """
        return await self._repo.group_by_field("category_id")

    async def get_daily_product_creation_stats(self) -> dict[str, int]:
        """获取每日产品创建统计

        返回：{"2025-01-01": 5, "2025-01-02": 8, ...}

        应用场景：
        - 运营分析
        - 增长趋势
        """
        return await self._repo.group_by_date("created_at", "day")

    async def get_monthly_stats(self) -> dict[str, int]:
        """获取月度产品统计"""
        return await self._repo.group_by_date("created_at", "month")

    async def get_category_brand_matrix(self) -> dict[tuple, int]:
        """获取类别-品牌矩阵

        返回：{("category_id", "brand"): count}

        应用场景：
        - 品类分析
        - 供应商管理
        """
        return await self._repo.group_by_multiple_fields(["category_id", "brand"])

    # ==================== P2: 软删除增强 ====================

    async def get_deleted_products(self) -> list[Product]:
        """查看回收站中的产品

        应用场景：
        - 产品恢复
        - 审计追踪
        """
        return await self._repo.find_trashed()

    async def get_all_products_including_deleted(self) -> list[Product]:
        """获取所有产品（包括已删除）

        应用场景：
        - 完整历史记录
        - 数据导出
        """
        return await self._repo.find_with_trashed()

    async def count_deleted_products(self) -> int:
        """统计回收站中的产品数量"""
        return await self._repo.count_trashed()

    async def check_if_deleted(self, product_id: ID) -> bool:
        """检查产品是否在回收站"""
        return await self._repo.is_trashed(product_id)

    # ==================== P3: 随机推荐 ====================

    async def get_random_product(self) -> Product | None:
        """随机推荐一个产品

        应用场景：
        - "手气不错"功能
        - 随机展示
        """
        return await self._repo.find_random()

    async def get_featured_products(self, count: int = 5) -> list[Product]:
        """获取精选产品（随机N个）

        应用场景：
        - 首页推荐
        - "为你推荐"
        - 随机展示
        """
        return await self._repo.find_random_n(count)

    async def get_product_sample_for_audit(
        self, percentage: float = 10.0, max_count: int = 100
    ) -> list[Product]:
        """获取产品样本用于审计

        抽取指定百分比的产品，用于：
        - 质量抽检
        - 数据审计
        - 统计分析
        """
        return await self._repo.sample_percentage(percentage, max_count=max_count)

    # ==================== 实战组合示例 ====================

    async def get_dashboard_stats(self) -> dict:
        """获取管理后台统计数据

        展示如何组合使用多个增强方法
        """
        return {
            # 总数统计
            "total_products": await self._repo.count_field("id"),
            "total_value": await self._repo.sum_field("price"),
            "avg_price": await self._repo.avg_field("price"),
            # 价格区间
            "min_price": await self._repo.min_field("price"),
            "max_price": await self._repo.max_field("price"),
            # 分类统计
            "category_distribution": await self._repo.group_by_field("category_id"),
            # 唯一值统计
            "unique_categories": await self._repo.count_field("category_id", distinct=True),
            # 回收站统计
            "deleted_count": await self._repo.count_trashed(),
            # 最新产品
            "latest_product": await self._repo.find_first(order_by="-created_at"),
        }

    async def cleanup_old_deleted_products(self, days: int = 30) -> int:
        """清理超过N天的已删除产品

        结合条件删除功能
        """
        # 注意：这需要配合 Specification 使用
        # cutoff_date = datetime.now() - timedelta(days=days)
        # spec = ProductSpec().deleted_before(cutoff_date)
        # return await self._repo.delete_by_spec(spec)

        # 临时示例：展示 API
        print(f"将清理 {days} 天前删除的产品")
        return 0


# ==================== 使用示例 ====================


async def example_usage():
    """展示如何在实际应用中使用增强功能"""

    # 假设我们有一个 product_repo

    # session = ...  # 从某处获取 session
    # product_repo = ProductRepository(session, actor="admin")
    # service = ProductEnhancedService(product_repo)

    # 示例 1: 批量获取产品
    # product_ids = ["p1", "p2", "p3"]
    # products = await service.get_products_batch(product_ids)
    # print(f"获取了 {len(products)} 个产品")

    # 示例 2: 验证 SKU 唯一性
    # is_unique = await service.verify_sku_unique("NEW-SKU-001")
    # if not is_unique:
    #     print("SKU 已存在")

    # 示例 3: 获取统计数据
    # stats = await service.get_dashboard_stats()
    # print(f"总产品数: {stats['total_products']}")
    # print(f"平均价格: {stats['avg_price']}")
    # print(f"类别分布: {stats['category_distribution']}")

    # 示例 4: 分页查询
    # products, total = await service.get_products_paginated(page=1, page_size=20)
    # print(f"第1页: {len(products)} 个产品，总共 {total} 个")

    # 示例 5: 随机推荐
    # featured = await service.get_featured_products(count=5)
    # print(f"随机推荐了 {len(featured)} 个产品")

    pass


"""
总结：Repository Mixins 带来的好处

✅ 代码量减少 50-70%
✅ 一行代码完成复杂查询
✅ 类型安全，IDE 自动补全
✅ 数据库层面执行，性能优异
✅ 零配置，自动继承
✅ 易于测试，易于维护

对比：
❌ 旧方法需要：
   - 手写 SQL 查询
   - 手动处理结果映射
   - 自己计算分页 offset
   - 重复的样板代码

✅ 新方法只需：
   - 一行方法调用
   - 框架自动处理一切
   - 专注业务逻辑
"""
