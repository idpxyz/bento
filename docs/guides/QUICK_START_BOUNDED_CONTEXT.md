# 🚀 Bounded Context 快速开始指南

本指南将引导你使用 Bento Framework CLI 快速创建和开发基于 Bounded Context 的应用。

---

## 📋 前提条件

1. **安装 Bento Framework**
   ```bash
   pip install -e .
   ```

2. **验证安装**
   ```bash
   bento --version
   ```

---

## 🎯 场景示例：电商系统

我们将创建一个电商系统，包含以下 Bounded Context：
- **catalog**: 商品目录管理
- **order**: 订单处理
- **inventory**: 库存管理

---

## 步骤 1：初始化项目

```bash
# 创建项目
bento init my-shop --description "E-commerce platform"

# 进入项目目录
cd my-shop

# 查看项目结构
tree -L 2 contexts/
```

**输出**：
```
contexts/
├── __init__.py
└── shared/
    ├── README.md
    ├── domain/
    └── events/
```

---

## 步骤 2：创建 Bounded Context

### 2.1 创建商品目录上下文

```bash
bento gen context catalog \
  --description "Product catalog and category management"
```

**生成的结构**：
```
contexts/catalog/
├── README.md                           # Context 业务说明
├── domain/                             # 领域层
│   ├── model/                          # 聚合根、实体
│   ├── events/                         # 领域事件
│   ├── services/                       # 领域服务
│   ├── ports/                          # 端口接口
│   └── exceptions.py                   # 领域异常
│
├── application/                        # 应用层（CQRS风格）
│   ├── commands/                       # Command handlers（写操作）
│   ├── queries/                        # Query handlers（读操作）
│   ├── dto/                            # DTO
│   │   ├── requests/                   # 请求 DTO
│   │   └── responses/                  # 响应 DTO
│   ├── services/                       # 应用服务（可选）
│   └── mappers/                        # 映射器
│
├── infrastructure/                     # 基础设施层
│   ├── persistence/                    # 持久化
│   │   ├── models/                     # ORM 模型
│   │   ├── mappers/                    # PO <-> Domain 映射
│   │   └── repositories/               # Repository 实现
│   ├── messaging/                      # 消息传递
│   └── external/                       # 外部服务
│
└── interfaces/                         # 接口层
    ├── api/                            # REST API
    ├── cli/                            # CLI 命令
    └── events/                         # 事件订阅
```

### 2.2 创建订单处理上下文

```bash
bento gen context order \
  --description "Order processing and fulfillment workflow"
```

### 2.3 创建库存管理上下文

```bash
bento gen context inventory \
  --description "Stock and warehouse management"
```

**当前项目结构**：
```
my-shop/
├── contexts/
│   ├── catalog/      ✅ 已创建
│   ├── order/        ✅ 已创建
│   ├── inventory/    ✅ 已创建
│   └── shared/       ✅ 默认存在
│
├── tests/
│   ├── catalog/      ✅ 自动创建
│   ├── order/        ✅ 自动创建
│   └── inventory/    ✅ 自动创建
│
├── main.py
└── config.py
```

---

## 步骤 3：在 Context 中生成模块

### 3.1 生成 Product 模块（catalog 上下文）

```bash
bento gen module Product \
  --context catalog \
  --fields "name:str,sku:str,price:float,stock:int,category_id:str"
```

**生成内容（CQRS 风格）**：
- ✅ `domain/model/product.py` - Product 聚合根
- ✅ `domain/events/product_created_event.py` - ProductCreated 事件
- ✅ `application/commands/create_product.py` - CreateProduct 命令
- ✅ `application/commands/update_product.py` - UpdateProduct 命令
- ✅ `application/commands/delete_product.py` - DeleteProduct 命令
- ✅ `application/queries/get_product.py` - GetProduct 查询
- ✅ `application/queries/list_products.py` - ListProducts 查询
- ✅ `infrastructure/persistence/models/product_po.py` - Product ORM 模型
- ✅ `infrastructure/persistence/mappers/product_mapper.py` - Mapper
- ✅ `infrastructure/persistence/repositories/product_repository.py` - Repository
- ✅ `tests/catalog/unit/domain/test_product.py` - 单元测试
- ✅ `tests/catalog/unit/application/test_create_product.py` - 命令测试
- ✅ `tests/catalog/unit/application/test_get_product.py` - 查询测试
- ✅ `tests/catalog/integration/test_product_repository.py` - 集成测试

### 3.2 生成 Category 模块（catalog 上下文）

```bash
bento gen module Category \
  --context catalog \
  --fields "name:str,description:str,parent_id:str"
```

### 3.3 生成 Order 模块（order 上下文）

```bash
bento gen module Order \
  --context order \
  --fields "customer_id:str,status:str,total:float,items:list"
```

---

## 步骤 4：查看生成的代码

### Product 聚合根示例

