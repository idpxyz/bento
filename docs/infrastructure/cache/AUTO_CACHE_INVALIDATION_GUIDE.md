# 自动跨实体缓存失效指南

## 🎯 **问题**

手动管理跨实体缓存失效容易遗漏：

```python
# ❌ 开发者需要记住所有关联关系
class OrderService:
    async def create_order(self, order):
        await self._order_repo.save(order)

        # 😰 容易忘记：
        await cache.delete_pattern(f"Customer:{order.customer_id}:*")
        await cache.delete_pattern(f"Product:{product_id}:*")
        await cache.delete_pattern("ProductRanking:*")
        # ... 还有其他吗？记不清了！
```

## ✅ **解决方案**

框架自动处理！开发者只需配置关联关系：

```python
# ✅ 配置一次，永远有效
config.add_relation(
    create_simple_relation(
        source="Order",
        related=["Customer", "Product"],
        id_field="customer_id"
    )
)

# ✅ 之后代码无需改变
class OrderService:
    async def create_order(self, order):
        await self._order_repo.save(order)
        # ✅ 框架自动失效 Customer 和 Product 缓存！
```

## 🚀 **快速开始**

### 1. 配置关联关系

编辑 `config/cache_relations.py`：

```python
def configure_cache_relations():
    config = CacheInvalidationConfig()

    # Order 影响 Customer
    config.add_relation(
        create_simple_relation(
            source="Order",
            related="Customer",
            id_field="customer_id"
        )
    )

    return config
```

### 2. 应用层代码保持不变

```python
class OrderService:
    async def create_order(self, order_data):
        order = Order(...)
        await self._order_repo.save(order)
        # ✅ 完全不需要关心缓存失效！
```

### 3. 框架自动处理

```
Order.save() → OrderCreated 事件 → 自动失效 Customer 缓存 ✅
```

## 📖 **详细配置指南**

### 配置方式 1：简单配置（推荐新手）

```python
# 适用场景：简单的一对一关联
config.add_relation(
    create_simple_relation(
        source="Order",        # 源实体
        related="Customer",    # 受影响的实体
        id_field="customer_id" # 关联字段
    )
)

# 效果：失效 Customer:{customer_id}:* 所有缓存
```

### 配置方式 2：精确配置（推荐生产环境）

```python
# 适用场景：需要精确控制失效范围
config.add_relation(
    EntityRelation(
        source_entity="Review",
        related_entities=["Product"],
        operations=["CREATE", "UPDATE", "DELETE"],
        cache_patterns={
            "Product": [
                "Product:{product_id}:rating:*",    # 只失效评分
                "Product:{product_id}:reviews:*",   # 只失效评论列表
                "ProductRanking:by_rating:*"        # 失效全局排名
            ]
        }
    )
)
```

### 配置方式 3：流式 API（推荐高级用户）

```python
builder = create_relation_builder()

config = (
    builder
    .relation("Payment")
        .affects("Order", id_field="order_id")
        .affects("Customer", id_field="customer_id")
        .with_pattern("Customer:{customer_id}:spending:*")
    .relation("Shipment")
        .affects("Order", id_field="order_id")
    .build()
)
```

## 💡 **实际场景示例**

### 场景 1：电商订单系统

```python
# 配置
config.add_relation(
    EntityRelation(
        source_entity="Order",
        related_entities=["Customer", "Product"],
        cache_patterns={
            "Customer": [
                "Customer:{customer_id}:orders:*",
                "Customer:{customer_id}:spending:*"
            ],
            "Product": [
                "Product:{product_id}:sales:*",
                "ProductRanking:by_sales:*"
            ]
        }
    )
)

# 应用代码
class OrderService:
    async def create_order(self, order: Order):
        # 1. 保存订单
        await self._order_repo.save(order)

        # ✅ 自动失效：
        # - Order:* （拦截器）
        # - Customer:{customer_id}:orders:*
        # - Customer:{customer_id}:spending:*
        # - Product:{product_id}:sales:*
        # - ProductRanking:by_sales:*

        # 2. 更新库存
        for item in order.items:
            product = await self._product_repo.get(item.product_id)
            product.stock -= item.quantity
            await self._product_repo.save(product)

            # ✅ 自动失效：
            # - Product:id:{product_id}
            # - Product:agg:* （拦截器）
```

### 场景 2：评价系统

