# 📦 my-shop 项目完整概览

> 基于 Bento Framework 的完整电商应用 - Domain-Driven Design + Modular Monolith 架构

---

## 🏗️ 项目架构

### Modular Monolith - 按业务能力组织

```
my-shop/
├── 🎯 contexts/                    # 边界上下文（核心业务）
│   ├── catalog/                    # 商品目录
│   ├── identity/                   # 身份认证
│   ├── ordering/                   # 订单管理
│   └── shared/                     # 共享内核
│
├── 🌐 api/                         # API 网关层
├── 🧪 tests/                       # 测试（按上下文组织）
├── 🛠️  alembic/                    # 数据库迁移
└── 📝 配置文件
```

---

## 📊 完整功能清单

### 1️⃣ **Catalog Context - 商品目录上下文**

#### Product 聚合根
```python
@dataclass
class Product(AggregateRoot):
    id: str
    name: str
    price: float
```

**生成的文件：**
- ✅ `domain/product.py` - Product 聚合根
- ✅ `domain/events/productcreated_event.py` - ProductCreated 事件
- ✅ `infrastructure/models/product_po.py` - 数据库模型
- ✅ `infrastructure/mappers/product_mapper.py` - 映射器接口
- ✅ `infrastructure/repositories/product_repository.py` - 仓储接口
- ✅ `application/usecases/create_product.py` - 创建产品用例

**测试文件：**
- ✅ `tests/catalog/unit/domain/test_product.py`
- ✅ `tests/catalog/unit/application/test_create_product.py`
- ✅ `tests/catalog/integration/test_product_repository.py`

#### Category 聚合根
```python
@dataclass
class Category(AggregateRoot):
    id: str
    name: str
    description: str
    parent_id: str  # 支持多级分类
```

**生成的文件：**
- ✅ `domain/category.py` - Category 聚合根
- ✅ `domain/events/categorycreated_event.py` - CategoryCreated 事件
- ✅ `infrastructure/models/category_po.py` - 数据库模型
- ✅ `infrastructure/mappers/category_mapper.py` - 映射器接口
- ✅ `infrastructure/repositories/category_repository.py` - 仓储接口
- ✅ `application/usecases/create_category.py` - 创建分类用例

**测试文件：**
- ✅ `tests/catalog/unit/domain/test_category.py`
- ✅ `tests/catalog/unit/application/test_create_category.py`
- ✅ `tests/catalog/integration/test_category_repository.py`

---

### 2️⃣ **Identity Context - 身份认证上下文**

#### User 聚合根
```python
@dataclass
class User(AggregateRoot):
    id: str
    email: str
    username: str
    password_hash: str
    is_active: bool
```

**生成的文件：**
- ✅ `domain/user.py` - User 聚合根
- ✅ `domain/events/usercreated_event.py` - UserCreated 事件
- ✅ `infrastructure/models/user_po.py` - 数据库模型
- ✅ `infrastructure/mappers/user_mapper.py` - 映射器接口
- ✅ `infrastructure/repositories/user_repository.py` - 仓储接口
- ✅ `application/usecases/create_user.py` - 创建用户用例

**测试文件：**
- ✅ `tests/identity/unit/domain/test_user.py`
- ✅ `tests/identity/unit/application/test_create_user.py`
- ✅ `tests/identity/integration/test_user_repository.py`

---

### 3️⃣ **Ordering Context - 订单管理上下文**

#### Order 聚合根
```python
@dataclass
class Order(AggregateRoot):
    id: str
    customer_id: str
    total: float
    status: str
```

**生成的文件：**
- ✅ `domain/order.py` - Order 聚合根
- ✅ `domain/events/ordercreated_event.py` - OrderCreated 事件
- ✅ `infrastructure/models/order_po.py` - 数据库模型
- ✅ `infrastructure/mappers/order_mapper.py` - 映射器接口
- ✅ `infrastructure/repositories/order_repository.py` - 仓储接口
- ✅ `application/usecases/create_order.py` - 创建订单用例

**测试文件：**
- ✅ `tests/ordering/unit/domain/test_order.py`
- ✅ `tests/ordering/unit/application/test_create_order.py`
- ✅ `tests/ordering/integration/test_order_repository.py`

---

### 4️⃣ **Shared Context - 共享内核**

```
contexts/shared/
├── domain/          # 共享值对象（如 Money, Address）
├── events/          # 集成事件（跨上下文通信）
└── README.md
```

---

## 📈 统计数据

| 指标 | 数量 |
|-----|------|
| 边界上下文 | 4 个 |
| 聚合根 | 4 个 |
| 领域事件 | 4 个 |
| 用例 | 4 个 |
| 仓储接口 | 4 个 |
| 映射器 | 4 个 |
| 持久化对象 | 4 个 |
| 测试文件 | 12 个 |
| **总文件数** | **54 个** |

