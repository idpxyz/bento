# Bento Modular Monolith 架构指南

## 🎯 什么是 Modular Monolith？

**Modular Monolith（模块化单体）** 是一种按**边界上下文（Bounded Context）**组织代码的架构模式，每个上下文都是独立的模块，具有清晰的边界，但部署在同一个进程中。

### 核心优势

✅ **边界清晰** - 每个上下文独立演化
✅ **团队并行** - 不同团队负责不同上下文
✅ **易于拆分** - 未来可轻松拆分为微服务
✅ **依赖明确** - 上下文间通过接口/事件通信
✅ **单体优势** - 保持单体应用的简单性和性能

---

## 🏗️ 架构对比

### 传统分层架构（Layered）

```
my-app/
├── domain/              ❌ 所有聚合根混在一起
│   ├── product.py
│   ├── order.py
│   └── user.py
├── application/         ❌ 所有用例混在一起
│   └── usecases/
└── infrastructure/      ❌ 所有技术细节混在一起
```

**问题**：
- 边界不清晰
- 容易产生跨上下文依赖
- 难以演化和拆分
- 团队协作困难

### Modular Monolith 架构（推荐）

```
my-app/
├── contexts/                    ✅ 按边界上下文组织
│   ├── catalog/                # 产品目录上下文
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── ordering/               # 订单上下文
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── identity/               # 身份上下文
│   │   └── ...
│   └── shared/                 # 共享内核
│       ├── domain/
│       └── events/
└── tests/                      ✅ 按上下文组织测试
    ├── catalog/
    ├── ordering/
    └── identity/
```

**优势**：
- ✅ 边界清晰，每个上下文独立
- ✅ 上下文间通过集成事件通信
- ✅ 易于团队协作和并行开发
- ✅ 可独立演化和测试

---

## 🚀 快速开始

### 1. 初始化项目（Modular Monolith）

```bash
# 使用 Modular Monolith 架构（默认）
/workspace/bento/bin/bento-gen init my-ecommerce \
  --architecture modular-monolith \
  --description "E-commerce platform"

cd my-ecommerce
```

**生成的结构**：
```
my-ecommerce/
├── contexts/
│   └── shared/              # 共享内核
│       ├── domain/
│       └── events/
├── api/                     # API 层
├── tests/                   # 测试
├── main.py                  # 应用入口
└── config.py                # 配置
```

### 2. 生成第一个上下文模块

```bash
# 在 catalog 上下文中生成 Product 模块
/workspace/bento/bin/bento-gen gen module Product \
  --context catalog \
  --fields "name:str,price:float,stock:int" \
  --output .
```

**生成的结构**：
```
contexts/catalog/
├── domain/
│   ├── product.py
│   └── events/
│       └── productcreated_event.py
├── application/
│   └── usecases/
│       └── create_product.py
└── infrastructure/
    ├── models/
    │   └── product_po.py
    ├── mappers/
    │   └── product_mapper.py
    └── repositories/
        └── product_repository.py

tests/catalog/
├── unit/
│   ├── domain/
│   │   └── test_product.py
│   └── application/
│       └── test_create_product.py
└── integration/
    └── test_product_repository.py
```

### 3. 生成更多上下文

```bash
# Ordering 上下文
/workspace/bento/bin/bento-gen gen module Order \
  --context ordering \
  --fields "customer_email:str,total:float,status:str" \
  --output .

# Identity 上下文
/workspace/bento/bin/bento-gen gen module User \
  --context identity \
  --fields "username:str,email:str,is_active:bool" \
  --output .

# Inventory 上下文
/workspace/bento/bin/bento-gen gen module Stock \
  --context inventory \
  --fields "product_id:str,quantity:int,location:str" \
  --output .
```

---

## 📂 完整项目结构

### 实际电商应用示例

