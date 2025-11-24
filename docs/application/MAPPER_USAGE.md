AutoMapper 使用指南
====================

概览
----
AutoMapper 提供低/零配置的领域对象（Domain）与持久化对象（PO）之间的映射。其核心是“类型驱动”的自动推断，内置智能缺省，同时为复杂场景提供可扩展的“安全出口”。本指南演示在真实项目中的用法。

功能要点
- 基于类型的推断（不依赖易碎的 dir() 反射）
- ID/EntityId ↔ str、Enum ↔ str/int 的双向转换
- 自动解包 Optional/Union 和 Annotated
- 子实体自动映射与父键回填
- 列表批量映射辅助
- 字段级别的覆盖点（override）、别名/忽略/白名单控制
- 严格模式（strict）与调试日志（debug）用于诊断
- 通过 domain_factory/po_factory 支持自定义构造

适用场景
- 领域聚合/实体（dataclass 或带类型注解的类）与 POs（ORM/Pydantic/dataclass）之间的映射
- 外部 DTO 与领域类型之间的转换
- 降低样板代码与重复转换逻辑

快速开始
--------
导入：

```python
from bento.application.mapper import AutoMapper
from bento.application.mapper.base import MappingContext
from bento.core.ids import ID, EntityId
```

定义 Domain 与 PO：

```python
from dataclasses import dataclass
from enum import Enum
from typing import Annotated

class OrderStatus(Enum):
    NEW = "NEW"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    id: ID
    customer_id: EntityId | None
    status: OrderStatus
    annotated_id: Annotated[ID, "primary key"]

@dataclass
class OrderModel:
    id: str
    customer_id: str | None
    status: str
    annotated_id: str
```

创建 Mapper：

```python
class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self, *, context: MappingContext | None = None):
        super().__init__(Order, OrderModel, context=context)
```

使用示例：

```python
mapper = OrderMapper()
po = mapper.map(Order(id=ID("o-1"), customer_id=None, status=OrderStatus.NEW, annotated_id=ID("o-1")))
assert po.id == "o-1"
assert po.status == "NEW"

domain = mapper.map_reverse(po)
assert isinstance(domain.id, ID)
assert domain.status is OrderStatus.NEW
```

自动推断涵盖
------------
- ID 类型（ID/EntityId）在 Domain→PO 时转为 str；在反向映射时由 str 还原为 ID/EntityId
- Enum 默认转为 str；当 PO 字段是 int 时支持 Enum ↔ int（枚举值）
- 自动解包 Optional[T] 与 Annotated[T, ...]
- 简单类型（str/int/float/bool/bytes/date/datetime/UUID/Decimal）直接复制

别名 / 忽略 / 白名单
-------------------
```python
class ProductMapper(AutoMapper[Product, ProductModel]):
    def __init__(self):
        super().__init__(Product, ProductModel)
        self.alias_field("display_name", "name_text")
        self.ignore_fields("internal_notes")
        # 只映射白名单（与 strict 结合能获得更好诊断）
        # self.only_fields("id", "display_name", "price")
```

字段覆盖（override）
-------------------
针对单个字段自定义转换：

```python
self.override_field(
    "price",
    to_po=lambda p: str(p),           # Decimal → str
    from_po=lambda v: Decimal(v),     # str → Decimal
)
```

子实体与父键回填
----------------
注册子 mapper，并配置父键（支持多外键）：

```python
class OrderItemMapper(AutoMapper[OrderItem, OrderItemModel]):
    def __init__(self):
        super().__init__(OrderItem, OrderItemModel)

class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self):
        super().__init__(Order, OrderModel)
        self.register_child("items", OrderItemMapper(), parent_keys=["tenant_id", "order_id"])
```

调用 `map(order)` 时会自动映射 `items`（若存在）。父键将尽力回填到子 PO（例如 tenant_id 来自上下文，order_id 由父 id 转换）。

复杂构造的工厂支持
------------------
对于“富领域对象”或特殊 PO 构造（Pydantic/ORM），可提供工厂：

