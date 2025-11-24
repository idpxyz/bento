下面给出一套“电商复杂聚合与多态映射”的可落地设计方案，聚焦如何用 AutoMapper 在不牺牲可维护性的前提下覆盖高复杂度场景。

### 一、聚合建模建议（领域层）
- 订单聚合 `Order`
  - 标识与上下文：`id: ID`，`tenant_id: str`（可放入 `MappingContext`）
  - 价格与货币：`total: Money`（值对象，含 `amount: Decimal`、`currency: str`）
  - 折扣与税：`discounts: list[Discount]`，`tax_lines: list[TaxLine]`
  - 支付多态：`payment: Payment`（抽象基类，子类见下）
  - 配送多态：`shipment: Shipment`（抽象基类，子类见下）
  - 订单项复合：`items: list[OrderLine]`
    - `OrderLine` 支持普通/捆绑/定制商品等多态明细
- 多态对象
  - Payment（抽象）：`PaymentCard`、`PaymentPaypal`、`PaymentCOD`
    - 判别字段建议：`method: Literal["card","paypal","cod"]`
  - Shipment（抽象）：`ShipmentLocal`、`ShipmentFedex`、`ShipmentDHL`
    - 判别字段建议：`carrier: Literal["local","fedex","dhl"]`
  - OrderLine（抽象）：`LineSimple`、`LineBundle`、`LineCustom`
    - 判别字段建议：`kind: Literal["simple","bundle","custom"]`
- 值对象
  - Money（`Decimal` + `currency`）
  - Address（规范化字段，避免自由文本）
  - EntityId/ID（已由框架支持）

说明：建议所有多态类型在领域层保留“判别字段”或可推导的“类型标签”，便于映射时分派。

### 二、PO 设计建议（持久化层）
- 扁平 + 判别字段
  - `payment_*`、`shipment_*` 前缀字段，搭配 `payment_method`、`shipment_carrier` 判别
- 关系/嵌套
  - `order_items` 一对多，`discounts`、`tax_lines` 也建议拆表以适配查询
- Money 持久化
  - 方案 A：两个字段 `total_amount: str`（或 `Decimal`）+ `total_currency: str`
  - 方案 B：JSON（若数据库允许），但通常查询不友好

### 三、Mapper 组织与职责划分
- `OrderMapper`（聚合根）
  - 注册子 mapper：`items`、`discounts`、`tax_lines`
  - 多态字段（`payment`、`shipment`）通过工厂/覆写处理
  - 使用 `parent_keys=["tenant_id","order_id"]` 将父键回填到子 PO
- 子 mapper
  - `OrderLineMapper`：内部再分发至 `LineSimpleMapper` / `LineBundleMapper` / `LineCustomMapper`
  - `DiscountMapper`、`TaxLineMapper`
- 值对象映射
  - `Money` → 两字段或 JSON；建议提供复用型 `override_field` 策略

### 四、AutoMapper 配置范式（关键片段）
- 父子关系与父键回填
  - `self.register_child("items", OrderLineMapper(), parent_keys=["tenant_id","order_id"])`
- 值对象 Money 的复用覆盖
  - 在 `OrderMapper.__init__` 中注册：
    - `override_field("total", to_po=lambda m: str(m.amount), from_po=lambda v: Money(Decimal(v), "CNY"))`
    - 或拆成两个字段：`alias_field("total", "total_amount")` 并增加 `currency` 映射
- Enum ↔ int
  - 若 `status: OrderStatus` 持久化为 int，PO 类型用 `int`，AutoMapper 会自动走 `enum_int`；否则自定义 `override_field`
- ID/EntityId
  - 已内建转换（`EntityId|None ↔ str|None`）；我们已修复 `UnionType` 可用性

### 五、多态映射的两种实现路线
- 路线 A：domain_factory/po_factory（推荐）
  - 在 `OrderMapper` 里传入 `domain_factory`、`po_factory`，在工厂中根据判别字段（如 `payment_method`）选择构造子类/PO
  - 优点：保持单一映射入口，分派逻辑集中，避免在大量 `override_field` 中写 if/else
  - 示例思路：
    - po_factory：把 `{"payment_method":"card", "payment_card_last4":"1234", ...}` 构造成 `PaymentCard` 对应字段
    - domain_factory：从 `PaymentCard` 反推 `payment_method="card"` 并填充 PO 字段
- 路线 B：子 mapper 分派
  - 为多态成员独立 mapper，并在父 mapper 的 `override_field("payment", ...)` 中按判别符委派到相应子 mapper
  - 优点：每种子类型职责清晰；缺点：需要在 override 中显式分派

建议：优先路线 A（工厂），若子类型非常多且逻辑差异大，再为它们提供独立 mapper 并委派。

### 六、诊断与质量（强烈建议）
- 开发/接入阶段：
  - `strict=True` + `only_fields(...)`：缩小映射范围，把未映射字段当错误处理
  - `debug=True`：打印每个字段的映射决策与子实体映射异常