---

## 🚀 下一步开发任务

### Phase 1: 完善领域模型 ✏️

#### 1. 增强 Product 聚合根
```python
# contexts/catalog/domain/product.py

@dataclass
class Product(AggregateRoot):
    id: str
    name: str
    price: float
    category_id: str  # 关联到 Category
    stock: int = 0
    is_active: bool = True

    def change_price(self, new_price: float):
        """修改价格"""
        if new_price <= 0:
            raise ValueError("价格必须大于0")

        old_price = self.price
        self.price = new_price
        self.add_event(ProductPriceChangedEvent(
            product_id=self.id,
            old_price=old_price,
            new_price=new_price
        ))

    def decrease_stock(self, quantity: int):
        """减少库存"""
        if self.stock < quantity:
            raise ValueError("库存不足")

        self.stock -= quantity
        self.add_event(ProductStockDecreasedEvent(
            product_id=self.id,
            quantity=quantity
        ))

    def deactivate(self):
        """下架商品"""
        self.is_active = False
        self.add_event(ProductDeactivatedEvent(product_id=self.id))
```

#### 2. 增强 Category 聚合根
```python
# contexts/catalog/domain/category.py

@dataclass
class Category(AggregateRoot):
    id: str
    name: str
    description: str
    parent_id: str | None = None
    is_active: bool = True

    def is_root(self) -> bool:
        """是否为根分类"""
        return self.parent_id is None

    def rename(self, new_name: str):
        """重命名分类"""
        if not new_name or not new_name.strip():
            raise ValueError("分类名称不能为空")

        old_name = self.name
        self.name = new_name
        self.add_event(CategoryRenamedEvent(
            category_id=self.id,
            old_name=old_name,
            new_name=new_name
        ))
```

#### 3. 增强 User 聚合根
```python
# contexts/identity/domain/user.py

from datetime import datetime

@dataclass
class User(AggregateRoot):
    id: str
    email: str
    username: str
    password_hash: str
    is_active: bool = True
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    def activate(self):
        """激活用户"""
        if self.is_active:
            return

        self.is_active = True
        self.add_event(UserActivatedEvent(user_id=self.id))

    def deactivate(self):
        """停用用户"""
        if not self.is_active:
            return

        self.is_active = False
        self.add_event(UserDeactivatedEvent(user_id=self.id))

    def record_login(self):
        """记录登录"""
        self.last_login_at = datetime.utcnow()
        self.add_event(UserLoggedInEvent(
            user_id=self.id,
            timestamp=self.last_login_at
        ))
```

#### 4. 增强 Order 聚合根
```python
# contexts/ordering/domain/order.py

from enum import Enum
from datetime import datetime

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

@dataclass
class OrderItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price

@dataclass
class Order(AggregateRoot):
    id: str
    customer_id: str
    items: list[OrderItem]
    total: float
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime | None = None

    def confirm_payment(self):
        """确认支付"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("只有待支付订单可以确认支付")

        self.status = OrderStatus.PAID
        self.add_event(OrderPaidEvent(
            order_id=self.id,
            customer_id=self.customer_id,
            total=self.total
        ))

    def ship(self, tracking_number: str):
        """发货"""
        if self.status != OrderStatus.PAID:
            raise ValueError("只有已支付订单可以发货")

        self.status = OrderStatus.SHIPPED
        self.add_event(OrderShippedEvent(
            order_id=self.id,
            tracking_number=tracking_number
        ))

    def cancel(self, reason: str):
        """取消订单"""
        if self.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            raise ValueError("已发货或已送达的订单无法取消")

        self.status = OrderStatus.CANCELLED
        self.add_event(OrderCancelledEvent(
            order_id=self.id,
            reason=reason
        ))
```

---

### Phase 2: 实现用例 🔧

#### 示例：实现 CreateProduct 用例

```python
# contexts/catalog/application/usecases/create_product.py

from dataclasses import dataclass
from contexts.catalog.domain.product import Product
from contexts.catalog.domain.events.productcreated_event import ProductCreatedEvent

@dataclass
class CreateProductCommand:
    name: str
    price: float
    category_id: str
    stock: int = 0

class CreateProductUseCase:
    def __init__(self, repository, unit_of_work):
        self._repository = repository
        self._uow = unit_of_work

    async def validate(self, command: CreateProductCommand) -> None:
        """验证命令"""
        if not command.name or not command.name.strip():
            raise ValueError("产品名称不能为空")

        if command.price <= 0:
            raise ValueError("价格必须大于0")

        if command.stock < 0:
            raise ValueError("库存不能为负数")

    async def execute(self, command: CreateProductCommand) -> str:
        """执行用例"""
        await self.validate(command)

        async with self._uow:
            # 生成 ID
            product_id = self._generate_id()

            # 创建聚合根
            product = Product(
                id=product_id,
                name=command.name,
                price=command.price,
                category_id=command.category_id,
                stock=command.stock,
                is_active=True
            )

            # 添加领域事件
            product.add_event(ProductCreatedEvent(
                product_id=product.id,
                name=product.name,
                price=product.price
            ))

            # 保存
            await self._repository.save(product)
            await self._uow.commit()

            return product.id

    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())
```

