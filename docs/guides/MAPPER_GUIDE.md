# Bento Mapper System - 完整指南

> **更新日期**: 2024
> **最新特性**: 延迟初始化、Protocol 支持、运行时类型验证

## 概述

Bento Mapper 系统提供了 **2 种映射策略**，让你能够根据实际场景选择最合适的方式在 **Domain 对象** 和 **Persistence 对象 (PO)** 之间进行转换。

### 两种策略对比

| 策略 | 适用场景 | 开发效率 | 灵活性 | 代码量 |
|------|---------|---------|-------|--------|
| **AutoMapper** | 简单到中等（字段基本匹配；少量差异可用 alias/only/override 解决） | ⚡⚡⚡ 很快 | ✅ 中 | **~0-5 行** |
| **BaseMapper** | 复杂聚合（需要完全控制） | 🐌 较慢 | ✅✅✅ 极高 | 视复杂度而定 |

### 最新改进 (2024)

- ✅ **性能优化**: 延迟初始化类型分析，减少启动开销
- ✅ **类型增强**: Protocol 支持（HasId, HasEvents），增强类型检查
- ✅ **验证增强**: 运行时类型验证，早期发现错误

---

## 1. AutoMapper - 零代码自动映射

### 何时使用

- ✅ Domain 和 PO 字段名**基本匹配**（80%+）
- ✅ 简单的 CRUD 实体
- ✅ 主数据实体（如仓库、分类、标签）
- ✅ 快速原型开发
- ✅ 少量字段差异可用 `alias_field()` 或 `override_field()` 解决

### 自动转换规则

```python
# AutoMapper 自动处理：
EntityId("abc")  ↔  "abc"          # ID/EntityId ↔ str
ID("xyz")        ↔  "xyz"          # ID ↔ str
Status.ACTIVE     ↔  "active"       # Enum ↔ str

# 子实体：注册 register_child(...) 后自动映射（可用 map_children_auto 控制）
```

### 性能特性

- ✅ **延迟初始化**: 类型分析在首次使用时才执行，减少启动开销
- ✅ **strict 模式**: 启用后立即分析类型，早期发现配置错误
- ✅ **运行时验证**: `map()` 和 `map_reverse()` 自动验证类型，提供清晰的错误消息

### 快速开始

```python
from bento.application.mapper import AutoMapper
from bento.core.ids import EntityId

# 1. 定义 Domain 对象
@dataclass
class Warehouse:
    id: EntityId
    name: str
    location: str
    capacity: int
    status: WarehouseStatus  # Enum

# 2. 定义 PO 对象（字段名匹配）
@dataclass
class WarehousePO:
    id: str
    name: str
    location: str
    capacity: int
    status: str

# 3. 创建 Mapper - 就这么简单！
mapper = AutoMapper(Warehouse, WarehousePO)

# 4. 使用
warehouse = Warehouse(id=EntityId("wh-001"), name="Main", ...)
po = mapper.map(warehouse)  # Domain → PO
warehouse = mapper.map_reverse(po)  # PO → Domain
```

### 高级用法

#### 忽略字段

```python
mapper = AutoMapper(Product, ProductPO)
mapper.ignore_fields("_cache", "_computed_values")
```

#### 字段别名（名称不一致时）

```python
mapper = AutoMapper(Order, OrderPO)
mapper.alias_field("customerId", "customer_id")
```

#### 白名单与严格模式

```python
mapper = AutoMapper(Order, OrderPO, strict=True)

# 仅映射白名单字段；若未匹配会抛出带候选名的错误
mapper.only_fields("id", "customerId")

# 结合别名使用：
mapper.alias_field("customerId", "customer_id").only_fields("id", "customerId")
```

#### 覆盖个别字段的转换

```python
mapper = AutoMapper(Order, OrderPO)
mapper.override_field(
    "status",
    to_po=lambda s: s.value,
    from_po=lambda v: OrderStatus(v),
)
```

#### 自动子实体映射

