"""跨实体缓存失效配置.

在这里定义所有实体的关联关系，框架会自动处理跨实体缓存失效。

开发者只需要：
1. 定义哪些实体会影响其他实体
2. 指定需要失效的缓存模式（可选，有智能默认值）
3. 框架自动监听事件并失效缓存 ✅
"""

from bento.persistence.interceptor.auto_cache_invalidation import (
    CacheInvalidationConfig,
    EntityRelation,
    create_relation_builder,
    create_simple_relation,
)


def configure_cache_relations() -> CacheInvalidationConfig:
    """配置跨实体缓存关联关系.

    框架会自动：
    - 监听所有领域事件
    - 识别实体变更（OrderCreated, ProductUpdated 等）
    - 根据配置失效相关实体的缓存

    开发者只需维护这个配置文件！
    """
    config = CacheInvalidationConfig()

    # ==================== 方式 1: 简单配置（推荐） ====================

    # Order 影响 Customer（客户订单统计）
    config.add_relation(
        create_simple_relation(source="Order", related="Customer", id_field="customer_id")
    )
    # 效果：Order 变更时自动失效 Customer:{customer_id}:*

    # Order 影响 Product（产品销量统计）
    config.add_relation(
        create_simple_relation(source="Order", related="Product", id_field="product_id")
    )
    # 效果：Order 变更时自动失效 Product:{product_id}:*

    # ==================== 方式 2: 详细配置 ====================

    # Review 影响 Product（评分和排名）
    config.add_relation(
        EntityRelation(
            source_entity="Review",
            related_entities=["Product"],
            operations=["CREATE", "UPDATE", "DELETE"],
            cache_patterns={
                "Product": [
                    "Product:{product_id}:rating:*",  # 产品评分缓存
                    "Product:{product_id}:reviews:*",  # 产品评论列表
                    "ProductRanking:by_rating:*",  # 全局评分排行榜
                ]
            },
        )
    )

    # OrderItem 影响 Product（库存和销量）
    config.add_relation(
        EntityRelation(
            source_entity="OrderItem",
            related_entities=["Product"],
            cache_patterns={
                "Product": [
                    "Product:{product_id}:stock:*",  # 库存统计
                    "Product:{product_id}:sales:*",  # 销量统计
                    "ProductRanking:by_sales:*",  # 销量排行榜
                ]
            },
        )
    )

    # ==================== 方式 3: 流式 API（最优雅） ====================

    builder = create_relation_builder()

    advanced_config = (
        builder
        # Payment 影响 Order 和 Customer
        .relation("Payment")
        .affects("Order", id_field="order_id")
        .affects("Customer", id_field="customer_id")
        .with_pattern("Customer:{customer_id}:spending:*")
        # Shipment 影响 Order
        .relation("Shipment")
        .affects("Order", id_field="order_id")
        .with_pattern("Order:{order_id}:tracking:*")
        # Inventory 影响 Product
        .relation("Inventory")
        .affects("Product", id_field="product_id")
        .with_pattern("Product:{product_id}:availability:*")
        .build()
    )

    # 合并配置
    for relations in advanced_config._relations.values():
        for relation in relations:
            config.add_relation(relation)

    return config


# ==================== 使用示例（给开发者看） ====================

"""
配置完成后，框架会自动处理！

示例 1：创建订单
```python
# 应用层代码
class OrderService:
    async def create_order(self, order_data):
        # 1. 创建订单
        order = Order(...)
        await self._order_repo.save(order)

        # ✅ 框架自动做了以下事情：
        # - Order 相关缓存自动失效（拦截器处理）
        # - 发布 OrderCreated 事件
        # - 事件处理器识别到 Order.CREATE
        # - 自动失效 Customer:{customer_id}:* 缓存
        # - 自动失效 Product:{product_id}:* 缓存

        # ❌ 你不需要写：
        # await cache.delete_pattern(f"Customer:{order.customer_id}:*")
        # await cache.delete_pattern(f"Product:{product_id}:*")
```

示例 2：添加评论
```python
class ReviewService:
    async def create_review(self, review_data):
        # 1. 创建评论
        review = Review(...)
        await self._review_repo.save(review)

        # ✅ 框架自动失效：
        # - Review 相关缓存（拦截器）
        # - Product:{product_id}:rating:* （配置的关联）
        # - Product:{product_id}:reviews:* （配置的关联）
        # - ProductRanking:by_rating:* （配置的关联）

        # ✅ 完全自动，零遗漏！
```

示例 3：更新库存
```python
class InventoryService:
    async def update_stock(self, inventory_data):
        inventory = Inventory(...)
        await self._inventory_repo.save(inventory)

        # ✅ 框架自动失效：
        # - Inventory 相关缓存（拦截器）
        # - Product:{product_id}:availability:* （配置的关联）
```

好处：
1. ✅ 开发者只需维护配置文件
2. ✅ 不会遗忘失效缓存
3. ✅ 集中管理，易于审查
4. ✅ 框架自动处理，零人工干预
5. ✅ 支持复杂的多对多关联
"""