```python
# contexts/catalog/domain/model/product.py
from bento.domain.aggregate import AggregateRoot
from dataclasses import dataclass

@dataclass
class Product(AggregateRoot):
    """Product aggregate root"""
    
    name: str
    sku: str
    price: float
    stock: int
    category_id: str
    
    def change_price(self, new_price: float) -> None:
        """修改价格"""
        if new_price <= 0:
            raise ValueError("价格必须大于零")
        
        old_price = self.price
        self.price = new_price
        
        # 记录领域事件
        self.record_event(ProductPriceChanged(
            product_id=self.id,
            old_price=old_price,
            new_price=new_price
        ))
```

### CreateProduct Command 示例

```python
# contexts/catalog/application/commands/create_product.py
from dataclasses import dataclass
from bento.application.cqrs import CommandHandler

@dataclass
class CreateProductCommand:
    """创建商品命令"""
    name: str
    sku: str
    price: float
    stock: int
    category_id: str

class CreateProductHandler(CommandHandler):
    """创建商品处理器"""
    
    async def handle(self, command: CreateProductCommand):
        async with self.uow:
            # 1. 创建领域对象
            product = Product.create(
                name=command.name,
                sku=command.sku,
                price=Money(command.price),
                stock=command.stock,
                category_id=command.category_id
            )
            
            # 2. 保存
            repo = self.uow.repository(Product)
            await repo.save(product)
            
            # 3. 提交（自动发布事件）
            await self.uow.commit()
            
            return self.success(str(product.id))
```

### GetProduct Query 示例

```python
# contexts/catalog/application/queries/get_product.py
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
        """处理查询（只读操作）"""
        async with self.uow:
            repo = self.uow.repository(Product)
            product = await repo.get(ProductId(query.product_id))
            
            if not product:
                raise ProductNotFoundError(query.product_id)
            
            return ProductResponse(
                id=str(product.id),
                name=product.name,
                sku=product.sku,
                price=float(product.price.amount),
                stock=product.stock
            )
```

---

## 步骤 5：集成 Context 到 API

### 5.1 创建 API Router

```python
# contexts/catalog/interfaces/api/router.py
from fastapi import APIRouter, Depends, HTTPException
from contexts.catalog.application.commands.create_product import (
    CreateProductCommand,
    CreateProductHandler
)
from contexts.catalog.application.queries.get_product import (
    GetProductQuery,
    GetProductHandler
)

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

@router.post("/products", status_code=201)
async def create_product(
    command: CreateProductCommand,
    handler: CreateProductHandler = Depends(get_create_product_handler)
):
    """创建商品 (Command)"""
    result = await handler.handle(command)
    if result.is_success:
        return {"product_id": result.value}
    else:
        raise HTTPException(status_code=400, detail=result.error)

@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    handler: GetProductHandler = Depends(get_get_product_handler)
):
    """获取商品 (Query)"""
    query = GetProductQuery(product_id=product_id)
    try:
        return await handler.handle(query)
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### 5.2 注册到主应用

```python
# shared/api/router_registry.py
from fastapi import FastAPI
from contexts.catalog.interfaces.api.router import router as catalog_router
from contexts.order.interfaces.api.router import router as order_router

def register_routers(app: FastAPI):
    """注册所有 Context 的路由"""
    app.include_router(catalog_router)
    app.include_router(order_router)
```

```python
# main.py
from fastapi import FastAPI
from shared.api.router_registry import register_routers

app = FastAPI(title="My Shop")