```python
def build_domain(d: dict) -> Order:
    # 执行不变量校验 / 领域工厂 / 预处理
    return Order(**d)

def build_po(d: dict) -> OrderModel:
    # 例如：Pydantic 可使用 model_construct
    return OrderModel(**d)

class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self):
        super().__init__(Order, OrderModel, domain_factory=build_domain, po_factory=build_po)
```

若工厂抛出异常，AutoMapper 会包装为包含“目标类型与可用键名”的 TypeError，便于定位。

严格模式与调试日志
------------------
- `strict=True`：在字段未映射或转换不明确时抛出异常（结合 `only_fields` 效果更好）
- `debug=True`：输出映射决策（domain_field/type → po_field/type）与子实体映射错误

```python
strict_mapper = AutoMapper(Order, OrderModel, strict=True, debug=True)
```

批量映射辅助
------------
```python
pos = mapper.map_list([o1, o2, o3])
domains = mapper.map_reverse_list(pos)                  # 默认清理领域事件
domains_keep = mapper.map_reverse_list(pos, with_events=False)
```

错误信息与诊断
--------------
在 strict/debug 下常见诊断示例：
- 未映射字段建议：`title -> candidates: name, display_name`
- 类型不匹配提示：`status (Enum) → po.status (int)。可启用 enum_int 或对该字段 override`
- 枚举值非法：`Invalid OrderStatus: 'PAI'。Allowed values: ['NEW','PAID','CANCELLED']; names: [NEW, PAID, CANCELLED]`
- 工厂/构造失败：错误中包含目标类型与传入键名

多态场景建议
------------
AutoMapper 不强制特定多态方案，常见做法：
1) 判别字段 + 工厂
   - 在 `domain_factory/po_factory` 中读取判别符（如 `kind`）并构造正确子类/PO
2) 子类型专属 mapper
   - 为每个子类型注册独立 mapper，在调用处选择
3) 嵌套多态委托给子 mapper

测试用例范式
------------
```python
po = mapper.map(order)
assert po.id == "order-123"
assert po.status == "PAID"
assert po.customer_id is None

domain = mapper.map_reverse(po)
assert isinstance(domain.id, ID)
assert domain.status is OrderStatus.PAID
```

建议对新映射开启 `strict=True`，尽早发现遗漏；在开发调试中临时开启 `debug=True` 追踪决策。

常见问答（FAQ）
---------------
Q: PO 需要特殊构造（如 Pydantic）怎么办？
A: 提供 `po_factory`，AutoMapper 会先整理好 dict 交给它构造。

Q: 领域对象需要工厂保证不变量？
A: 提供 `domain_factory`，避免绕过不变量。

Q: 为什么某个字段没映射上？
A: 开 `debug=True` 看决策；更严格可开 `strict=True` 并配合 `only_fields(...)`。

Q: 数据库存的是枚举 int？
A: 若 PO 字段是 `int`，AutoMapper 会使用枚举值转换；否则自行 override。

Q: 子对象需要 tenant_id 与 order_id 两个父键？
A: `register_child(..., parent_keys=["tenant_id","order_id"])`，tenant/org 也可来自 `MappingContext`。

参考清单
--------
核心类型：
- `AutoMapper[Domain, PO]`
- `MappingContext`（传播 tenant_id/org_id/actor_id/extra）

定制 API：
- `alias_field(domain_field, po_field)`
- `ignore_fields(*names)`
- `only_fields(*names)`（与 `strict=True` 搭配更佳）
- `override_field(field_name, to_po, from_po)`
- `register_child(field_name, child_mapper, parent_keys=...)`
- `rebuild_mappings()`（在变更后重新分析）

构造参数：
- `include_none`、`strict`、`debug`、`map_children_auto`
- `default_id_type`、`id_factory`
- `domain_factory`、`po_factory`
- `context: MappingContext`

以上即为 AutoMapper 的核心用法：在保证类型安全与可维护性的同时，兼顾复杂场景的可扩展性。


