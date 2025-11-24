from decimal import Decimal

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.persistence.mappers.order_mapper import OrderMapper
from bento.core.ids import ID


def test_total_money_uses_order_currency():
    mapper = OrderMapper()
    order = Order(order_id=ID("o-8008"), customer_id=ID("c-8"))
    order.currency = "CNY"
    order.add_item(product_id=ID("p-1"), product_name="A", quantity=2, unit_price=Decimal("10.00"))
    order.add_item(product_id=ID("p-2"), product_name="B", quantity=1, unit_price=Decimal("5.50"))

    assert order.total_money.amount == Decimal("25.50")
    assert order.total_money.currency == "CNY"

    po = mapper.map(order)
    assert po.currency == "CNY"

    domain = mapper.map_reverse(po)
    assert domain.currency == "CNY"
