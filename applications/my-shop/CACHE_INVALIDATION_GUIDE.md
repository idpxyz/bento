# 缓存失效机制详解

## 🎯 核心原则

**所有写操作都会自动失效相关缓存，确保数据一致性**

## 📋 自动失效场景

### 1. 单个实体操作

#### CREATE - 创建实体
```python
product = Product(id=ID("p1"), name="iPhone", price=999)
await repo.save(product)
```

**自动失效的缓存：**
- ✅ `Product:agg:*` - 所有聚合统计（总价、平均价等）
- ✅ `Product:group:*` - 所有分组统计
- ✅ `Product:sort:*` - 所有排序查询
- ✅ `Product:page:*` - 所有分页查询
- ✅ `Product:query:*` - 所有条件查询

**为什么？** 新增产品会影响所有统计结果。

#### UPDATE - 更新实体
```python
product.price = 899  # 降价
await repo.save(product)
```

**自动失效的缓存：**
- ✅ `Product:id:p1` - 该产品的缓存
- ✅ `Product:agg:*` - 价格变化影响聚合统计
- ✅ `Product:group:*` - 可能影响分组
- ✅ `Product:sort:*` - 价格变化影响排序
- ✅ `Product:page:*` - 影响分页结果
- ✅ `Product:query:*` - 影响查询结果

**为什么？** 属性变化可能影响所有查询。

#### DELETE - 删除实体
```python
await repo.delete(product)
```

**自动失效的缓存：**
- ✅ 与 UPDATE 相同，失效所有相关缓存

**为什么？** 实体删除影响所有统计和查询。

### 2. 批量操作

#### BATCH_CREATE - 批量创建
```python
products = [Product(...) for i in range(100)]
await repo.batch_create(products)
```

**自动失效的缓存：**
- ✅ 所有 `Product:*` 相关的缓存

#### BATCH_UPDATE - 批量更新
```python
await repo.batch_update(products)
```

**自动失效的缓存：**
- ✅ 每个产品的 `Product:id:{id}` 缓存
- ✅ 所有 `Product:agg:*`, `Product:group:*` 等缓存

#### BATCH_DELETE - 批量删除
```python
await repo.batch_delete(products)
```

**自动失效的缓存：**
- ✅ 每个产品的 ID 缓存
- ✅ 所有聚合、分组、排序、分页缓存

## 🔍 完整的缓存失效流程

### 写操作触发链

```
1. 应用层调用
   await repo.save(product)
        ↓
2. 拦截器 before_operation
   - 准备上下文
        ↓
3. 执行数据库操作
   - INSERT/UPDATE/DELETE
        ↓
4. 拦截器 process_result
   - 检测到写操作
   - 调用 _invalidate_related()
        ↓
5. 缓存失效
   - delete(Product:id:123)
   - delete_pattern(Product:agg:*)
   - delete_pattern(Product:group:*)
   - delete_pattern(Product:sort:*)
   - delete_pattern(Product:page:*)
   - delete_pattern(Product:query:*)
        ↓
6. 返回结果
```

## 💡 实际示例

### 示例 1: 商品价格变化

```python
# 场景：降价促销
product = await repo.get(ID("p1"))
product.price = 799  # 原价 999

# 保存更新
await repo.save(product)

# ✅ 以下缓存全部失效：
# - Product:id:p1 (该商品缓存)
# - Product:agg:sum:price:* (总价统计)
# - Product:agg:avg:price:* (平均价统计)
# - Product:sort:top_n:-price:* (最贵商品排行榜)
# - Product:page:1:20:-price:* (按价格排序的分页)
# - Product:group:category_id:* (类别统计)

# ✅ 下次查询会重新计算：
total_value = await repo.sum_field("price")  # 重新查询数据库
top_products = await repo.find_top_n(10, order_by="-price")  # 重新查询
```

### 示例 2: 新增商品

```python
# 场景：上架新品
new_product = Product(
    id=ID("p100"),
    name="iPad Pro",
    price=1299,
    category_id="tablets"
)

# 保存新品
await repo.save(new_product)

# ✅ 以下统计缓存全部失效：
# - Product:agg:count:id:* (商品总数)
# - Product:agg:sum:price:* (总库存价值)
# - Product:group:category_id:* (类别分布 - tablets +1)
# - Product:sort:first:-created_at:* (最新商品)
# - Product:page:*:*:* (所有分页)

# ✅ 下次查询会包含新品：
count = await repo.count_field("id")  # 重新统计
category_dist = await repo.group_by_field("category_id")  # tablets +1
```

