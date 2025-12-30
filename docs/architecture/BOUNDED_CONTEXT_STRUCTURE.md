# 📐 Bounded Context 目录结构规范

## 概述

Bento Framework 采用 **Modular Monolith** 架构，以 **Bounded Context（限界上下文）** 为核心组织单元。每个 Bounded Context 代表一个业务子域，拥有独立的领域模型、应用逻辑和基础设施实现。

## 设计原则

### 1. **领域驱动 (Domain-Driven)**
- 按业务能力划分，而非技术层次
- 每个 Context 有明确的业务边界
- Context 之间通过集成事件通信

### 2. **高内聚低耦合 (High Cohesion, Low Coupling)**
- Context 内部高度内聚
- Context 之间通过定义良好的接口交互
- 避免跨 Context 直接依赖领域模型

### 3. **独立演化 (Independent Evolution)**
- 每个 Context 可独立开发、测试、部署
- 技术栈可按 Context 差异化选择
- 团队可按 Context 分工

---

## 标准目录结构

### 项目根目录

```
my-shop/                          # 项目根目录
├── contexts/                     # 所有限界上下文
│   ├── __init__.py              # Contexts 包初始化
│   ├── shared/                  # 共享内核
│   ├── catalog/                 # 商品目录上下文
│   ├── inventory/               # 库存管理上下文
│   ├── order/                   # 订单处理上下文
│   └── identity/                # 身份认证上下文
│
├── shared/                       # 跨 Context 共享
│   ├── api/                     # 统一 API 层
│   ├── config/                  # 全局配置
│   └── infrastructure/          # 共享基础设施
│
├── tests/                        # 测试（按 Context 组织）
│   ├── catalog/
│   ├── inventory/
│   └── integration/             # 跨 Context 集成测试
│
├── alembic/                      # 数据库迁移
├── main.py                       # 应用入口
├── config.py                     # 配置加载
└── pyproject.toml               # 项目配置
```

---

## Bounded Context 内部结构

每个 Bounded Context 遵循严格的分层架构：

```
contexts/catalog/                           # 商品目录上下文
│
├── __init__.py                            # Context 包初始化
├── README.md                              # Context 业务说明
│
├── domain/                                # 🔵 领域层（核心）
│   ├── __init__.py
│   ├── model/                             # 领域模型
│   │   ├── __init__.py
│   │   ├── product.py                     # 聚合根：Product
│   │   ├── category.py                    # 聚合根：Category
│   │   └── specification/                 # 领域规约
│   │       ├── __init__.py
│   │       └── product_specification.py
│   │
│   ├── events/                            # 领域事件
│   │   ├── __init__.py
│   │   ├── product_created.py
│   │   └── product_updated.py
│   │
│   ├── services/                          # 领域服务
│   │   ├── __init__.py
│   │   └── pricing_service.py
│   │
│   ├── ports/                             # 端口（接口）
│   │   ├── __init__.py
│   │   ├── repository.py                  # Repository 接口
│   │   └── external_service.py            # 外部服务接口
│   │
│   └── exceptions.py                      # 领域异常
│
├── application/                           # 🟢 应用层（CQRS风格）
│   ├── __init__.py
│   ├── commands/                          # Command handlers（写操作）
│   │   ├── __init__.py
│   │   ├── create_product.py
│   │   ├── update_product.py
│   │   ├── delete_product.py
│   │   ├── create_category.py
│   │   └── update_category.py
│   │
│   ├── queries/                           # Query handlers（读操作）
│   │   ├── __init__.py
│   │   ├── get_product.py
│   │   ├── list_products.py
│   │   ├── get_category.py
│   │   └── list_categories.py
│   │
│   ├── dto/                               # 数据传输对象
│   │   ├── __init__.py
│   │   ├── requests/                      # 请求 DTO
│   │   │   ├── __init__.py
│   │   │   ├── create_product_request.py
│   │   │   └── update_product_request.py
│   │   └── responses/                     # 响应 DTO
│   │       ├── __init__.py
│   │       ├── product_response.py
│   │       └── category_response.py
│   │
│   ├── services/                          # 应用服务（可选，复杂编排）
│   │   ├── __init__.py
│   │   ├── product_service.py
│   │   └── category_service.py
│   │
│   └── mappers/                           # DTO <-> Domain 映射
│       ├── __init__.py
│       └── product_mapper.py
│
├── infrastructure/                        # 🟠 基础设施层（技术实现）
│   ├── __init__.py
│   ├── persistence/                       # 持久化
│   │   ├── __init__.py
│   │   ├── models/                        # ORM 模型（PO）
│   │   │   ├── __init__.py
│   │   │   ├── product_po.py
│   │   │   └── category_po.py
│   │   │
│   │   ├── mappers/                       # PO <-> Domain 映射
│   │   │   ├── __init__.py
│   │   │   ├── product_mapper.py
│   │   │   └── category_mapper.py
│   │   │
│   │   └── repositories/                  # Repository 实现
│   │       ├── __init__.py
│   │       ├── product_repository.py
│   │       └── category_repository.py
│   │
│   ├── messaging/                         # 消息传递
│   │   ├── __init__.py
│   │   └── event_handlers.py             # 事件处理器
│   │
│   └── external/                          # 外部服务适配器
│       ├── __init__.py
│       └── payment_client.py
│
└── interfaces/                            # 🔴 接口层（驱动适配器）
    ├── __init__.py
    ├── api/                               # REST API
    │   ├── __init__.py
    │   ├── router.py                      # FastAPI 路由
    │   └── schemas.py                     # API Schema（Pydantic）
    │
    ├── cli/                               # CLI 命令
    │   ├── __init__.py
    │   └── commands.py
    │
    └── events/                            # 事件订阅
        ├── __init__.py
        └── subscribers.py
```