```
ecommerce-modular/
├── 📦 配置文件
│   ├── pyproject.toml
│   ├── .env.example
│   ├── pytest.ini
│   └── alembic.ini
│
├── 🚀 应用入口
│   ├── main.py
│   └── config.py
│
├── 🌐 API 层
│   └── api/
│       ├── deps.py
│       └── router.py
│
├── 🎯 边界上下文
│   └── contexts/
│       ├── catalog/          # 产品目录上下文
│       │   ├── domain/
│       │   │   ├── product.py
│       │   │   ├── category.py
│       │   │   └── events/
│       │   ├── application/
│       │   │   └── usecases/
│       │   └── infrastructure/
│       │       ├── models/
│       │       ├── mappers/
│       │       └── repositories/
│       │
│       ├── ordering/         # 订单上下文
│       │   ├── domain/
│       │   │   ├── order.py
│       │   │   ├── order_item.py
│       │   │   └── events/
│       │   ├── application/
│       │   └── infrastructure/
│       │
│       ├── identity/         # 身份上下文
│       │   ├── domain/
│       │   │   ├── user.py
│       │   │   └── events/
│       │   ├── application/
│       │   └── infrastructure/
│       │
│       ├── inventory/        # 库存上下文
│       │   └── ...
│       │
│       └── shared/           # 共享内核
│           ├── domain/       # 共享值对象
│           └── events/       # 集成事件
│
└── 🧪 测试
    └── tests/
        ├── catalog/
        │   ├── unit/
        │   └── integration/
        ├── ordering/
        │   ├── unit/
        │   └── integration/
        └── identity/
            ├── unit/
            └── integration/
```

---

## 🎨 上下文设计指南

### 如何识别边界上下文？

按**业务能力**划分，而不是技术层：

#### ✅ 好的上下文划分

```
contexts/
├── catalog/          # 产品目录管理（商品团队）
├── ordering/         # 订单处理（订单团队）
├── inventory/        # 库存管理（仓储团队）
├── payment/          # 支付处理（支付团队）
├── shipping/         # 物流配送（物流团队）
└── identity/         # 用户身份（安全团队）
```

#### ❌ 错误的上下文划分

```
contexts/
├── crud/             # ❌ 技术功能，不是业务能力
├── validation/       # ❌ 技术关注点
└── persistence/      # ❌ 技术实现细节
```

### 上下文大小原则

- **小而聚焦** - 一个上下文通常包含 2-10 个聚合根
- **单一职责** - 每个上下文负责一个核心业务能力
- **独立演化** - 上下文应能独立修改和部署

---

## 🔗 上下文间通信

### 1. 集成事件（推荐）

**场景**：订单上下文需要知道产品价格变化

```python
# contexts/catalog/domain/events/product_price_changed.py
from dataclasses import dataclass
from bento.domain.domain_event import DomainEvent

@dataclass(frozen=True)
class ProductPriceChangedEvent(DomainEvent):
    """产品价格变更事件（集成事件）"""
    name: str = "product_price_changed"
    product_id: str
    old_price: float
    new_price: float

# contexts/catalog/domain/product.py
class Product(AggregateRoot):
    def update_price(self, new_price: float):
        old_price = self.price
        self.price = new_price
        # 发布集成事件给其他上下文
        self.add_event(ProductPriceChangedEvent(
            product_id=self.id,
            old_price=old_price,
            new_price=new_price
        ))

# contexts/ordering/application/event_handlers/product_price_handler.py
class ProductPriceChangedHandler:
    """订单上下文订阅产品价格变更事件"""
    async def handle(self, event: ProductPriceChangedEvent):
        # 更新订单中的产品价格快照
        ...
```

### 2. 查询接口（读取数据）

**场景**：订单上下文需要读取产品信息

```python
# contexts/catalog/application/queries/product_query.py
from typing import Protocol

class IProductQuery(Protocol):
    """产品查询接口 - 供其他上下文使用"""
    async def get_product_info(self, product_id: str) -> ProductInfo:
        ...

# contexts/ordering/application/usecases/place_order.py
class PlaceOrderUseCase:
    def __init__(self, product_query: IProductQuery):
        self._product_query = product_query  # 依赖注入

    async def execute(self, cmd):
        # ✅ 通过接口查询，不直接依赖 Product 聚合根
        product_info = await self._product_query.get_product_info(cmd.product_id)

        # 在订单中保存产品快照
        order.add_item(
            product_id=product_info.id,
            name=product_info.name,
            price=product_info.price
        )
```

### 3. 共享内核（谨慎使用）

