# === Domain ===
from dataclasses import dataclass, field
from enum import Enum
from bento.application.mapper.base import BaseMapper, MappingContext
from bento.core.ids import EntityId


class OrderStatus(Enum):
    NEW = "NEW"
    PAID = "PAID"


@dataclass
class OrderItem:
    id: EntityId | None
    sku: str
    qty: int


@dataclass
class Order:
    id: EntityId | None
    tenant_id: str | None
    org_id: str | None
    status: OrderStatus
    items: list[OrderItem] = field(default_factory=list)
    _events: list[object] = field(default_factory=list)

    def clear_events(self) -> None:
        self._events.clear()


# === PO / ORM (示意) ===
class OrderItemModel:
    id: str | None = None
    order_id: str | None = None
    tenant_id: str | None = None  # 多外键自动回填
    org_id: str | None = None  # 多外键自动回填
    sku: str = ""
    qty: int = 0


class OrderModel:
    id: str | None = None
    tenant_id: str | None = None
    org_id: str | None = None
    status: str = "NEW"
    items: list[OrderItemModel] = []


# === Mappers ===
class OrderItemMapper(BaseMapper[OrderItem, OrderItemModel]):
    def __init__(self, **kw):
        super().__init__(OrderItem, OrderItemModel, **kw)

    def map(self, d: OrderItem) -> OrderItemModel:
        po = OrderItemModel()
        po.id = self.convert_id_to_str(d.id)
        po.sku = d.sku
        po.qty = d.qty
        return po

    def map_reverse(self, po: OrderItemModel) -> OrderItem:
        return OrderItem(
            id=self.convert_str_to_id(po.id, id_type=EntityId) if po.id else None,
            sku=po.sku,
            qty=po.qty,
        )


class OrderMapper(BaseMapper[Order, OrderModel]):
    def __init__(self, **kw):
        super().__init__(Order, OrderModel, **kw)
        # 多外键自动回填：tenant_id / org_id / order_id
        self.register_child(
            "items", OrderItemMapper(**kw), parent_keys=["tenant_id", "org_id", "order_id"]
        )

    def map(self, d: Order) -> OrderModel:
        po = OrderModel()
        po.id = self.convert_id_to_str(d.id)
        po.tenant_id = d.tenant_id
        po.org_id = d.org_id
        po.status = self.convert_enum_to_str(d.status) or "NEW"
        po.items = self.map_children(d, po, "items", set_parent_keys=True)
        return po

    def map_reverse(self, po: OrderModel) -> Order:
        status = self.convert_str_to_enum(po.status, OrderStatus) or OrderStatus.NEW
        d = Order(
            id=self.convert_str_to_id(po.id, id_type=EntityId) if po.id else None,
            tenant_id=po.tenant_id,
            org_id=po.org_id,
            status=status,  # type: ignore[arg-type]
            items=self.map_reverse_children(po, "items"),
        )
        return d


# === 用法示例 ===
ctx = MappingContext(tenant_id="t-001", org_id="o-001")
order_mapper = OrderMapper(context=ctx)

domain_order = Order(
    id=EntityId("ord_123"),
    tenant_id="t-001",
    org_id="o-001",
    status=OrderStatus.NEW,
    items=[OrderItem(id=None, sku="SKU-1", qty=2)],
)

po_order = order_mapper.map(domain_order)
# 子项会被自动填充 tenant_id/org_id/order_id
print(po_order)
print(domain_order)
domain_order2 = order_mapper.map_reverse_with_events(po_order)
# 确保事件被清理
print(domain_order2)
