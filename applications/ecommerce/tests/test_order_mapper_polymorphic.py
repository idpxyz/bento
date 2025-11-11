from datetime import datetime

from applications.ecommerce.modules.order.domain.order import (
    Order,
    OrderItem,
    PaymentCard,
    ShipmentFedex,
)
from applications.ecommerce.modules.order.domain.order_status import OrderStatus
from applications.ecommerce.modules.order.persistence.mappers.order_mapper import (
    OrderItemMapper,
    OrderMapper,
)
from applications.ecommerce.modules.order.persistence.models.order_model import OrderItemModel
from bento.core.ids import ID


def test_order_mapper_payment_and_shipment_fields_roundtrip():
    mapper = OrderMapper()

    order = Order(order_id=ID("o-1001"), customer_id=ID("c-9"))
    order.payment_method = "card"
    order.payment_card_last4 = "4242"
    order.payment_card_brand = "VISA"
    order.shipment_carrier = "fedex"
    order.shipment_tracking_no = "FX123"
    order.shipment_service = "PRIORITY"
    order.status = OrderStatus.PAID
    order.paid_at = datetime.utcnow()

    po = mapper.map(order)
    assert po.payment_method == "card"
    assert po.payment_card_last4 == "4242"
    assert po.payment_card_brand == "VISA"
    assert po.shipment_carrier == "fedex"
    assert po.shipment_tracking_no == "FX123"
    assert po.shipment_service == "PRIORITY"

    domain = mapper.map_reverse(po)
    assert domain.payment_method == "card"
    assert domain.payment_card_last4 == "4242"
    assert domain.payment_card_brand == "VISA"
    assert domain.shipment_carrier == "fedex"
    assert domain.shipment_tracking_no == "FX123"
    assert domain.shipment_service == "PRIORITY"


def test_order_item_mapper_sets_default_kind():
    mapper = OrderItemMapper()
    item = OrderItem(product_id=ID("p-1"), product_name="X", quantity=1, unit_price=10.0)
    po = mapper.map(item)
    assert isinstance(po, OrderItemModel)
    assert po.kind == "simple"


def test_order_mapper_infers_discriminators_when_missing():
    mapper = OrderMapper()

    order = Order(order_id=ID("o-2002"), customer_id=ID("c-1"))
    # Only set card fields, payment_method left None -> should infer "card"
    order.payment_card_last4 = "1111"
    order.payment_card_brand = "VISA"
    # Only set tracking, shipment_carrier left None -> should infer "fedex"
    order.shipment_tracking_no = "TRK123"

    po = mapper.map(order)
    assert po.payment_method == "card"
    assert po.shipment_carrier == "fedex"  # naive default by heuristic


def test_order_mapper_explicit_objects_roundtrip():
    mapper = OrderMapper()
    order = Order(order_id=ID("o-3003"), customer_id=ID("c-2"))
    order.payment = PaymentCard(last4="9999", brand="MASTER")
    order.shipment = ShipmentFedex(tracking_no="FX-999", service="PRIORITY")

    po = mapper.map(order)
    assert po.payment_method == "card"
    assert po.payment_card_last4 == "9999"
    assert po.payment_card_brand == "MASTER"
    assert po.shipment_carrier == "fedex"
    assert po.shipment_tracking_no == "FX-999"
    assert po.shipment_service == "PRIORITY"

    domain = mapper.map_reverse(po)
    assert isinstance(domain.payment, PaymentCard)
    assert domain.payment.last4 == "9999"
    assert domain.payment.brand == "MASTER"
    assert isinstance(domain.shipment, ShipmentFedex)
    assert domain.shipment.tracking_no == "FX-999"
