# E-commerce Application Architecture

本文档详细说明了电商应用的架构设计和实现细节。

## 📋 **目录**

- [架构概述](#架构概述)
- [分层架构](#分层架构)
- [Order 模块详解](#order-模块详解)
- [依赖注入](#依赖注入)
- [事件流程](#事件流程)
- [数据流](#数据流)

## 🏗️ **架构概述**

### Hexagonal Architecture (六边形架构)

```
                    ┌─────────────────────────┐
                    │   Interfaces Layer      │
                    │   (FastAPI Routes)      │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Application Layer      │
                    │  (Use Cases/Commands)   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │    Domain Layer         │
                    │  (Aggregates/Events)    │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   Adapters Layer        │
                    │   (Repositories)        │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Infrastructure         │
                    │  (Database/Cache)       │
                    └─────────────────────────┘
```

### 核心原则

1. **依赖反转**: 所有依赖都指向内层（Domain）
2. **端口与适配器**: 使用接口（Ports）隔离实现（Adapters）
3. **单一职责**: 每层只负责特定职责
4. **关注点分离**: 业务逻辑与技术细节分离

## 📚 **分层架构**

### 1. Domain Layer (领域层)

**职责**: 核心业务逻辑和规则

**包含**:
- **Aggregates (聚合根)**: `Order`
- **Entities (实体)**: `OrderItem`
- **Value Objects (值对象)**: `OrderStatus`
- **Domain Events (领域事件)**: `OrderCreated`, `OrderPaid`, `OrderCancelled`

**特点**:
- ✅ 纯业务逻辑，不依赖外部技术
- ✅ 不可变性和封装性
- ✅ 丰富的行为模型

**示例**:

```python
class Order(AggregateRoot):
    """订单聚合根"""
    
    def pay(self) -> None:
        """支付订单（业务规则）"""
        # 规则1: 订单必须有商品
        if not self.items:
            raise DomainException(OrderErrors.EMPTY_ORDER_ITEMS)
        
        # 规则2: 不能重复支付
        if self.status == OrderStatus.PAID:
            raise DomainException(OrderErrors.ORDER_ALREADY_PAID)
        
        # 状态变更
        self.status = OrderStatus.PAID
        self.paid_at = datetime.now()
        
        # 发布事件
        self.add_event(OrderPaid(...))
```

### 2. Application Layer (应用层)

**职责**: 协调业务流程（Use Cases）

**包含**:
- **Commands (命令)**: `CreateOrderCommand`, `PayOrderCommand`
- **Queries (查询)**: `GetOrderQuery`
- **Use Cases (用例)**: `CreateOrderUseCase`, `PayOrderUseCase`
- **DTOs (数据传输对象)**: `OrderItemDTO`

**特点**:
- ✅ 薄层，主要是编排
- ✅ 事务边界
- ✅ CQRS 模式

**示例**:

```python
class PayOrderUseCase:
    """支付订单用例"""
    
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
    
    async def execute(self, command: PayOrderCommand):
        async with self.uow:
            # 1. 加载聚合
            order = await self.uow.repository(Order).find_by_id(...)
            
            # 2. 执行业务逻辑
            order.pay()
            
            # 3. 保存变更
            await self.uow.repository(Order).update(order)
            
            # 4. 提交事务（自动发布事件）
            await self.uow.commit()
```

### 3. Adapters Layer (适配器层)

**职责**: 实现技术细节

**包含**:
- **Repositories (仓储)**: `OrderRepository`
- **Mappers (映射器)**: AR ↔ PO 转换
- **External Services (外部服务)**: 第三方 API

**特点**:
- ✅ 实现 Domain 定义的接口
- ✅ 隔离技术实现
- ✅ 可替换

**示例**:

```python
class OrderRepository(SimpleRepositoryAdapter[Order]):
    """订单仓储实现"""
    
    async def find_by_customer_id(self, customer_id: ID) -> list[Order]:
        """根据客户ID查询订单"""
        spec = Criteria.eq("customer_id", customer_id.value)
        return await self.find_by_specification(spec)
```

### 4. Interfaces Layer (接口层)

**职责**: 暴露应用功能

**包含**:
- **API Routes (路由)**: FastAPI endpoints
- **Request/Response Models (请求/响应模型)**
- **Dependency Injection (依赖注入)**

**特点**:
- ✅ RESTful API
- ✅ 自动文档（Swagger）
- ✅ 统一异常处理

**示例**:

```python
@router.post("/api/orders/{order_id}/pay")
async def pay_order(
    order_id: str,
    use_case: PayOrderUseCase = Depends(get_pay_order_use_case),
):
    """支付订单 API"""
    command = PayOrderCommand(order_id=order_id)
    order = await use_case.execute(command)
    return order
```

## 🎯 **Order 模块详解**

### 聚合设计

```
Order (Aggregate Root)
├── id: ID
├── customer_id: ID
├── status: OrderStatus
├── items: list[OrderItem]  ← 实体集合
├── created_at: datetime
├── paid_at: datetime | None
└── cancelled_at: datetime | None

OrderItem (Entity)
├── id: ID
├── product_id: ID
├── product_name: str
├── quantity: int
└── unit_price: float
```

### 业务规则

1. **创建订单**:
   - ✅ 必须有客户ID
   - ✅ 至少包含一个商品
   - ✅ 商品数量和价格必须为正数

2. **支付订单**:
   - ✅ 订单必须有商品
   - ✅ 只能支付 PENDING 状态的订单
   - ✅ 不能重复支付

3. **取消订单**:
   - ✅ 只能取消 PENDING 状态的订单
   - ✅ 已支付的订单需要申请退款
   - ✅ 不能重复取消

### 状态转换

```
PENDING ──pay()──> PAID ──ship()──> SHIPPED ──deliver()──> DELIVERED
   │                 │                                         │
   │                 │                                         │
cancel()          refund()                                 refund()
   │                 │                                         │
   ▼                 ▼                                         ▼
CANCELLED         REFUNDED                                REFUNDED
```

### 领域事件

| 事件 | 触发时机 | 包含数据 |
|------|---------|---------|
| `OrderCreated` | 订单创建时 | `order_id`, `customer_id`, `total_amount` |
| `OrderPaid` | 订单支付时 | `order_id`, `customer_id`, `total_amount`, `paid_at` |
| `OrderCancelled` | 订单取消时 | `order_id`, `customer_id`, `reason` |

## 🔌 **依赖注入**

### Composition Root

```python
# runtime/composition.py

def create_order_repository(session: AsyncSession) -> OrderRepository:
    """创建订单仓储"""
    return OrderRepository(session)

async def get_unit_of_work() -> IUnitOfWork:
    """获取工作单元"""
    session = async_session_factory()
    outbox_repo = OutboxRepository(session)
    
    def repository_factory(aggregate_class):
        if aggregate_class == Order:
            return create_order_repository(session)
        raise ValueError(f"No repository for {aggregate_class}")
    
    return UnitOfWork(session, outbox_repo, repository_factory)
```

### FastAPI 依赖

```python
# interfaces/order_api.py

async def get_create_order_use_case() -> CreateOrderUseCase:
    """获取创建订单用例"""
    uow = await get_unit_of_work()
    return CreateOrderUseCase(uow)

@router.post("")
async def create_order(
    request: CreateOrderRequest,
    use_case: CreateOrderUseCase = Depends(get_create_order_use_case),
):
    """创建订单 API"""
    ...
```

## 📊 **事件流程**

### 订单支付流程

```
1. Client
   │
   │ POST /api/orders/{id}/pay
   │
   ▼
2. order_api.py (Interfaces)
   │
   │ PayOrderCommand
   │
   ▼
3. PayOrderUseCase (Application)
   │
   │ async with uow:
   │     order = await repo.find_by_id(...)
   │     order.pay()  ← 触发领域逻辑
   │     await repo.update(order)
   │     await uow.commit()  ← 保存 + 发布事件
   │
   ▼
4. Order.pay() (Domain)
   │
   │ 1. 检查业务规则
   │ 2. 修改状态
   │ 3. 添加事件: self.add_event(OrderPaid(...))
   │
   ▼
5. UnitOfWork.commit()
   │
   │ 1. 保存 Order 到数据库
   │ 2. 保存 Event 到 Outbox 表
   │ 3. 提交事务
   │
   ▼
6. OutboxPublisher (后台任务)
   │
   │ 1. 轮询 Outbox 表
   │ 2. 发布事件到消息总线
   │ 3. 标记为已发布
   │
   ▼
7. Event Handlers
   │
   │ 处理 OrderPaid 事件:
   │ - 发送支付通知邮件
   │ - 更新库存
   │ - 触发发货流程
   │ - ...
```

## 💾 **数据流**

### 写操作（Command）

```
Request (JSON)
    ↓
Request Model (Pydantic)
    ↓
Command (DTO)
    ↓
Use Case
    ↓
Aggregate Root (Domain Model)
    ↓
Repository
    ↓
PO (Persistent Object) - SQLAlchemy Model
    ↓
Database
```

### 读操作（Query）

```
Request
    ↓
Query (DTO)
    ↓
Use Case
    ↓
Repository
    ↓
Aggregate Root
    ↓
to_dict()
    ↓
Response (JSON)
```

## 🔐 **安全性**

### 1. 输入验证

```python
# Pydantic 模型自动验证
class CreateOrderRequest(BaseModel):
    customer_id: str
    items: list[OrderItemRequest]
    
# Domain 层二次验证
if quantity <= 0:
    raise DomainException(OrderErrors.INVALID_QUANTITY)
```

### 2. 异常处理

```python
# 统一异常处理器
@app.exception_handler(BentoException)
async def handle_bento_exception(request, exc):
    return JSONResponse(
        status_code=exc.error_code.http_status,
        content=exc.to_dict()
    )
```

### 3. 事务安全

```python
# 使用 UnitOfWork 保证事务
async with self.uow:
    # 所有操作在同一事务中
    await repo.add(order)
    await self.uow.commit()  # 原子提交
```

## 📈 **性能优化**

### 1. 数据库索引

```python
class OrderModel(Base):
    customer_id = Column(String, index=True)  # 按客户查询
    status = Column(String, index=True)       # 按状态查询
```

### 2. 批量操作

```python
# 批量查询
orders = await repo.find_by_customer_id(customer_id)

# 批量保存
for order in orders:
    await repo.update(order)
await uow.commit()  # 一次性提交
```

### 3. 缓存（未来）

```python
# 使用 Cache 系统
@cached(key="order:{order_id}", ttl=300)
async def get_order(order_id: str):
    ...
```

## 🧪 **测试策略**

### 1. 单元测试（Domain）

```python
def test_order_pay():
    order = Order(...)
    order.add_item(...)
    
    order.pay()
    
    assert order.status == OrderStatus.PAID
    assert len(order.events) == 2  # OrderCreated + OrderPaid
```

### 2. 集成测试（Use Case）

```python
async def test_create_order_use_case():
    uow = InMemoryUnitOfWork()
    use_case = CreateOrderUseCase(uow)
    
    command = CreateOrderCommand(...)
    order = await use_case.execute(command)
    
    assert order["status"] == "pending"
```

### 3. E2E 测试（API）

```python
async def test_api_create_order():
    async with AsyncClient(app=app) as client:
        response = await client.post("/api/orders", json={...})
        assert response.status_code == 200
```

## 🚀 **扩展性**

### 1. 添加新模块

```
modules/
├── order/         # 现有
├── product/       # 新增：产品模块
├── customer/      # 新增：客户模块
└── inventory/     # 新增：库存模块
```

### 2. 添加新功能

```python
# 1. 添加领域方法
class Order:
    def ship(self):
        ...

# 2. 添加 Use Case
class ShipOrderUseCase:
    ...

# 3. 添加 API
@router.post("/{order_id}/ship")
async def ship_order(...):
    ...
```

### 3. 微服务拆分

```
Order Service (订单服务)
├── Order Bounded Context
└── API + Database + Events

Product Service (产品服务)
├── Product Bounded Context
└── API + Database + Events

通过事件总线解耦通信
```

## 📚 **参考**

- [Domain-Driven Design (Eric Evans)](https://www.domainlanguage.com/ddd/)
- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [CQRS Pattern (Martin Fowler)](https://martinfowler.com/bliki/CQRS.html)
- [Event Sourcing (Greg Young)](https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf)