- 错误消息目标
  - 未映射字段：给出候选字段
  - 类型不匹配：提示期望/实际类型与建议（如开启 enum_int 或用 override）
  - 工厂失败：报告目标类型与键名列表

### 七、示例落地（简化示意）
- `OrderMapper(AutoMapper[Order, OrderModel])`：
  - `__init__` 中：
    - `register_child("items", OrderLineMapper(), parent_keys=["tenant_id","order_id"])`
    - Money 映射 `override_field("total", ...)`
    - 多态：传入 `domain_factory=build_order_domain`, `po_factory=build_order_po`
- `build_order_po`（示意）
  - 读取 `payment_method`：
    - "card" → 组装 `PaymentCard` 的字段（`last4`, `brand`, `exp`）到 `payment_*`
    - "paypal" → 组装 `PaymentPaypal` 字段
  - `shipment_carrier` 同理
- `OrderLineMapper`：
  - 读取 `kind` 分派到 `LineSimpleMapper/LineBundleMapper/LineCustomMapper`
  - `LineBundle` 处理嵌套子项（可再次 `register_child("components", LineSimpleMapper(), parent_keys=["tenant_id","order_id"])`）

### 八、最小改造路线（性价比最高）
- 先为 `Order` 增加 `payment.method` 与 `shipment.carrier` 判别字段（若未有）
- 为 `OrderMapper` 增加工厂（domain_factory/po_factory），聚合多态组装逻辑
- 为 `Money/Decimal`、`Enum↔int` 建立复用覆盖策略（工具函数级别），保证所有 mapper 共享一致转换
- 新增少量单测：验证多态分派、值对象映射、子项父键回填

这样，你可以以最少改动扩展出“复杂聚合 + 多态映射”的能力，同时保持 AutoMapper 的统一入口、类型安全与调试友好。需要我按这个方案先为 `Order` 和 `OrderModel` 加上判别字段与 mapper 工厂骨架代码吗？

---

## 已落地方案概览（v1）

- 数据库/PO
  - `OrderModel` 增加判别字段：`payment_method`、`shipment_carrier`
  - `OrderModel` 增加通用字段：`payment_card_last4`、`payment_card_brand`、`payment_paypal_payer_id`、`shipment_tracking_no`、`shipment_service`
  - `OrderItemModel` 增加 `kind`（默认 `simple`，带索引）
- 领域
  - `Order` 增加与上述匹配的扁平字段（便于类型驱动映射）
  - `Payment` 抽象与子类：`PaymentCard(last4, brand)`、`PaymentPaypal(payer_id)`
  - `Shipment` 抽象与子类：`ShipmentFedex(tracking_no, service)`、`ShipmentLocal(...)`
  - `Order` 增加可选 `payment: Payment | None`、`shipment: Shipment | None`
- 映射
  - `OrderMapper` 接入 `domain_factory/po_factory`，在 `before_map_reverse` 捕获 PO，用于工厂补齐构造必需参数（如 `id -> order_id`、`customer_id`）
  - Domain→PO：若存在显式 `payment/shipment` 对象，投影为判别+扁平字段；否则保留自动推断与兜底拷贝
  - PO→Domain：按判别重建 `payment/shipment` 对象；兼容不完整数据（判别缺失时保持 `None`）
  - `OrderItemMapper`：
    - Domain→PO：`after_map` 按子类设置 `kind`：`LineBundle → "bundle"`、`LineCustom → "custom"`、默认 `"simple"`。
    - PO→Domain：`domain_factory` 按 `kind` 分派构造 `LineSimple/LineBundle/LineCustom`。
    - 兜底：在父级 `OrderMapper.after_map` 中二次确保 `po.items[i].kind` 不为空；在 `after_map_reverse` 的回退重建中，同样按 `kind` 构造对应子类。
  - `DiscountMapper` / `TaxLineMapper`：
    - 将 `Money` 的 `amount` 映射为 `Decimal(18,2)`；`order_id` 由父映射回填。
- 测试
  - 增补往返映射、默认推断、显式对象往返的测试用例（全部通过）
  - 新增 `OrderItem` 多态单测：默认 simple、bundle、以及从 PO `kind="custom"` 反向构造 `LineCustom`

## OrderItem 多态与 kind 分派（实现摘录）

- 领域子类：`LineSimple/LineBundle/LineCustom`（继承自 `OrderItem`）
- `OrderItemMapper` 关键点：
  - `ignore_fields("order_id","kind")`，`only_fields("product_id","product_name","quantity","unit_price")`
  - `after_map` 设置 `po.kind`
  - `domain_factory` 从 `kind` 选择构造器（`"bundle"|"custom"|"simple"`）
  - 兼容 SQLAlchemy `Mapped[...]` 场景的字段覆写（`product_id`、`quantity`、`unit_price`）
