# 在 my-shop 中使用 Repository Mixins

## 🎉 好消息！

**所有 29 个增强方法已经在你的 Repository 中可用了！**

无需任何配置，所有继承自 `RepositoryAdapter` 的 Repository 都自动获得了这些方法。

## ✅ 已经可用的 Repository

1. **ProductRepository** - `/contexts/catalog/infrastructure/repositories/product_repository_impl.py`
2. **CategoryRepository** - `/contexts/catalog/infrastructure/repositories/category_repository_impl.py`
3. **OrderRepository** - `/contexts/ordering/infrastructure/repositories/order_repository_impl.py`
4. **UserRepository** - `/contexts/identity/infrastructure/repositories/user_repository_impl.py`

## 🚀 立即使用示例

### 1. 在 Product Service 中使用

```python
# contexts/catalog/application/services/product_service.py

class ProductApplicationService:
    def __init__(self, product_repo: ProductRepository):
        self._repo = product_repo

    # ✅ P0: 批量操作
    async def get_products_for_cart(self, product_ids: list[ID]) -> list[Product]:
        """批量获取购物车商品 - 一次数据库查询"""
        return await self._repo.get_by_ids(product_ids)

    # ✅ P1: 聚合查询
    async def get_inventory_value(self) -> float:
        """计算库存总价值"""
        return await self._repo.sum_field("price")

    async def get_average_price(self) -> float:
        """计算平均价格"""
        return await self._repo.avg_field("price")

    # ✅ P1: 排序查询
    async def get_top_selling_products(self, limit: int = 10) -> list[Product]:
        """获取销量最高的产品"""
        return await self._repo.find_top_n(limit, order_by="-sales_count")

    async def get_latest_products(self, limit: int = 10) -> list[Product]:
        """获取最新产品"""
        return await self._repo.find_top_n(limit, order_by="-created_at")

    #  P1: 分页查询
    async def list_products_paginated(
        self, page: int, page_size: int
    ) -> tuple[list[Product], int]:
        """分页列表"""
        return await self._repo.find_paginated(page, page_size, order_by="name")

    # ✅ P2: 分组统计
    async def get_category_distribution(self) -> dict[str, int]:
        """按类别统计产品数量"""
        return await self._repo.group_by_field("category_id")

    # ✅ P3: 随机推荐
    async def get_featured_products(self, count: int = 5) -> list[Product]:
        """随机推荐产品"""
        return await self._repo.find_random_n(count)
```

### 2. 在 Order Service 中使用

```python
# contexts/ordering/application/services/order_analytics_service.py

class OrderAnalyticsService:
    def __init__(self, order_repo: OrderRepositoryImpl):
        self._repo = order_repo

    # ✅ 财务分析
    async def get_revenue_stats(self) -> dict:
        """获取收入统计"""
        return {
            "total_revenue": await self._repo.sum_field("total_amount"),
            "average_order": await self._repo.avg_field("total_amount"),
            "min_order": await self._repo.min_field("total_amount"),
            "max_order": await self._repo.max_field("total_amount"),
            "total_orders": await self._repo.count_field("id"),
        }

    # ✅ 趋势分析
    async def get_daily_trend(self) -> dict[str, int]:
        """每日订单趋势"""
        return await self._repo.group_by_date("created_at", "day")

    async def get_monthly_revenue(self) -> dict[str, int]:
        """月度订单统计"""
        return await self._repo.group_by_date("created_at", "month")

    # ✅ 客户分析
    async def count_unique_customers(self) -> int:
        """统计不同客户数"""
        return await self._repo.count_field("customer_id", distinct=True)

    async def get_customer_orders(self, customer_id: str) -> list[Order]:
        """获取客户所有订单"""
        return await self._repo.find_all_by_field("customer_id", customer_id)

    # ✅ 状态分布
    async def get_status_distribution(self) -> dict[str, int]:
        """订单状态分布"""
        return await self._repo.group_by_field("status")
```

### 3. 在 User Service 中使用

```python
# contexts/identity/application/services/user_service.py

class UserApplicationService:
    def __init__(self, user_repo: UserRepositoryImpl):
        self._repo = user_repo

    # ✅ 唯一性验证
    async def is_email_available(self, email: str) -> bool:
        """检查邮箱是否可用"""
        return await self._repo.is_unique("email", email)

    async def is_email_available_for_update(
        self, email: str, user_id: ID
    ) -> bool:
        """更新时检查邮箱（排除自己）"""
        return await self._repo.is_unique("email", email, exclude_id=user_id)

    # ✅ 查找用户
    async def find_by_email(self, email: str) -> User | None:
        """通过邮箱查找用户"""
        return await self._repo.find_by_field("email", email)

    # ✅ 批量操作
    async def get_users_batch(self, user_ids: list[ID]) -> list[User]:
        """批量获取用户"""
        return await self._repo.get_by_ids(user_ids)
```