# 注册路由
register_routers(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 步骤 6：Context 间通信（集成事件）

### 6.1 定义集成事件（shared context）

```python
# contexts/shared/events/order_completed.py
from bento.domain.domain_event import IntegrationEvent
from dataclasses import dataclass

@dataclass
class OrderCompletedEvent(IntegrationEvent):
    """订单完成事件（跨 Context）"""
    order_id: str
    customer_id: str
    items: list[dict]
    total: float
    topic: str = "order.completed"
```

### 6.2 发布事件（order context）

```python
# contexts/order/domain/model/order.py
class Order(AggregateRoot):
    def complete(self) -> None:
        """完成订单"""
        if self.status != "PAID":
            raise InvalidOrderStateError("只有已支付订单可以完成")
        
        self.status = "COMPLETED"
        
        # 发布集成事件
        self.record_event(OrderCompletedEvent(
            order_id=str(self.id),
            customer_id=self.customer_id,
            items=self.items,
            total=self.total
        ))
```

### 6.3 订阅事件（inventory context）

```python
# contexts/inventory/infrastructure/messaging/event_handlers.py
from contexts.shared.events import OrderCompletedEvent

async def handle_order_completed(event: OrderCompletedEvent):
    """处理订单完成事件 - 减少库存"""
    for item in event.items:
        product_id = item['product_id']
        quantity = item['quantity']
        
        # 减少库存
        await inventory_service.decrease_stock(product_id, quantity)
```

---

## 步骤 7：运行测试

### 7.1 运行特定 Context 的测试

```bash
# 测试 catalog context
pytest tests/catalog/ -v

# 测试 order context
pytest tests/order/ -v

# 测试所有 context
pytest tests/ -v
```

### 7.2 查看测试覆盖率

```bash
pytest tests/ --cov=contexts --cov-report=html
open htmlcov/index.html
```

---

## 步骤 8：架构验证

### 8.1 验证整个项目

```bash
bento validate --project-path . --output report.json
```

### 8.2 验证特定 Context

```bash
# 验证 catalog context
bento validate --context catalog

# 验证 order context
bento validate --context order
```

### 8.3 CI/CD 集成

```bash
# 在 CI 中使用，发现违规时失败
bento validate --fail-on-violations
```

---

## 🎨 最佳实践

### 1. **CQRS 模式应用**

✅ **Command（写操作）**：
- 修改系统状态
- 返回操作结果（成功/失败）
- 触发领域事件
- 需要事务保护

```python
# 示例：Command 命名规范
CreateProductCommand       # 创建
UpdateProductCommand       # 更新
DeleteProductCommand       # 删除
PublishProductCommand      # 业务操作
```

✅ **Query（读操作）**：
- 不修改系统状态
- 返回数据（DTO）
- 可以直接查询优化的读模型
- 无需事务

```python
# 示例：Query 命名规范
GetProductQuery           # 获取单个
ListProductsQuery         # 获取列表
SearchProductsQuery       # 搜索
GetProductStatsQuery      # 统计
```

### 2. **从旧结构迁移到 CQRS**

如果你的项目使用旧的 `usecases/` 结构，可以这样迁移：

```bash
# 1. 创建新目录
mkdir -p application/commands
mkdir -p application/queries
mkdir -p application/dto/requests
mkdir -p application/dto/responses

# 2. 迁移文件
# Commands (写操作)
mv application/usecases/create_*.py application/commands/
mv application/usecases/update_*.py application/commands/
mv application/usecases/delete_*.py application/commands/

# Queries (读操作)
mv application/usecases/get_*.py application/queries/
mv application/usecases/list_*.py application/queries/
mv application/usecases/search_*.py application/queries/
mv application/usecases/queries/*.py application/queries/

# 3. 删除旧目录
rm -rf application/usecases/

# 4. 更新导入路径
# 将所有 from ...usecases.create_product import ...
# 改为 from ...commands.create_product import ...
```

### 3. **Context 划分原则**

✅ **按业务能力划分**：
- `catalog`: 商品目录管理
- `order`: 订单处理
- `inventory`: 库存管理
- `payment`: 支付处理

❌ **避免按技术层次划分**：
- ❌ `api-context`
- ❌ `database-context`

### 4. **Context 间通信**

✅ **推荐**：异步集成事件
- 松耦合
- 独立演化
- 易于扩展

❌ **避免**：直接依赖其他 Context 的聚合根
```python
# ❌ 错误
from contexts.catalog.domain.model import Product

class Order(AggregateRoot):
    product: Product  # 跨 Context 依赖

# ✅ 正确
class Order(AggregateRoot):
    product_id: str  # 只保存 ID
    product_snapshot: dict  # 或保存快照
```

### 3. **Shared Context 使用原则**

✅ **适合放入 shared**：
- 通用值对象（Money, Email, Address）
- 集成事件（跨 Context 通信）
- 技术基础设施接口

❌ **不适合放入 shared**：
- 聚合根（应属于特定 Context）
- 业务逻辑（应在具体 Context 中）

### 4. **防腐层（Anti-Corruption Layer）**

当需要调用其他 Context 时，使用防腐层：

```python
# contexts/order/application/adapters/inventory_adapter.py
class InventoryAdapter:
    """库存服务防腐层"""
    
    async def check_stock(self, product_id: str) -> int:
        """检查库存（转换外部模型）"""
        # 调用 inventory context 的 API
        response = await self.inventory_client.get_stock(product_id)
        
        # 转换为本 Context 的模型
        return response['available_quantity']
```

---

## 📚 参考资料

- **目录结构规范**: `/docs/architecture/BOUNDED_CONTEXT_STRUCTURE.md`
- **CLI 使用指南**: `/docs/CLI_USAGE_GUIDE.md`
- **架构验证**: `bento validate --help`
- **测试指南**: `/docs/TESTING_GUIDE.md`

---

## 💡 常见问题

### Q1: 如何判断应该创建新的 Context？

**评估标准**：
1. ✅ 有独立的业务价值
2. ✅ 有清晰的业务边界
3. ✅ 可以独立交付
4. ✅ 有明确的 Ubiquitous Language

### Q2: Context 应该多大？

**经验法则**：
- **团队规模**：3-7 人可维护
- **聚合根数量**：3-10 个
- **代码行数**：5000-20000 行

### Q3: Context 之间如何共享代码？

**分层策略**：
1. **Domain 层**：通过 shared context
2. **Infrastructure 层**：通过共享库（bento framework）
3. **Application 层**：不共享，各 Context 独立

### Q4: 如何重构已有代码到 Context？

**步骤**：
1. 识别业务边界
2. 创建新 Context
3. 逐步迁移聚合根
4. 建立集成事件
5. 并行运行，逐步切换

---

**版本**: 1.0  
**最后更新**: 2025-12-02  
**维护者**: Bento Framework Team
