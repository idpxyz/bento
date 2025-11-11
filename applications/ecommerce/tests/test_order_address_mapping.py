from applications.ecommerce.modules.order.domain.order import Address, Order
from applications.ecommerce.modules.order.persistence.mappers.order_mapper import OrderMapper
from bento.core.ids import ID


def test_shipping_address_roundtrip():
    mapper = OrderMapper()
    order = Order(order_id=ID("o-7007"), customer_id=ID("c-700"))
    order.shipping_address = Address(line1="1 Infinite Loop", city="Cupertino", country="US")

    po = mapper.map(order)
    assert po.shipping_address_line1 == "1 Infinite Loop"
    assert po.shipping_city == "Cupertino"
    assert po.shipping_country == "US"

    domain = mapper.map_reverse(po)
    assert domain.shipping_address is not None
    assert domain.shipping_address.line1 == "1 Infinite Loop"
    assert domain.shipping_address.city == "Cupertino"
    assert domain.shipping_address.country == "US"