```python
# contexts/shared/domain/money.py
@dataclass(frozen=True)
class Money:
    """共享值对象 - 金额"""
    amount: float
    currency: str = "CNY"

    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)

# 在所有上下文中使用
from contexts.shared.domain.money import Money
```

---

## 📝 实践示例

### 完整的电商应用

```bash
# 1. 初始化项目
/workspace/bento/bin/bento-gen init ecommerce \
  --architecture modular-monolith

cd ecommerce

# 2. 产品目录上下文
/workspace/bento/bin/bento-gen gen module Product \
  --context catalog \
  --fields "name:str,description:str,price:float,category:str"

/workspace/bento/bin/bento-gen gen module Category \
  --context catalog \
  --fields "name:str,parent_id:str"

# 3. 订单上下文
/workspace/bento/bin/bento-gen gen module Order \
  --context ordering \
  --fields "customer_id:str,status:str,total:float"

/workspace/bento/bin/bento-gen gen module OrderItem \
  --context ordering \
  --fields "order_id:str,product_id:str,quantity:int,price:float"

# 4. 身份上下文
/workspace/bento/bin/bento-gen gen module User \
  --context identity \
  --fields "username:str,email:str,hashed_password:str"

# 5. 库存上下文
/workspace/bento/bin/bento-gen gen module Stock \
  --context inventory \
  --fields "product_id:str,quantity:int,warehouse:str"

# 6. 支付上下文
/workspace/bento/bin/bento-gen gen module Payment \
  --context payment \
  --fields "order_id:str,amount:float,method:str,status:str"
```

---

## 🔄 与传统架构的迁移

### 从 Layered 迁移到 Modular Monolith

```bash
# 旧项目结构（layered）
domain/
├── product.py
├── order.py
└── user.py

# 迁移步骤
1. 识别边界上下文
2. 创建 contexts/ 目录
3. 移动相关代码到对应上下文
4. 重构跨上下文依赖

# 新结构
contexts/
├── catalog/domain/product.py
├── ordering/domain/order.py
└── identity/domain/user.py
```

---

## 📊 架构选择指南

| 项目规模 | 推荐架构 | 原因 |
|---------|---------|------|
| **小型**（<5 聚合根）| Layered | 简单快速，边界不重要 |
| **中型**（5-20 聚合根）| **Modular Monolith** | 边界清晰，易于演化 |
| **大型**（>20 聚合根）| **Modular Monolith** | 必须，否则无法维护 |

### 何时使用 Modular Monolith？

✅ **应该使用**：
- 系统有多个明确的业务能力
- 多个团队协作开发
- 需要独立演化不同模块
- 未来可能拆分为微服务

❌ **不必使用**：
- 单人项目
- 极简 CRUD 应用
- 原型或 MVP
- 所有功能高度耦合

---

## 🎓 最佳实践

### 1. 上下文命名

```bash
# ✅ 好的命名 - 业务术语
contexts/catalog/
contexts/ordering/
contexts/inventory/

# ❌ 坏的命名 - 技术术语
contexts/products/
contexts/orders/
contexts/stocks/
```

### 2. 依赖方向

```
❌ 错误：ordering -> catalog (直接依赖聚合根)
✅ 正确：ordering -> IProductQuery (依赖接口)
✅ 正确：catalog -> ProductPriceChanged -> ordering (事件通知)
```

### 3. 数据一致性

- **同上下文内**：使用事务保证强一致性
- **跨上下文**：使用最终一致性（事件驱动）

### 4. 测试隔离

```bash
# 每个上下文独立测试
pytest tests/catalog/
pytest tests/ordering/
pytest tests/identity/

# 集成测试验证上下文间通信
pytest tests/integration/
```

---

## 🚀 下一步

1. **设计上下文边界** - 识别核心业务能力
2. **定义集成事件** - 设计上下文间通信
3. **实现共享内核** - 定义共享概念
4. **编写测试** - 验证上下文隔离
5. **持续重构** - 优化边界和依赖

---

## 📚 参考资源

- [Domain-Driven Design](https://martinfowler.com/bliki/BoundedContext.html)
- [Modular Monolith](https://www.kamilgrzybek.com/design/modular-monolith-primer/)
- [Context Mapping](https://github.com/ddd-crew/context-mapping)

---

**Bento CLI 现已完全支持 Modular Monolith 架构！** 🎉
