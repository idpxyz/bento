from dataclasses import dataclass

from bento.application.mappers import AutoMapper


@dataclass
class OrderItem:
    id: str
    name: str


@dataclass
class OrderItemModel:
    id: str
    name: str
    order_id: str | None = None


@dataclass
class Order:
    id: str
    items: list[OrderItem]


@dataclass
class OrderModel:
    id: str
    items: list[OrderItemModel]


class ItemMapper(AutoMapper[OrderItem, OrderItemModel]):
    def __init__(self) -> None:
        super().__init__(OrderItem, OrderItemModel)
        # order_id is set by parent via parent_keys
        self.ignore_fields("order_id")


class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self) -> None:
        super().__init__(Order, OrderModel)
        self.register_child("items", ItemMapper(), parent_keys="order_id")


def test_auto_children_mapping_forward_and_reverse():
    order = Order(
        id="ord_1",
        items=[OrderItem(id="i1", name="A"), OrderItem(id="i2", name="B")],
    )

    mapper = OrderMapper()

    po = mapper.map(order)
    assert isinstance(po, OrderModel)
    assert isinstance(po.items, list)
    assert len(po.items) == 2
    assert {c.id for c in po.items} == {"i1", "i2"}
    # parent_keys set on children
    assert all(c.order_id == order.id for c in po.items)

    # Reverse mapping
    domain2 = mapper.map_reverse(po)
    assert isinstance(domain2, Order)
    assert len(domain2.items) == 2
    assert {c.id for c in domain2.items} == {"i1", "i2"}
    assert {c.name for c in domain2.items} == {"A", "B"}
