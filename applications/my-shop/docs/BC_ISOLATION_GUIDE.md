# Bounded Context 隔离指南

## 🎯 核心原则

在 DDD 中，**Bounded Context (BC)** 是业务领域的边界。不同的 BC 之间必须保持隔离，避免直接依赖对方的领域模型。

### ✅ 正确的做法

```
Ordering BC  →  [反腐败层]  →  Catalog BC
   ↓                ↓              ↓
Domain         Interface      Domain
```

### ❌ 错误的做法

```
Ordering BC  →  直接引用  →  Catalog.Product
   ↓                           ↓
Domain                      Domain
```

---

## 📐 架构设计

### Bounded Context 划分

my-shop 项目有以下 4 个 BC：

1. **Catalog BC** - 商品目录管理
   - 聚合根：Product, Category
   - 职责：商品信息、分类管理

2. **Identity BC** - 身份认证
   - 聚合根：User
   - 职责：用户管理、认证授权

3. **Ordering BC** - 订单管理
   - 聚合根：Order（包含 OrderItem 实体）
   - 职责：订单生命周期管理

4. **Shared Context** - 共享内核
   - 集成事件、共享值对象

---

## 🔧 反腐败层实现

### 场景：Ordering BC 需要验证产品存在性

**问题：** Ordering BC 在创建订单时需要验证产品是否存在，但不应该直接依赖 Catalog BC 的 Product 聚合根。

**解决方案：** 使用反腐败层（Anti-Corruption Layer, ACL）

### 1. 定义值对象（Ordering BC 的视角）

```python
# contexts/ordering/domain/product_info.py

@dataclass(frozen=True)
class ProductInfo:
    """产品信息值对象（Ordering Context 的产品视图）"""
    product_id: str
    product_name: str
    unit_price: float
    is_available: bool = True
```

**关键点：**
- 这不是 Catalog BC 的 Product，而是 Ordering BC 需要的产品快照
- 只包含订单创建时需要的属性
- 作为不可变值对象（frozen=True）

### 2. 定义反腐败层接口（Port）

```python
# contexts/ordering/application/ports/product_catalog_service.py

class IProductCatalogService(ABC):
    """产品目录服务接口（反腐败层）"""

    @abstractmethod
    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        """获取产品信息"""
        pass

    @abstractmethod
    async def check_products_available(
        self, product_ids: list[str]
    ) -> tuple[list[str], list[str]]:
        """检查产品是否可用

        Returns:
            (可用的产品ID列表, 不可用的产品ID列表)
        """
        pass
```

**关键点：**
- 接口定义在 Ordering BC 的 `application/ports/` 中
- 返回的是 Ordering BC 的 `ProductInfo`，不是 Catalog BC 的 `Product`
- 这是依赖倒置原则（DIP）的应用

### 3. 实现反腐败层（Adapter）

```python
# contexts/ordering/infrastructure/services/product_catalog_service.py

class ProductCatalogService(IProductCatalogService):
    """产品目录服务实现（查询 Catalog BC 的只读视图）"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        # 直接查询 ProductPO（持久化对象，而非领域模型）
        stmt = select(ProductPO).where(
            ProductPO.id == product_id,
            ProductPO.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        product_po = result.scalar_one_or_none()

        if not product_po:
            return None

        return self._to_product_info(product_po)

    def _to_product_info(self, product_po: ProductPO) -> ProductInfo:
        """关键转换：ProductPO → ProductInfo"""
        return ProductInfo(
            product_id=product_po.id,
            product_name=product_po.name,
            unit_price=float(product_po.price),
            is_available=not product_po.is_deleted
        )
```

**关键点：**
- 实现在 `infrastructure/services/` 中（适配器层）
- 只读访问 Catalog BC 的数据库表（ProductPO）
- 转换函数 `_to_product_info` 是隔离的关键：
  - 输入：Catalog BC 的持久化对象
  - 输出：Ordering BC 的值对象
  - 如果 Catalog BC 改变，只需修改这个转换函数

### 4. 在用例中使用

```python
# contexts/ordering/application/commands/create_order.py

class CreateOrderUseCase(BaseUseCase[CreateOrderCommand, Order]):
    def __init__(
        self,
        uow: IUnitOfWork,
        product_catalog: IProductCatalogService  # 注入反腐败层
    ):
        super().__init__(uow)
        self._product_catalog = product_catalog

    async def handle(self, command: CreateOrderCommand) -> Order:
        # ✅ 通过反腐败层验证产品
        _, unavailable_ids = await self._product_catalog.check_products_available(
            [item.product_id for item in command.items]
        )

        if unavailable_ids:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"unavailable_products": unavailable_ids}
            )

        # 创建订单...
```