```python
# 配置
config.add_relation(
    EntityRelation(
        source_entity="Review",
        related_entities=["Product", "User"],
        cache_patterns={
            "Product": [
                "Product:{product_id}:rating:*",
                "Product:{product_id}:review_count:*",
                "ProductRanking:by_rating:*"
            ],
            "User": [
                "User:{user_id}:reviews:*",
                "User:{user_id}:contribution:*"
            ]
        }
    )
)

# 应用代码
class ReviewService:
    async def create_review(self, review: Review):
        await self._review_repo.save(review)

        # ✅ 自动失效所有配置的缓存
        # ✅ 不会遗漏任何一个
```

### 场景 3：库存管理

```python
# 配置
config.add_relation(
    EntityRelation(
        source_entity="Inventory",
        related_entities=["Product"],
        cache_patterns={
            "Product": [
                "Product:{product_id}:stock:*",
                "Product:{product_id}:availability:*",
                "Product:list:available:*"
            ]
        }
    )
)

# 应用代码
class InventoryService:
    async def update_stock(self, product_id: ID, quantity: int):
        inventory = await self._inventory_repo.get_by_product(product_id)
        inventory.quantity = quantity
        await self._inventory_repo.save(inventory)

        # ✅ 自动失效库存相关缓存
```

## 🔍 **工作原理**

### 完整流程

```
1. 开发者保存实体
   await repo.save(order)
        ↓
2. Repository 触发拦截器
   - AuditInterceptor（审计）
   - CacheInterceptor（失效同实体缓存）
        ↓
3. Repository 发布领域事件
   OrderCreated(order_id, customer_id, ...)
        ↓
4. DomainEventCacheInvalidator 监听事件
   - 识别实体类型："Order"
   - 识别操作类型："CREATE"
        ↓
5. 查找配置的关联关系
   - Order → Customer
   - Order → Product
        ↓
6. 失效关联实体缓存
   - delete_pattern("Customer:{customer_id}:*")
   - delete_pattern("Product:{product_id}:*")
        ↓
7. 完成 ✅
```

### 事件识别规则

框架自动识别标准事件命名：

| 事件名称 | 实体 | 操作 |
|---------|------|------|
| `OrderCreated` | Order | CREATE |
| `ProductUpdated` | Product | UPDATE |
| `ReviewDeleted` | Review | DELETE |
| `CustomerModified` | Customer | UPDATE |

## ⚙️ **配置选项详解**

### EntityRelation 参数

```python
EntityRelation(
    source_entity="Order",           # 源实体类型
    related_entities=["Customer"],   # 受影响的实体列表
    operations=["CREATE", "UPDATE"], # 触发的操作类型（可选）
    cache_patterns={                 # 自定义失效模式（可选）
        "Customer": [
            "Customer:{customer_id}:*"
        ]
    }
)
```

### 占位符说明

缓存模式支持占位符，从事件数据中自动替换：

```python
cache_patterns={
    "Product": [
        "Product:{product_id}:*",           # ✅ {product_id} 从事件获取
        "Category:{category_id}:products:*" # ✅ {category_id} 从事件获取
    ]
}

# 事件数据示例：
# {
#     "product_id": "p123",
#     "category_id": "cat456"
# }

# 实际失效：
# - Product:p123:*
# - Category:cat456:products:*
```

## 📊 **性能优化**

### 1. 精确配置模式

```python
# ❌ 过度失效
cache_patterns={
    "Product": ["Product:*"]  # 失效所有商品缓存
}

# ✅ 精确失效
cache_patterns={
    "Product": [
        "Product:{product_id}:sales:*",  # 只失效销量
        "ProductRanking:by_sales:*"      # 只失效排名
    ]
}
```

### 2. 批量操作优化

```python
# ✅ 批量操作会自动合并失效
await repo.batch_create(orders)  # 只触发一次缓存失效
```

### 3. 选择性配置

```python
# 只在必要的操作时失效
EntityRelation(
    source_entity="Order",
    operations=["CREATE", "DELETE"],  # ✅ 只监听创建和删除
    # UPDATE 不触发失效
)
```

## 🧪 **测试和验证**

### 验证配置

