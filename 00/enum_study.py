# === Domain 层 ===
from dataclasses import dataclass
from enum import Enum

from bento.application.mapper.base import BaseMapper
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
    status: OrderStatus
    items: list[OrderItem]
    _events: list[object] = None

    def clear_events(self):
        self._events = []


# === PO（ORM）层（以 SQLAlchemy 模型为例）===
class OrderModel:
    id: str | None
    status: str
    items: list["OrderItemModel"]


class OrderItemModel:
    id: str | None
    order_id: str | None
    sku: str
    qty: int


# === Mapper 实现 ===
class OrderItemMapper(BaseMapper[OrderItem, OrderItemModel]):
    parent_key = "order_id"  # 可在 __init__ 后赋值，也可通过 register_child 传入

    def __init__(self):
        super().__init__(OrderItem, OrderItemModel)

    def map(self, d: OrderItem) -> OrderItemModel:
        po = OrderItemModel()
        po.id = self.convert_id_to_str(d.id)
        po.sku = d.sku
        po.qty = d.qty
        return po

    def map_reverse(self, po: OrderItemModel) -> OrderItem:
        d = OrderItem(
            id=self.convert_str_to_id(po.id, id_type=EntityId) if po.id else None,
            sku=po.sku,
            qty=po.qty,
        )
        return d


class OrderMapper(BaseMapper[Order, OrderModel]):
    def __init__(self):
        super().__init__(Order, OrderModel)
        self.register_child("items", OrderItemMapper(), parent_keys="order_id")

    def map(self, d: Order) -> OrderModel:
        po = OrderModel()
        po.id = self.convert_id_to_str(d.id)
        po.status = self.convert_enum_to_str(d.status) or "NEW"
        po.items = self.map_children(d, po, "items")
        return po

    def map_reverse(self, po: OrderModel) -> Order:
        d = Order(
            id=self.convert_str_to_id(po.id, id_type=EntityId) if po.id else None,
            status=self.convert_str_to_enum(po.status, OrderStatus) or OrderStatus.NEW,
            items=self.map_reverse_children(po, "items"),
        )
        self.auto_clear_events(d)  # 当前需要手动调用
        return d