```python
class OrderItemMapper(AutoMapper[OrderItem, OrderItemPO]):
    def __init__(self) -> None:
        super().__init__(OrderItem, OrderItemPO)
        self.ignore_fields("order_id")  # 由父设置

class OrderMapper(AutoMapper[Order, OrderPO]):
    def __init__(self) -> None:
        super().__init__(Order, OrderPO)
        # parent_keys 支持单个字符串或多个键（多外键场景）
        self.register_child("items", OrderItemMapper(), parent_keys="order_id")
        # 或使用多个父键：
        # self.register_child("items", OrderItemMapper(),
        #                     parent_keys=["tenant_id", "org_id", "order_id"])
        # map_children_auto 默认为 True：会自动映射 items
```

#### 重新构建映射（修改 alias/ignore/only 后）

```python
mapper.rebuild_mappings()
```

---

## 2. BaseMapper - 手写可控，带智能助手

### 何时使用

- ✅ 复杂聚合根、字段结构差异大
- ✅ 需要完全控制每个字段的转换
- ✅ 对性能/可读性有明确预期

### 快速开始

```python
from bento.application.mapper import BaseMapper

class OrderMapper(BaseMapper[Order, OrderPO]):
    def __init__(self) -> None:
        super().__init__(Order, OrderPO)
        self.register_child("items", OrderItemMapper(), parent_keys="order_id")

    def map(self, d: Order) -> OrderPO:
        po = OrderPO(
            id=self.convert_id_to_str(d.id),
            customer_id=self.convert_id_to_str(d.customer_id),
            status=self.convert_enum_to_str(d.status),
            paid_at=d.paid_at,
        )
        po.items = self.map_children(d, po, "items")
        return po

    def map_reverse(self, po: OrderPO) -> Order:
        d = Order(
            id=self.convert_str_to_id(po.id),
            customer_id=self.convert_str_to_id(po.customer_id),
            status=self.convert_str_to_enum(po.status, OrderStatus),
            paid_at=po.paid_at,
            items=[],
        )
        d.items = self.map_reverse_children(po, "items")
        self.auto_clear_events(d)
        return d
```

要点：
- `convert_*` 系列已支持 None 安全；
- `map_children` 会优先使用 `domain.id`（转换为字符串）设置子 PO 外键；
- `map_reverse` 结束时调用 `auto_clear_events`；
- 支持多外键场景：`parent_keys=["tenant_id", "org_id", "order_id"]`；
- 支持 `MappingContext` 自动传播 `tenant_id`、`org_id`、`actor_id` 等信息。

---

## 实战案例

### 案例 1：简单仓库实体（AutoMapper）

```python
from bento.application.mapper import AutoMapper

# Domain
@dataclass
class Warehouse:
    id: EntityId
    code: str
    name: str
    location: str
    capacity: int
    status: WarehouseStatus

# PO
@dataclass
class WarehousePO:
    id: str
    code: str
    name: str
    location: str
    capacity: int
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

# Mapper - 0 行代码！
mapper = AutoMapper(Warehouse, WarehousePO)

# 使用
warehouse = Warehouse(id=EntityId("wh-001"), ...)
po = mapper.map(warehouse)  # 完成！
```

**优势**：零代码，自动转换，审计字段自动忽略。

---

### 案例 2：商品实体（AutoMapper + override）

```python
from bento.application.mapper import AutoMapper

# Domain
@dataclass
class Product:
    id: EntityId
    sku: str
    name: str
    price: float
    status: ProductStatus

    def calculate_discounted_price(self) -> float:
        return self.price * 0.9

# PO
@dataclass
class ProductPO:
    id: str
    sku: str
    name: str
    price: float
    status: str
    discounted_price: float  # 计算字段

# Mapper - 只需 3 个 override_field
mapper = AutoMapper(Product, ProductPO)
mapper.override_field(
    "discounted_price",
    to_po=lambda p: p.calculate_discounted_price(),
    from_po=lambda v: None  # 单向，从 PO 读取时忽略
)

# id, sku, name, price, status 自动映射 ✨
# discounted_price 使用自定义转换
```

**优势**：80% 自动映射，20% 自定义，代码简洁。

---

### 案例 3：订单聚合（BaseMapper）