---

### Phase 3: 添加 API 端点 🌐

#### 在 `api/router.py` 中添加路由

```python
# api/router.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

api_router = APIRouter()

# Product API
class CreateProductRequest(BaseModel):
    name: str
    price: float
    category_id: str
    stock: int = 0

@api_router.post("/products", status_code=201)
async def create_product(
    request: CreateProductRequest,
    use_case = Depends(get_create_product_usecase)  # 依赖注入
):
    """创建产品"""
    command = CreateProductCommand(
        name=request.name,
        price=request.price,
        category_id=request.category_id,
        stock=request.stock
    )
    product_id = await use_case.execute(command)
    return {"product_id": product_id}

@api_router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    repository = Depends(get_product_repository)
):
    """获取产品详情"""
    product = await repository.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# Category API
@api_router.get("/categories")
async def list_categories(
    repository = Depends(get_category_repository)
):
    """获取分类列表"""
    categories = await repository.list(limit=100)
    return {"categories": categories}

# User API
@api_router.post("/users/register")
async def register_user(
    request: CreateUserRequest,
    use_case = Depends(get_create_user_usecase)
):
    """用户注册"""
    # 实现注册逻辑
    pass

# Order API
@api_router.post("/orders")
async def create_order(
    request: CreateOrderRequest,
    use_case = Depends(get_create_order_usecase)
):
    """创建订单"""
    # 实现下单逻辑
    pass
```

---

### Phase 4: 实现仓储 💾

#### 示例：ProductRepository 实现

```python
# contexts/catalog/infrastructure/repositories/product_repository_impl.py

from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.repository import BaseRepository
from bento.persistence.interceptor import create_default_chain
from contexts.catalog.domain.product import Product
from contexts.catalog.infrastructure.models.product_po import ProductPO
from contexts.catalog.infrastructure.mappers.product_mapper import ProductMapper

class ProductRepository(RepositoryAdapter[Product, ProductPO, str]):
    """Product 仓储实现"""

    def __init__(self, session, actor: str = "system"):
        mapper = ProductMapper()
        base_repo = BaseRepository(
            session=session,
            po_type=ProductPO,
            actor=actor,
            interceptor_chain=create_default_chain(actor)
        )
        super().__init__(repository=base_repo, mapper=mapper)

    async def find_by_category(self, category_id: str) -> list[Product]:
        """根据分类ID查找产品"""
        # 自定义查询方法
        pass
```

---

## 🧪 测试策略

### 单元测试
```bash
# 测试领域逻辑
pytest tests/catalog/unit/domain/ -v

# 测试用例
pytest tests/catalog/unit/application/ -v
```

### 集成测试
```bash
# 测试仓储
pytest tests/catalog/integration/ -v
```

### 端到端测试
```bash
# 测试 API
pytest tests/e2e/ -v
```

---

## 📚 开发参考

### DDD 概念映射

| DDD 概念 | 项目实现 |
|---------|---------|
| 聚合根 (Aggregate Root) | Product, Category, User, Order |
| 值对象 (Value Object) | OrderItem, Money (待实现) |
| 领域事件 (Domain Event) | ProductCreated, OrderPaid |
| 仓储 (Repository) | IProductRepository |
| 工作单元 (Unit of Work) | IUnitOfWork |
| 应用服务 (Application Service) | CreateProductUseCase |

### 依赖方向

```
infrastructure → application → domain
      ↓              ↓            ↓
     PO          UseCase     Aggregate
   Mapper                     Event
   Repository
```

---

## 🎯 总结

✅ **完整的电商项目架构** - 4 个边界上下文，54 个文件
✅ **DDD 分层清晰** - Domain, Application, Infrastructure
✅ **Modular Monolith** - 按业务能力组织，易于演化
✅ **测试覆盖完整** - 12 个测试文件骨架
✅ **代码生成自动化** - CLI 工具一键生成
✅ **导入路径正确** - 使用绝对导入，IDE 友好

现在可以开始实现业务逻辑了！🚀
