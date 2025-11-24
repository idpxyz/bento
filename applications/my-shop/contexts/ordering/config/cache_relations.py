"""Ordering 上下文的跨实体缓存失效配置.

Order 实体的跨实体关联：
1. Order → Customer（客户订单统计、消费金额）
2. Order → Product（产品销量、库存）

框架会自动监听 Order 的事件并失效相关缓存。
"""

from bento.persistence.interceptor.auto_cache_invalidation import (
    CacheInvalidationConfig,
    create_relation_builder,
)


def configure_ordering_cache_relations() -> CacheInvalidationConfig:
    """配置 Ordering 上下文的缓存关联关系.

    Order 是订单上下文的核心聚合根，它的变化会影响：
    - Customer：客户的订单数量、消费总额、订单历史
    - Product：产品的销量统计、库存状态、热度排名
    """
    builder = create_relation_builder()

    config = (
        builder
        # ==================== Order 关联配置 ====================
        .relation("Order")
        # Order 影响 Customer（客户统计）
        .affects("Customer", id_field="customer_id")
        .with_pattern("Customer:{customer_id}:orders:*")  # 客户订单列表
        .with_pattern("Customer:{customer_id}:spending:*")  # 客户消费统计
        .with_pattern("Customer:{customer_id}:order_count:*")  # 客户订单数量
        # Order 影响 Product（销量统计）
        # 注意：Order 包含多个 OrderItem，每个 item 有 product_id
        # 框架会自动遍历 items 并失效每个 product 的缓存
        .affects("Product")  # 不指定 id_field，使用事件中的 items
        .with_pattern("Product:sales:*")  # 全局销量统计
        .with_pattern("ProductRanking:by_sales:*")  # 销量排行榜
        # ==================== OrderItem 关联配置（可选）====================
        # 如果 OrderItem 独立变化（不通过 Order），也需要配置
        # .relation("OrderItem")
        #     .affects("Product", id_field="product_id")
        #     .with_pattern("Product:{product_id}:sales:*")
        .build()
    )

    return config


# ==================== 详细说明（给开发者看） ====================

"""
配置完成后的效果：

场景 1：创建订单
-------------------
```python
class OrderService:
    async def create_order(self, order_data):
        # 1. 创建订单
        order = Order(
            customer_id="c123",
            items=[
                OrderItem(product_id="p1", quantity=2),
                OrderItem(product_id="p2", quantity=1),
            ]
        )
        await self._order_repo.save(order)

        # ✅ 框架自动失效以下缓存：
        #
        # 拦截器自动失效（同实体）：
        # - Order:id:{order_id}
        # - Order:agg:*
        # - Order:group:*
        # - Order:sort:*
        # - Order:page:*
        #
        # 配置的跨实体失效：
        # - Customer:c123:orders:*          （客户订单列表）
        # - Customer:c123:spending:*        （客户消费统计）
        # - Customer:c123:order_count:*     （客户订单数量）
        # - Product:sales:*                 （全局销量）
        # - ProductRanking:by_sales:*       （销量排行）
```

场景 2：订单支付
-------------------
```python
class OrderService:
    async def confirm_payment(self, order_id: ID):
        order = await self._order_repo.get(order_id)
        order.confirm_payment()  # 触发 OrderPaidEvent
        await self._order_repo.save(order)

        # ✅ 框架自动失效：
        # - Order 相关缓存（拦截器）
        # - Customer 统计缓存（配置的关联）
        # - Product 销量缓存（配置的关联）
```

场景 3：订单取消
-------------------
```python
class OrderService:
    async def cancel_order(self, order_id: ID, reason: str):
        order = await self._order_repo.get(order_id)
        order.cancel(reason)  # 触发 OrderCancelledEvent
        await self._order_repo.save(order)

        # ✅ 框架自动失效：
        # - Order 相关缓存（拦截器）
        # - Customer 统计缓存（需要重新计算）
        # - Product 销量缓存（取消订单影响销量）
```

特殊处理：Order 包含多个 Product
-----------------------------------
Order 的 items 包含多个 product_id，框架会智能处理：

1. 事件数据包含所有 product_id：
   ```python
   OrderCreatedEvent(
       order_id=order.id,
       customer_id="c123",
       items=[
           {"product_id": "p1", ...},
           {"product_id": "p2", ...},
       ]
   )
   ```

2. 框架自动遍历并失效每个产品的缓存：
   - Product:p1:sales:*
   - Product:p2:sales:*
   - Product:sales:* （全局）
   - ProductRanking:by_sales:* （排行榜）

优势：
-----
✅ 开发者不需要记住失效哪些缓存
✅ 订单创建、支付、取消都自动处理
✅ 多产品场景自动遍历
✅ 新增字段只需更新配置，代码无需改变
✅ 零遗漏、零出错

注意事项：
---------
1. 确保事件包含所有必要的 ID（customer_id, product_ids）
2. 如果有新的关联实体，只需更新此配置文件
3. 如果需要更精确的失效控制，使用完整的 EntityRelation 配置
"""