### 示例 3: 批量删除过期商品

```python
# 场景：清理下架商品
expired_products = await repo.find(ProductSpec().is_expired())

# 批量删除
await repo.batch_delete(expired_products)

# ✅ 失效所有相关缓存：
# - 每个商品的 ID 缓存
# - 所有统计缓存（总数减少、平均价可能变化）
# - 所有分组缓存（各类别数量减少）
# - 所有排序/分页缓存

# ✅ 下次查询反映最新数据：
active_count = await repo.count_field("id")  # 排除已删除的
category_stats = await repo.group_by_field("category_id")  # 更新统计
```

## ⚡ 性能优化建议

### 1. 使用 Pattern 删除

```python
# ✅ 高效：使用 pattern 一次删除多个
await cache.delete_pattern("Product:agg:*")

# ❌ 低效：逐个删除
await cache.delete("Product:agg:sum:price:none")
await cache.delete("Product:agg:avg:price:none")
# ... 很多次
```

### 2. 批量操作合并

```python
# ✅ 推荐：批量操作
products = [Product(...) for i in range(100)]
await repo.batch_create(products)
# 只触发一次缓存失效

# ❌ 避免：循环单个操作
for product in products:
    await repo.save(product)
# 触发100次缓存失效！
```

### 3. 选择性缓存

```python
# 高频变动的数据：不缓存或短期缓存
cache_config = {
    OperationType.AGGREGATE: 60,  # 1分钟（如果数据变化频繁）
}

# 稳定的历史数据：长期缓存
cache_config = {
    OperationType.GROUP_BY: 86400,  # 24小时（历史统计）
}
```

## 🔧 自定义失效策略

### 场景：跨实体类型失效

```python
class OrderService:
    async def create_order(self, order: Order):
        # 创建订单
        await self._order_repo.save(order)

        # ✅ 订单缓存自动失效

        # ⚠️ 但如果需要失效关联实体的缓存：
        # 例如：产品库存统计、客户订单统计

        # 手动失效相关缓存
        await self._cache.delete_pattern("Product:agg:sum:stock:*")
        await self._cache.delete_pattern(f"Customer:orders:{order.customer_id}:*")
```

### 场景：事件驱动失效

```python
class CacheInvalidationHandler:
    """监听领域事件，智能失效缓存"""

    @event_handler(OrderCreatedEvent)
    async def on_order_created(self, event: OrderCreatedEvent):
        # 失效订单统计
        await cache.delete_pattern("Order:agg:*")
        await cache.delete_pattern("Order:group:*")

        # 失效客户统计
        customer_id = event.customer_id
        await cache.delete_pattern(f"Customer:{customer_id}:*")

    @event_handler(ProductStockChangedEvent)
    async def on_stock_changed(self, event: ProductStockChangedEvent):
        # 失效库存统计
        await cache.delete_pattern("Product:agg:sum:stock:*")
        await cache.delete_pattern("Product:group:stock_status:*")
```

## 📊 失效监控

### 记录失效日志

```python
class MonitoredCacheInterceptor(CacheInterceptor):
    async def _invalidate_related(self, context):
        et = self._get_entity_type(context)

        # 记录失效操作
        logger.info(f"Invalidating cache for {et} after {context.operation}")

        # 执行失效
        await super()._invalidate_related(context)

        # 统计
        metrics.increment(f"cache.invalidation.{et}")
```

### 失效统计

```python
# 查看失效频率
GET /metrics/cache/invalidation

{
    "Product": {
        "total_invalidations": 1250,
        "last_invalidation": "2025-11-21T21:26:00Z"
    },
    "Order": {
        "total_invalidations": 3400,
        "last_invalidation": "2025-11-21T21:25:55Z"
    }
}
```

## ✅ 最佳实践总结

1. **信任自动失效** - 框架会处理大部分场景
2. **批量操作优先** - 减少失效次数
3. **合理设置 TTL** - 平衡性能和一致性
4. **监控失效频率** - 发现过度失效的问题
5. **跨实体手动处理** - 需要时显式失效关联缓存

## 🎯 结论

**99% 的场景下，你不需要关心缓存失效**

框架会自动处理：
- ✅ 所有单个实体的写操作
- ✅ 所有批量操作
- ✅ 所有聚合、分组、排序、分页的缓存失效

只有在**跨实体关联**的特殊场景下，才需要手动失效缓存。
