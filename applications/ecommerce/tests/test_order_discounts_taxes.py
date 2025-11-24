from decimal import Decimal

from applications.ecommerce.modules.order.domain.order import Discount, Money, Order, TaxLine
from applications.ecommerce.modules.order.persistence.mappers.order_mapper import OrderMapper
from bento.core.ids import ID


def test_discounts_and_taxes_roundtrip_and_total():
    mapper = OrderMapper()
    order = Order(order_id=ID("o-9009"), customer_id=ID("c-9"))
    order.currency = "USD"
    # add items to make total
    order.add_item(
        product_id=ID("p-1"),
        product_name="A",
        quantity=1,
        unit_price=Money(Decimal("100.00"), "USD"),
    )
    # add discount and tax lines
    order.discounts.append(Discount(amount=Money(Decimal("10.00"), "USD"), reason="promo"))
    order.tax_lines.append(TaxLine(amount=Money(Decimal("5.00"), "USD"), tax_type="state"))

    po = mapper.map(order)
    assert len(po.discounts) == 1
    assert len(po.tax_lines) == 1
    assert po.discounts[0].amount == Decimal("10.00")
    assert po.tax_lines[0].amount == Decimal("5.00")

    domain = mapper.map_reverse(po)
    assert len(domain.discounts) == 1
    assert len(domain.tax_lines) == 1
    assert domain.discounts[0].amount.amount == Decimal("10.00")
    assert domain.tax_lines[0].amount.amount == Decimal("5.00")
    # total = 100 - 10 + 5 = 95
    assert domain.total_money.amount == Decimal("95.00")
