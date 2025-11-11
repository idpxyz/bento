from decimal import Decimal

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.persistence.mappers.order_mapper import OrderMapper
from bento.core.ids import ID


def test_order_discount_and_tax_decimal_roundtrip():
    mapper = OrderMapper()
    order = Order(order_id=ID("o-5005"), customer_id=ID("c-77"))
    order.discount_amount = Decimal("12.34")
    order.tax_amount = Decimal("5.66")

    po = mapper.map(order)
    # Stored as string for precision
    assert po.discount_amount == "12.34"
    assert po.tax_amount == "5.66"

    domain = mapper.map_reverse(po)
    assert domain.discount_amount == Decimal("12.34")
    assert domain.tax_amount == Decimal("5.66")