---

## 分层职责说明

### 🔵 **Domain Layer（领域层）**

**职责**：业务逻辑的核心，包含聚合根、实体、值对象、领域事件和领域服务。

**依赖规则**：
- ✅ **无外部依赖**：不依赖任何外部框架或技术实现
- ✅ **纯业务逻辑**：只包含业务规则和不变量
- ❌ **禁止依赖**：Application、Infrastructure、Interfaces 层

**包含内容**：
- **model/**: 聚合根、实体、值对象
- **events/**: 领域事件（DomainEvent）
- **services/**: 领域服务（跨聚合的业务逻辑）
- **ports/**: 端口接口（Repository Protocol）
- **exceptions.py**: 领域异常

**示例**：
```python
# domain/model/product.py
class Product(AggregateRoot):
    """商品聚合根"""
    
    def change_price(self, new_price: Money) -> None:
        """修改价格（业务规则验证）"""
        if new_price.amount <= 0:
            raise InvalidPriceError("价格必须大于零")
        
        old_price = self.price
        self.price = new_price
        
        # 记录领域事件
        self.record_event(ProductPriceChanged(
            product_id=self.id,
            old_price=old_price,
            new_price=new_price
        ))
```

---

### 🟢 **Application Layer（应用层）**

**职责**：用例编排、事务管理、DTO 转换。采用 **CQRS（命令查询职责分离）** 模式。

**依赖规则**：
- ✅ **可依赖**：Domain 层（通过 Ports）
- ❌ **不依赖**：Infrastructure、Interfaces 层的具体实现

**包含内容**：
- **commands/**: Command handlers（写操作：Create/Update/Delete）
- **queries/**: Query handlers（读操作：Get/List）
- **dto/**: 数据传输对象
  - **requests/**: 请求 DTO
  - **responses/**: 响应 DTO
- **services/**: 应用服务（可选，用于复杂编排）
- **mappers/**: DTO <-> Domain 映射

**示例（Command）**：
```python
# application/commands/create_product.py
from dataclasses import dataclass
from bento.application.cqrs import CommandHandler

@dataclass
class CreateProductCommand:
    """创建商品命令"""
    name: str
    sku: str
    price: float
    stock: int

class CreateProductHandler(CommandHandler):
    """创建商品处理器"""
    
    async def handle(
        self, 
        command: CreateProductCommand
    ) -> ApplicationServiceResult[str]:
        """处理创建商品命令"""
        async with self.uow:
            # 1. 创建聚合根
            product = Product.create(
                name=command.name,
                sku=command.sku,
                price=Money(command.price),
                stock=command.stock
            )
            
            # 2. 保存
            repo = self.uow.repository(Product)
            await repo.save(product)
            
            # 3. 提交事务（自动发布事件）
            await self.uow.commit()
            
            return self.success(str(product.id))
```

**示例（Query）**：
```python
# application/queries/get_product.py
from dataclasses import dataclass

@dataclass
class GetProductQuery:
    """获取商品查询"""
    product_id: str

class GetProductHandler:
    """获取商品处理器"""
    
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
    
    async def handle(self, query: GetProductQuery) -> ProductResponse:
        """处理获取商品查询"""
        async with self.uow:
            repo = self.uow.repository(Product)
            product = await repo.get(ProductId(query.product_id))
            
            if not product:
                raise ProductNotFoundError(query.product_id)
            
            return ProductResponse.from_domain(product)
```

---

### 🟠 **Infrastructure Layer（基础设施层）**

**职责**：技术实现细节（数据库、消息队列、外部服务）。

**依赖规则**：
- ✅ **实现 Domain 的 Ports**
- ✅ **可依赖**：Domain、Application 层
- ✅ **使用技术框架**：SQLAlchemy、Redis、HTTP Client 等

**包含内容**：
- **persistence/**: 持久化（ORM 模型、Repository 实现、Mapper）
- **messaging/**: 消息传递（EventBus 实现、事件处理器）
- **external/**: 外部服务适配器（HTTP Client、三方 API）

**示例**：
```python
# infrastructure/persistence/repositories/product_repository.py
class ProductRepositoryImpl(RepositoryAdapter[Product, ProductPO, str]):
    """商品仓储实现（六边形架构的适配器）"""
    
    def __init__(self, session: AsyncSession):
        mapper = ProductMapper()
        base_repo = BaseRepository(session, ProductPO)
        super().__init__(base_repo, mapper)
```

---

### 🔴 **Interfaces Layer（接口层）**

**职责**：驱动适配器，外部世界与应用的桥梁。

**依赖规则**：
- ✅ **可依赖**：Application 层（调用 ApplicationService）
- ❌ **不直接依赖**：Domain、Infrastructure 层

**包含内容**：
- **api/**: REST API（FastAPI Router）
- **cli/**: 命令行接口
- **events/**: 事件订阅（消息队列消费者）

**示例**：
```python
# interfaces/api/router.py
router = APIRouter(prefix="/products", tags=["products"])

@router.post("/", response_model=ProductResponse)
async def create_product(
    request: CreateProductRequest,
    service: ProductApplicationService = Depends(get_product_service)
):
    """创建商品 API"""
    command = CreateProductCommand(**request.dict())
    result = await service.create_product(command)
    
    if result.is_success:
        return ProductResponse.from_dto(result.value)
    else:
        raise HTTPException(status_code=400, detail=result.error)
```

---

## Shared Context（共享内核）

**用途**：多个 Context 共享的领域概念。

**包含内容**：
- **domain/**: 共享的值对象（Money、Address 等）
- **events/**: 集成事件（跨 Context 通信）

**原则**：
- ✅ 只共享**稳定**且**通用**的概念
- ❌ 避免共享聚合根
- ⚠️ 谨慎使用，防止耦合

```
contexts/shared/
├── domain/
│   ├── value_objects/
│   │   ├── money.py          # 货币值对象
│   │   └── address.py        # 地址值对象
│   └── primitives/
│       └── entity_id.py      # 实体ID基类
│
└── events/
    ├── order_completed.py    # 集成事件：订单完成
    └── payment_received.py   # 集成事件：支付收到
```

---

## Context 之间的通信

### 1. **集成事件（Integration Events）**

**推荐方式**：异步、松耦合

```python
# contexts/order/domain/events/order_completed.py
@dataclass
class OrderCompletedEvent(IntegrationEvent):
    """订单完成事件（跨 Context）"""
    order_id: str
    customer_id: str
    total_amount: float
    topic: str = "order.completed"

# contexts/inventory/infrastructure/messaging/event_handlers.py
async def handle_order_completed(event: OrderCompletedEvent):
    """库存 Context 监听订单完成事件"""
    # 减少库存
    ...
```

### 2. **防腐层（Anti-Corruption Layer）**

**用途**：保护本 Context 不被外部模型污染

```python
# contexts/catalog/application/adapters/inventory_adapter.py
class InventoryAdapter:
    """库存服务防腐层"""
    
    async def get_stock(self, product_id: str) -> int:
        """获取库存（转换外部模型）"""
        external_stock = await self.inventory_client.get_stock(product_id)
        # 转换为本 Context 的模型
        return external_stock.available_quantity
```

### 3. **禁止直接依赖**

❌ **错误做法**：
```python
# contexts/order/domain/model/order.py
from contexts.catalog.domain.model import Product  # ❌ 跨 Context 依赖

class Order(AggregateRoot):
    product: Product  # ❌ 直接使用其他 Context 的聚合根
```

✅ **正确做法**：
```python
# contexts/order/domain/model/order.py
class Order(AggregateRoot):
    product_id: str  # ✅ 只保存 ID
    product_name: str  # ✅ 或保存快照数据
```

---

## CLI 使用指南

### 初始化项目

```bash
bento init my-shop --description "电商平台"
cd my-shop
```

### 创建 Bounded Context

```bash
# 创建商品目录上下文
bento gen context catalog --description "商品目录管理"

# 创建订单处理上下文
bento gen context order --description "订单处理流程"
```

### 在 Context 中生成模块

```bash
# 在 catalog 上下文中生成 Product 模块（CQRS 风格）
bento gen module Product \
  --context catalog \
  --fields "name:str,sku:str,price:float,stock:int"

# 生成内容：
# ✅ domain/model/product.py - Product 聚合根
# ✅ domain/events/product_created_event.py - 领域事件
# ✅ application/commands/create_product.py - Create命令
# ✅ application/commands/update_product.py - Update命令
# ✅ application/commands/delete_product.py - Delete命令
# ✅ application/queries/get_product.py - Get查询
# ✅ application/queries/list_products.py - List查询
# ✅ infrastructure/persistence/models/product_po.py - ORM模型
# ✅ infrastructure/persistence/mappers/product_mapper.py - Mapper
# ✅ infrastructure/persistence/repositories/product_repository.py - Repository

# 在 order 上下文中生成 Order 模块
bento gen module Order \
  --context order \
  --fields "customer_id:str,status:str,total:float"
```

---

## 最佳实践

### 1. **Context 划分原则**

✅ **按业务能力划分**：
- `catalog`: 商品目录管理
- `inventory`: 库存管理
- `order`: 订单处理
- `payment`: 支付处理
- `identity`: 用户身份

❌ **避免按技术层次划分**：
- ❌ `api-context`
- ❌ `database-context`

### 2. **Context 大小**

- **单个团队可维护**：3-7人
- **聚合根数量**：3-10个
- **代码行数**：5000-20000行

### 3. **Context 边界验证**

问自己：
1. ✅ 这个 Context 有明确的业务价值吗？
2. ✅ 它能独立交付吗？
3. ✅ 不同团队能并行开发吗？
4. ✅ 它有明确的 Ubiquitous Language（通用语言）吗？

### 4. **依赖检查**

使用 Bento 架构验证工具：

```bash
# 检查整个项目
bento validate --project-path .

# 检查特定 Context
bento validate --context catalog

# 生成报告
bento validate --output report.json --fail-on-violations
```

---

## 参考资料

- **Domain-Driven Design**: Eric Evans
- **Implementing Domain-Driven Design**: Vaughn Vernon
- **Modular Monolith Architecture**: Kamil Grzybek
- **Bento Framework 文档**: `/docs/architecture/`

---

## 附录：快速参考

### Context 创建 Checklist

- [ ] 定义 Context 业务边界
- [ ] 创建 README.md 说明业务价值
- [ ] 定义 Ubiquitous Language
- [ ] 识别核心聚合根
- [ ] 设计集成事件
- [ ] 定义防腐层（如需要）
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 更新架构文档

### 文件命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 聚合根 | PascalCase | `Product`, `Order` |
| 实体 | PascalCase | `OrderLine`, `Address` |
| 值对象 | PascalCase | `Money`, `Email` |
| 领域事件 | PascalCase + Event | `ProductCreatedEvent` |
| DTO | PascalCase + DTO | `ProductDTO`, `CreateProductRequest` |
| PO | PascalCase + PO | `ProductPO` |
| Repository | PascalCase + Repository | `ProductRepository` |
| Service | PascalCase + Service | `ProductApplicationService` |

---

**版本**: 1.0  
**最后更新**: 2025-12-02  
**维护者**: Bento Framework Team