## 📊 实际应用场景

### 场景 1: 购物车结算

```python
async def checkout(self, cart_items: list[CartItem]):
    # ✅ 旧方式：循环查询，N次数据库访问
    # products = []
    # for item in cart_items:
    #     product = await product_repo.get_by_id(item.product_id)
    #     products.append(product)

    # ✅ 新方式：一次查询完成
    product_ids = [item.product_id for item in cart_items]
    products = await self._product_repo.get_by_ids(product_ids)
```

### 场景 2: 管理后台统计

```python
async def get_dashboard_data(self):
    # ✅ 使用多个增强方法快速获取统计数据
    return {
        # 产品统计
        "total_products": await self._product_repo.count_field("id"),
        "total_value": await self._product_repo.sum_field("price"),
        "avg_price": await self._product_repo.avg_field("price"),
        "category_dist": await self._product_repo.group_by_field("category_id"),

        # 订单统计
        "total_revenue": await self._order_repo.sum_field("total_amount"),
        "total_orders": await self._order_repo.count_field("id"),
        "daily_orders": await self._order_repo.group_by_date("created_at", "day"),
        "status_dist": await self._order_repo.group_by_field("status"),

        # 用户统计
        "unique_customers": await self._order_repo.count_field(
            "customer_id", distinct=True
        ),
    }
```

### 场景 3: 产品推荐

```python
async def get_recommendations_for_user(self, user: User):
    # ✅ 随机推荐 + 规则过滤
    # 这里演示纯随机，实际可结合 Specification 添加过滤条件
    recommendations = await self._product_repo.find_random_n(10)
    return recommendations
```

### 场景 4: 数据分析报表

```python
async def generate_sales_report(self, start_date: date, end_date: date):
    # ✅ 结合 Specification（待实现）可以过滤日期范围
    # spec = OrderSpec().created_between(start_date, end_date)

    # 当前可以直接获取全量统计
    return {
        "daily_trend": await self._order_repo.group_by_date("created_at", "day"),
        "weekly_trend": await self._order_repo.group_by_date("created_at", "week"),
        "monthly_trend": await self._order_repo.group_by_date("created_at", "month"),
        "status_breakdown": await self._order_repo.group_by_field("status"),
        "payment_methods": await self._order_repo.group_by_field("payment_method"),
    }
```

## 💡 最佳实践

### 1. 在 Application Service 中使用

```python
✅ 推荐：在 Application Service 层调用
❌ 避免：在 Domain 层直接调用 Repository 增强方法
```

### 2. 结合业务逻辑

```python
# ✅ 好的实践
async def get_available_products(self):
    # 1. 使用增强方法获取数据
    products, total = await self._repo.find_paginated(1, 20)

    # 2. 应用业务逻辑
    available = [p for p in products if p.is_available()]

    return available, total

# ❌ 不好的实践：只依赖增强方法，忽略业务规则
async def get_products(self):
    return await self._repo.find_all()  # 没有业务过滤
```

### 3. 性能优化

```python
# ✅ 使用聚合函数（数据库计算）
total = await repo.sum_field("price")

# ❌ 加载所有数据再计算（内存计算）
products = await repo.find_all()
total = sum(p.price for p in products)
```

## 📚 更多资源

- **完整指南**: `/docs/infrastructure/REPOSITORY_MIXINS_GUIDE.md`
- **快速参考**: `/docs/infrastructure/REPOSITORY_MIXINS_QUICK_REF.md`
- **示例代码**:
  - `/contexts/catalog/application/services/product_enhanced_service.py`
  - `/contexts/ordering/application/services/order_analytics_service.py`

## 🎯 下一步

1. ✅ **立即使用** - 在现有 Service 中调用新方法
2. ✅ **重构代码** - 用新方法替换现有的复杂查询
3. ✅ **添加功能** - 利用新方法快速实现新功能
4. ✅ **性能优化** - 用批量操作替换循环查询

---

**提示**: 所有这些方法都是类型安全的，你的 IDE 会提供自动补全！