```python
from bento.application.mapper import BaseMapper

# Domain
@dataclass
class Order:
    id: EntityId
    customer_id: ID
    status: OrderStatus
    total_amount: float
    paid_at: datetime | None
    items: list[OrderItem]  # 子实体

# PO（字段名不同）
@dataclass
class OrderPO:
    id: str
    customer_id: str
    status: str
    amount: float  # 不同名！
    paid_at: datetime | None

# Mapper - 完全控制
class OrderMapper(BaseMapper[Order, OrderPO]):
    def __init__(self) -> None:
        super().__init__(Order, OrderPO)
        self.register_child("items", OrderItemMapper(), parent_keys="order_id")

    def map(self, d: Order) -> OrderPO:
        po = OrderPO(
            id=self.convert_id_to_str(d.id),
            customer_id=self.convert_id_to_str(d.customer_id),
            status=self.convert_enum_to_str(d.status),
            amount=d.total_amount,  # 处理名称差异
            paid_at=d.paid_at,
        )
        po.items = self.map_children(d, po, "items")
        return po

    def map_reverse(self, po: OrderPO) -> Order:
        d = Order(
            id=self.convert_str_to_id(po.id),
            customer_id=self.convert_str_to_id(po.customer_id),
            status=self.convert_str_to_enum(po.status, OrderStatus),
            total_amount=po.amount,  # 处理名称差异
            paid_at=po.paid_at,
            items=[],
        )
        d.items = self.map_reverse_children(po, "items")
        self.auto_clear_events(d)
        return d
```

**优势**：完全控制，清晰明确，适合复杂场景。

---

## 最佳实践

### 1. 选择合适的策略

```python
# ✅ 简单/中等复杂：优先 AutoMapper（可配合 alias/only/override）
mapper = AutoMapper(Warehouse, WarehousePO)

# ✅ 复杂聚合/完全控制：使用 BaseMapper
mapper = BaseMapper(Order, OrderPO)
```

### 2. 审计字段交给 Interceptor

```python
# ❌ 错误：在 Mapper 中设置审计字段
class OrderMapper(BaseMapper[Order, OrderPO]):
    def map(self, d: Order) -> OrderPO:
        po = OrderPO(...)
        po.created_at = datetime.now()  # ❌ 不要这样做

# ✅ 正确：审计字段由 Interceptor 自动管理
mapper = AutoMapper(Order, OrderPO)  # 自动忽略 created_at 等字段
```

### 3. 子实体映射

```python
# AutoMapper：注册子映射器后自动完成（推荐）
order_mapper = AutoMapper(Order, OrderPO)
order_mapper.register_child("items", AutoMapper(OrderItem, OrderItemPO), parent_keys="order_id")

# BaseMapper：在 map/map_reverse 中显式调用 map_children/map_reverse_children
```

### 4. 清除领域事件

```python
# Mapper 自动调用 clear_events()（如果存在）
restored_order = mapper.map_reverse(po)
# restored_order.events == []  ✅ 已清除
```

---

## 与 Repository 集成

```python
from bento.persistence.repository import BaseRepository
from bento.application.mapper import AutoMapper

class ProductRepositoryAdapter:
    def __init__(self, session: AsyncSession):
        # 1. 创建 Mapper（简单/中等复杂度）
        self._mapper = AutoMapper(Product, ProductPO)

        # 2. 创建 BaseRepository（带 Interceptor）
        self._base_repo = BaseRepository(
            session=session,
            po_type=ProductPO,
            actor="system",
            interceptor_chain=create_default_chain()
        )

    async def save(self, product: Product) -> None:
        # 3. Domain → PO
        po = self._mapper.map(product)

        # 4. 保存 PO（Interceptor 自动填充审计字段）
        await self._base_repo.create_po(po)

    async def get_by_id(self, id: EntityId) -> Product | None:
        # 5. 获取 PO
        po = await self._base_repo.get_po_by_id(id.value)
        if not po:
            return None

        # 6. PO → Domain
        return self._mapper.map_reverse(po)
```

---

## 迁移指南

### 从旧手写 Mapper 迁移