**关键点：**
- 依赖注入 `IProductCatalogService` 接口（而非实现）
- 完全不知道 Catalog BC 的存在
- 测试时可以 Mock `IProductCatalogService`

---

## 🧪 测试策略

### 单元测试（Mock 反腐败层）

```python
@pytest.mark.asyncio
async def test_create_order_product_not_found(usecase, mock_product_catalog):
    """测试产品不存在的场景"""
    command = CreateOrderCommand(
        customer_id="customer-001",
        items=[OrderItemInput(
            product_id="nonexistent-product",
            product_name="Product X",
            quantity=1,
            unit_price=100.0,
        )]
    )

    # Mock 反腐败层返回产品不可用
    mock_product_catalog.check_products_available.return_value = (
        [],  # available
        ["nonexistent-product"],  # unavailable
    )

    # 验证抛出异常
    with pytest.raises(ApplicationException):
        await usecase.execute(command)
```

### 集成测试（真实反腐败层）

```python
@pytest.mark.asyncio
async def test_create_order_integration(session):
    """集成测试：验证跨 BC 的产品查询"""
    # 1. 在 Catalog BC 中创建产品
    product = Product(id="prod-001", name="Product A", price=100.0)
    catalog_repo = ProductRepository(session)
    await catalog_repo.save(product)

    # 2. 在 Ordering BC 中创建订单
    product_catalog = ProductCatalogService(session)  # 真实实现
    ordering_uow = SQLAlchemyUnitOfWork(session)
    usecase = CreateOrderUseCase(ordering_uow, product_catalog)

    command = CreateOrderCommand(
        customer_id="customer-001",
        items=[OrderItemInput(
            product_id="prod-001",
            product_name="Product A",
            quantity=1,
            unit_price=100.0,
        )]
    )

    order = await usecase.execute(command)
    assert order.total == 100.0
```

---

## 🔄 跨 BC 通信的其他方式

### 方式 1: 本地只读副本（当前实现）

```
Ordering BC 查询 → ProductPO (Catalog BC 的表) → ProductInfo
```

**优点：**
- 实时数据，无延迟
- 实现简单（Modular Monolith 适用）

**缺点：**
- 仍然共享数据库
- 微服务迁移时需要重构

### 方式 2: 集成事件同步副本

```
Catalog BC → ProductCreated Event → Ordering BC 监听 → 存储本地副本
```

**优点：**
- 完全解耦，每个 BC 有自己的数据库
- 适合微服务架构

**缺点：**
- 最终一致性（有延迟）
- 需要事件基础设施

### 方式 3: HTTP/gRPC 调用

```
Ordering BC → HTTP Request → Catalog BC API → ProductInfo
```

**优点：**
- 适合微服务
- BC 可以独立部署

**缺点：**
- 网络延迟
- 需要处理服务不可用的情况

---

## 📋 重构 Checklist

当你发现跨 BC 直接依赖时，按以下步骤重构：

- [ ] 识别依赖关系（如：Ordering → Catalog.Product）
- [ ] 在目标 BC 定义值对象（如：ProductInfo）
- [ ] 定义反腐败层接口（如：IProductCatalogService）
- [ ] 实现反腐败层（如：ProductCatalogService）
- [ ] 修改用例使用接口而非直接依赖
- [ ] 更新测试（单元测试 Mock 接口）
- [ ] 添加集成测试验证跨 BC 交互

---

## 🎓 总结

### BC 隔离的价值

1. **独立演化**：Catalog BC 的修改不影响 Ordering BC
2. **清晰边界**：每个 BC 只关注自己的领域模型
3. **可测试性**：通过 Mock 接口轻松测试
4. **可替换性**：未来可以替换为 HTTP 调用或事件驱动

### 记住这个规则

> **BC 之间只能通过以下方式通信：**
> 1. 反腐败层（ACL）
> 2. 集成事件（Integration Events）
> 3. 共享内核（Shared Kernel）
>
> **绝不直接依赖其他 BC 的领域模型！**

---

## 📚 参考资料

- [DDD Reference - Bounded Context](https://www.domainlanguage.com/ddd/)
- [Anti-Corruption Layer Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer)
- [Context Mapping](https://github.com/ddd-crew/context-mapping)
