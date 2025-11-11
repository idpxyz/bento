from decimal import Decimal

from applications.ecommerce.modules.order.domain.order import (
    LineBundle,
    LineCustom,
    LineSimple,
    Money,
    Order,
)
from applications.ecommerce.modules.order.persistence.mappers.order_mapper import OrderMapper
from bento.core.ids import ID


def test_default_simple_line_maps_kind_simple_and_roundtrip():
    mapper = OrderMapper()
    order = Order(order_id=ID("o-1"), customer_id=ID("c-1"))
    order.currency = "USD"
    order.items.append(
        LineSimple(
            product_id=ID("p-1"),
            product_name="Simple",
            quantity=1,
            unit_price=Money(Decimal("10.00"), "USD"),
        )
    )
    po = mapper.map(order)
    assert po.items[0].kind == "simple"
    domain = mapper.map_reverse(po)
    assert isinstance(domain.items[0], LineSimple)


def test_bundle_line_maps_kind_bundle_and_roundtrip():
    mapper = OrderMapper()
    order = Order(order_id=ID("o-2"), customer_id=ID("c-2"))
    order.currency = "USD"
    order.items.append(
        LineBundle(
            product_id=ID("p-2"),
            product_name="Bundle",
            quantity=2,
            unit_price=Money(Decimal("5.00"), "USD"),
        )
    )
    po = mapper.map(order)
    assert po.items[0].kind == "bundle"
    domain = mapper.map_reverse(po)
    assert isinstance(domain.items[0], LineBundle)


def test_reverse_from_custom_kind_builds_LineCustom():
    mapper = OrderMapper()
    order = Order(order_id=ID("o-3"), customer_id=ID("c-3"))
    order.currency = "USD"
    # start with simple, then mutate PO to custom to simulate read from DB
    order.items.append(
        LineSimple(
            product_id=ID("p-3"),
            product_name="X",
            quantity=1,
            unit_price=Money(Decimal("1.00"), "USD"),
        )
    )
    po = mapper.map(order)
    po.items[0].kind = "custom"
    domain = mapper.map_reverse(po)
    assert isinstance(domain.items[0], LineCustom)
