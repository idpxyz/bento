# Phase 2: Query 返回 DTO 迁移计划

## 🎯 目标

将所有 Query Handlers 从返回领域对象（AR）改为返回 DTO（数据传输对象），符合 CQRS 最佳实践。

## ❌ 当前问题

```python
# ❌ 当前：Query 返回领域对象
@query_handler
class GetProductHandler(QueryHandler[GetProductQuery, Product]):
    async def handle(self, query):
        repo = self.uow.repository(Product)
        product = await repo.get(ID(query.product_id))
        return product  # 返回 Product 聚合根
```

**问题**：
1. 违反 CQRS 原则（Query 不应暴露领域对象）
2. 可能暴露领域逻辑
3. 性能问题（加载完整聚合根）
4. 耦合了查询和领域模型

## ✅ 目标模式

```python
# ✅ 正确：Query 返回 DTO
@dataclass
class ProductDTO:
    id: str
    name: str
    price: float
    ...
    
    @classmethod
    def from_domain(cls, product: Product) -> "ProductDTO":
        return cls(
            id=str(product.id),
            name=product.name,
            price=product.price,
            ...
        )

@query_handler
class GetProductHandler(QueryHandler[GetProductQuery, ProductDTO]):
    async def handle(self, query):
        repo = self.uow.repository(Product)
        product = await repo.get(ID(query.product_id))
        if not product:
            raise EntityNotFoundError(...)
        return ProductDTO.from_domain(product)  # 返回 DTO
```

## 📊 需要迁移的 Query Handlers

### Catalog 模块 (4个)
- [ ] GetProductHandler → ProductDTO
- [ ] ListProductsHandler → list[ProductDTO]
- [ ] GetCategoryHandler → CategoryDTO
- [ ] ListCategoriesHandler → list[CategoryDTO]

### Order 模块 (2个)
- [ ] GetOrderHandler → OrderDTO
- [ ] ListOrdersHandler → list[OrderDTO]

### User 模块 (1个)
- [ ] GetUserHandler → UserDTO

**总计**: 7 个 Query Handlers

## 🛠️ 实施步骤

### Step 1: 创建 DTO 类
在每个 Context 的 `application/dto/` 目录下创建 DTO：

```
contexts/catalog/application/dto/
├── __init__.py
├── product_dto.py
└── category_dto.py

contexts/ordering/application/dto/
├── __init__.py
└── order_dto.py

contexts/identity/application/dto/
├── __init__.py
└── user_dto.py
```

### Step 2: 定义 DTO 结构

每个 DTO 包含：
1. 所有需要返回的字段
2. `from_domain()` 类方法（从领域对象转换）
3. 可选：嵌套 DTO（如 OrderItemDTO）

### Step 3: 更新 Query Handlers

1. 修改返回类型注解
2. 在 `handle()` 方法中转换为 DTO
3. 更新异常处理

### Step 4: 更新 API Response Models

API 层的 Response Models 可以直接使用 DTO 或基于 DTO 创建。

## 🎯 预期效果

### 代码对比

**Before**:
```python
# Query Handler
class GetProductHandler(QueryHandler[GetProductQuery, Product]):
    async def handle(self, query):
        return await repo.get(query.product_id)

# API 层需要转换
@router.get("/{id}")
async def get_product(handler):
    product = await handler.execute(query)
    return product_to_dict(product)  # 手动转换
```

**After**:
```python
# Query Handler
class GetProductHandler(QueryHandler[GetProductQuery, ProductDTO]):
    async def handle(self, query):
        product = await repo.get(query.product_id)
        return ProductDTO.from_domain(product)  # 在 Handler 中转换

# API 层直接返回
@router.get("/{id}")
async def get_product(handler):
    return await handler.execute(query)  # 直接返回 DTO
```

### 优势

1. ✅ **CQRS 原则**：严格分离读写
2. ✅ **性能优化**：只加载需要的字段
3. ✅ **解耦**：查询不依赖领域模型
4. ✅ **API 简化**：无需手动转换
5. ✅ **类型安全**：明确的 DTO 类型

## 📝 注意事项

1. **向后兼容**：现有的 `*_to_dict()` presenter 函数可以保留或移除
2. **嵌套对象**：如 Order 包含 OrderItems，需要嵌套 DTO
3. **列表查询**：返回 `list[DTO]` 而非 `list[AR]`
4. **分页结果**：需要定义 Result DTO（包含 items + metadata）

## 🚀 下一步行动

1. 创建所有 DTO 类
2. 逐个迁移 Query Handlers
3. 简化 API 层代码
4. 测试验证
5. 移除旧的 presenter 函数（可选）

---

**预计时间**: 1-2 小时  
**优先级**: 高（符合架构最佳实践）