- `OrderMapper` 兜底：
  - Domain→PO：若子映射未设置 `kind`，在父级对齐 `kind`；若子映射失败，回退手动构造 `OrderItemModel` 列表并补齐 `order_id`
  - PO→Domain：若子反向映射被跳过，按 `item_po.kind` 构造 `Line*` 子类列表

## 折扣/税行（Discount/TaxLine）子映射

- 新增表：`order_discounts`、`order_tax_lines`（`amount: Numeric(18,2)`、`order_id` 外键索引）
- 映射：
  - `OrderMapper.register_child("discounts", OrderDiscountMapper(), parent_keys="order_id")`
  - `OrderMapper.register_child("tax_lines", OrderTaxLineMapper(), parent_keys="order_id")`
  - `OrderDiscountMapper/OrderTaxLineMapper` 统一把 `Money.amount` ↔ `Decimal` 映射，`order_id` 由父回填

## 迁移（Alembic）

- 配置：`applications/ecommerce/alembic.ini`
- 环境：`applications/ecommerce/migrations/env.py`（`target_metadata = Base.metadata`）
- 版本脚本：`applications/ecommerce/migrations/versions/20251111_1_add_order_discounts_tax_lines.py`
- 运行（需要 `DATABASE_URL`）：
  - `uv run alembic -c applications/ecommerce/alembic.ini upgrade head`

## 多态映射实操要点

1) 判别字段与扁平字段
- 通过 `payment_method`、`shipment_carrier` 搭配扁平字段（如 `payment_card_last4`、`shipment_tracking_no`）进行持久化。
- 优点：查询友好，可按判别直接过滤；映射时可分派重建对象。

2) 工厂与钩子
- `domain_factory`：处理构造器不匹配（如 `id -> order_id`）与缺失参数（从 `before_map_reverse` 捕获的 PO 中补齐）。
- `after_map/after_map_reverse`：作为兜底层，确保多态字段在各 ORM/Mapped 边界条件下也能正确赋值/重建。

3) 分派策略
- Domain→PO：若 `payment` 是 `PaymentCard`，则写入 `payment_method="card"` 与 `payment_card_*`；`PaymentPaypal` 同理。
- PO→Domain：按 `payment_method` 重建 `PaymentCard/PaymentPaypal`；`shipment_carrier` 重建 `ShipmentFedex/ShipmentLocal`。
- 同时保留“轻量推断”（仅在判别缺失时，基于已填字段进行合理推断）。

## 覆盖策略（Decimal/Enum）——如何使用

> 为减少各处重复 `override_field`，提供了复用型覆盖工具：

文件：`src/bento/application/mapper/overrides.py`
- `register_decimal_str_overrides(mapper, *field_names)`：对若干字段注册 Decimal ↔ str 覆盖。
- `register_custom_overrides(mapper, {field_name: (to_po, from_po)})`：批量注册任意自定义覆盖。

使用示例（伪代码）：
```python
from bento.application.mapper.overrides import register_decimal_str_overrides

class InvoiceMapper(AutoMapper[Invoice, InvoiceModel]):
    def __init__(self):
        super().__init__(Invoice, InvoiceModel)
        # 将 Decimal 字段映射为 str（例如存储时更通用，避免精度丢失）
        register_decimal_str_overrides(self, "total_amount", "tax_amount")
```

说明：
- 如果当前电商示例暂未引入 Decimal 字段，可在需要时按上面方式快速启用，无需在各 mapper 重复写覆盖函数。

### 金额字段最佳实践

- 领域层统一使用 `Decimal` 表示金额，避免浮点误差；构造时允许传入 `float`，内部规范化为 `Decimal(str(v))`。
- PO 层优先以文本（String）存储金额，或使用数据库 Decimal 类型（若迁移成本允许）。示例中为通用性采用 String。
- Mapper 层集中注册 `Decimal ↔ str` 覆盖，禁止各处散落手写转换。
- 合计/小计一律在领域层以 Decimal 计算；展示时再格式化为字符串。
- 若未来新增订单层面的 `discount_amount`、`tax_amount` 等字段，可直接在 `OrderMapper.__init__` 中：
  ```python
  register_decimal_str_overrides(self, "discount_amount", "tax_amount")
  ```

## 迁移与扩展建议

- 如需增加更多 `Shipment`/`Payment` 子类：
  - 在领域层新增子类（保持明确判别常量）
  - 在 `OrderMapper.after_map/after_map_reverse` 中扩充分派逻辑
  - 可引入“策略注册表”模式（dict：判别值 -> 构造函数）进一步减少 `if/elif`

- 如需为 `OrderLine` 引入 bundle/custom 等多态：
  - 为 `OrderLine` 增加子类与判别 `kind`
  - 增加 `LineBundleMapper/LineCustomMapper` 或在工厂内分派
  - 父子映射时继续使用 `register_child(..., parent_keys=[...])` 回填父键