```python
# 旧代码（手动实现）
class OrderMapper:
    def map(self, order: Order) -> OrderPO:
        return OrderPO(
            id=order.id.value,
            customer_id=order.customer_id.value,
            status=order.status.value,
            # ... 20 行手动映射
        )

    def map_reverse(self, po: OrderPO) -> Order:
        # ... 又是 20 行
        pass

# ✅ 新代码（使用 BaseMapper）
class OrderMapper(BaseMapper[Order, OrderPO]):
    def __init__(self) -> None:
        super().__init__(Order, OrderPO)

    def map(self, o: Order) -> OrderPO:
        return OrderPO(
            id=self.convert_id_to_str(o.id),
            customer_id=self.convert_id_to_str(o.customer_id),
            status=self.convert_enum_to_str(o.status),
        )

    def map_reverse(self, po: OrderPO) -> Order:
        d = Order(
            id=self.convert_str_to_id(po.id),
            customer_id=self.convert_str_to_id(po.customer_id),
            status=self.convert_str_to_enum(po.status, OrderStatus),
        )
        self.auto_clear_events(d)
        return d

# ✅✅ 更好：如果字段名基本匹配，用 AutoMapper，并用别名/覆盖解决少量差异
mapper = AutoMapper(Order, OrderPO)
mapper.alias_field("total_amount", "amount")  # 字段名不一致时使用别名
# 或使用 override_field 进行完全自定义转换
```

---

## 性能建议

### 1. 复用 Mapper 实例

```python
# ✅ 好：创建一次，多次使用
class ProductRepository:
    def __init__(self):
        self._mapper = AutoMapper(Product, ProductPO)
        self._mapper.override_field(...)

    async def save(self, product: Product):
        po = self._mapper.map(product)  # 复用
```

### 2. 批量映射

```python
# 批量映射
products = [...]
pos = [mapper.map(p) for p in products]

# 或使用列表推导
pos = list(map(mapper.map, products))
```

---

## 故障排查

### 问题 1：字段缺失

```python
# 错误信息：missing 1 required positional argument: 'name'

# 原因：AutoMapper 找不到匹配字段
# 解决：使用 alias_field 或 override_field
mapper = AutoMapper(Product, ProductPO)
mapper.alias_field("name", "product_name")  # 或
mapper.override_field("name", to_po=lambda p: p.name, from_po=lambda v: v)
```

### 问题 2：类型转换错误

```python
# 错误信息：'str' object has no attribute 'value'

# 原因：忘记类型转换
# 解决：添加 override
.override("id", to_po=lambda d: d.id.value, ...)
```

### 问题 3：Enum 转换失败

```python
# 错误信息： 'active' is not a valid ProductStatus

# 原因：Enum 值不匹配
# 解决：检查 Enum 定义和 PO 值
class ProductStatus(Enum):
    ACTIVE = "active"  # 确保和 PO 一致
```

---

## 总结

### 选择决策树

```
开始
  │
  ├─ 字段名基本匹配（80%+）？
  │   └─ ✅ 使用 AutoMapper（0-5 行代码）⭐ 推荐
  │       ├─ 字段名不一致？→ 使用 alias_field()
  │       ├─ 需要特殊转换？→ 使用 override_field()
  │       └─ 需要忽略字段？→ 使用 ignore_fields()
  │
  └─ 需要完全控制或字段差异大？
      └─ ✅ 使用 BaseMapper（~20-50 行代码）
          └─ 使用 convert_* 辅助方法简化代码
```

### 核心优势

1. **零到完全控制**：2 种策略覆盖所有场景
2. **类型安全**：完整的类型提示支持，Protocol 支持，运行时验证
3. **性能优化**：延迟初始化，减少启动开销
4. **架构解耦**：Domain 和 Infrastructure 完全分离
5. **易于测试**：每种 Mapper 都有完整单元测试
6. **与 Interceptor 无缝集成**：审计字段自动管理
7. **健壮性**：运行时类型验证，早期发现错误

---

## 参考链接

- [Mapper 示例代码](../../applications/ecommerce/examples/mapper_comparison_demo.py)
- [Mapper 单元测试](../../tests/unit/application/mapper/)
- [Interceptor 集成文档](../infrastructure/INTERCEPTOR_USAGE.md)
- [Repository 模式文档](../guides/REPOSITORY_PATTERN.md)

---

**Happy Mapping! 🚀**