```python
# 测试配置是否生效
async def test_order_invalidates_customer_cache():
    # 1. 预热缓存
    customer_orders = await customer_service.get_orders(customer_id)
    assert cache_hit  # 第二次从缓存读取

    # 2. 创建订单
    order = Order(customer_id=customer_id, ...)
    await order_repo.save(order)

    # 3. 验证缓存已失效
    customer_orders = await customer_service.get_orders(customer_id)
    assert cache_miss  # ✅ 缓存已失效，重新查询
```

### 监控失效

```python
# 添加日志
class MonitoredDomainEventCacheInvalidator(DomainEventCacheInvalidator):
    async def on_domain_event(self, event):
        logger.info(f"Processing cache invalidation for: {event.name}")
        await super().on_domain_event(event)
        logger.info(f"Cache invalidation completed for: {event.name}")
```

## 🎓 **最佳实践**

### 1. 集中配置

```python
# ✅ 所有关联关系在一个文件中
# config/cache_relations.py

# ❌ 不要分散在多个地方
```

### 2. 文档化关联关系

```python
# ✅ 添加注释说明为什么需要这个关联
config.add_relation(
    EntityRelation(
        source_entity="Review",
        related_entities=["Product"],
        # 📝 原因：评论会影响产品的平均评分和评论数
        cache_patterns={
            "Product": ["Product:{product_id}:rating:*"]
        }
    )
)
```

### 3. 定期审查

```python
# 定期检查是否有遗漏的关联关系
# 1. 查看所有跨实体查询
# 2. 确认是否已配置关联
# 3. 添加缺失的配置
```

### 4. 测试覆盖

```python
# 为每个关联关系编写测试
@pytest.mark.asyncio
async def test_order_creation_invalidates_customer_cache():
    ...

@pytest.mark.asyncio
async def test_review_creation_invalidates_product_rating():
    ...
```

## 🚨 **常见问题**

### Q1: 如何处理多对多关联？

```python
# Order 包含多个 Product
config.add_relation(
    EntityRelation(
        source_entity="Order",
        related_entities=["Product"],
        cache_patterns={
            "Product": [
                # ✅ 框架会自动遍历 order.items
                "Product:{product_id}:sales:*"
            ]
        }
    )
)

# 确保事件包含所有相关 ID
class OrderCreatedEvent(DomainEvent):
    order_id: ID
    customer_id: ID
    product_ids: list[ID]  # ✅ 包含所有产品 ID
```

### Q2: 如何处理条件失效？

```python
# 使用自定义事件处理器
class ConditionalCacheInvalidator:
    async def on_order_created(self, event: OrderCreatedEvent):
        # 只在大额订单时失效 VIP 缓存
        if event.total_amount > 10000:
            await cache.delete_pattern("VIPCustomer:*")
```

### Q3: 性能影响如何？

```python
# 失效操作是异步的，不阻塞主流程
await repo.save(order)  # ← 这里已经完成
# 缓存失效在后台异步执行 ✅
```

## 📝 **迁移指南**

### 从手动失效迁移到自动失效

#### Before（手动管理）

```python
class OrderService:
    async def create_order(self, order):
        await self._order_repo.save(order)

        # 手动失效
        await self._cache.delete_pattern(f"Customer:{order.customer_id}:*")
        await self._cache.delete_pattern(f"Product:{product_id}:*")
```

#### After（自动管理）

```python
# 1. 添加配置
config.add_relation(
    create_simple_relation("Order", ["Customer", "Product"])
)

# 2. 删除手动失效代码
class OrderService:
    async def create_order(self, order):
        await self._order_repo.save(order)
        # ✅ 就这样！框架自动处理
```

## ✅ **总结**

### 开发者只需要：

1. ✅ 定义实体关联关系（一次性配置）
2. ✅ 正常保存实体（无需关心缓存）
3. ✅ 框架自动失效所有相关缓存

### 框架自动处理：

1. ✅ 监听所有领域事件
2. ✅ 识别实体变更类型
3. ✅ 根据配置失效相关缓存
4. ✅ 零遗漏、零人工干预

### 好处：

- 🚀 **不会忘记** - 配置一次，永远有效
- 🔧 **易于维护** - 集中管理，清晰可见
- 🎯 **类型安全** - 配置错误会在启动时发现
- ⚡ **高性能** - 异步失效，不阻塞主流程
- 📊 **可审计** - 所有关联关系一目了然

**彻底解决跨实体缓存失效的遗忘问题！** 🎉
