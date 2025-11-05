"""Tests for order domain logic."""

import pytest
from datetime import datetime

from bento.core.ids import ID
from bento.core.errors import DomainException
from applications.ecommerce.modules.order.domain.order import Order, OrderItem
from applications.ecommerce.modules.order.domain.order_status import OrderStatus
from applications.ecommerce.modules.order.errors import OrderErrors


def test_create_order():
    """Test creating a new order."""
    order_id = ID.generate()
    customer_id = ID.generate()
    
    order = Order(order_id=order_id, customer_id=customer_id)
    
    assert order.id == order_id
    assert order.customer_id == customer_id
    assert order.status == OrderStatus.PENDING
    assert order.items == []
    assert order.total_amount == 0.0
    assert len(order.events) == 1  # OrderCreated event


def test_add_item_to_order():
    """Test adding items to an order."""
    order = Order(order_id=ID.generate(), customer_id=ID.generate())
    
    order.add_item(
        product_id=ID.generate(),
        product_name="iPhone 15 Pro",
        quantity=2,
        unit_price=999.99
    )
    
    assert len(order.items) == 1
    assert order.items[0].product_name == "iPhone 15 Pro"
    assert order.items[0].quantity == 2
    assert order.items[0].unit_price == 999.99
    assert order.total_amount == 1999.98


def test_add_item_with_invalid_quantity():
    """Test that adding item with invalid quantity raises error."""
    order = Order(order_id=ID.generate(), customer_id=ID.generate())
    
    with pytest.raises(DomainException) as exc_info:
        order.add_item(
            product_id=ID.generate(),
            product_name="Product",
            quantity=0,  # Invalid
            unit_price=10.0
        )
    
    assert exc_info.value.error_code == OrderErrors.INVALID_QUANTITY


def test_pay_order():
    """Test paying for an order."""
    order = Order(order_id=ID.generate(), customer_id=ID.generate())
    order.add_item(
        product_id=ID.generate(),
        product_name="Product",
        quantity=1,
        unit_price=100.0
    )
    
    order.pay()
    
    assert order.status == OrderStatus.PAID
    assert order.paid_at is not None
    assert len(order.events) == 2  # OrderCreated + OrderPaid


def test_cannot_pay_empty_order():
    """Test that paying empty order raises error."""
    order = Order(order_id=ID.generate(), customer_id=ID.generate())
    
    with pytest.raises(DomainException) as exc_info:
        order.pay()
    
    assert exc_info.value.error_code == OrderErrors.EMPTY_ORDER_ITEMS


def test_cannot_pay_twice():
    """Test that paying twice raises error."""
    order = Order(order_id=ID.generate(), customer_id=ID.generate())
    order.add_item(
        product_id=ID.generate(),
        product_name="Product",
        quantity=1,
        unit_price=100.0
    )
    
    order.pay()
    
    with pytest.raises(DomainException) as exc_info:
        order.pay()
    
    assert exc_info.value.error_code == OrderErrors.ORDER_ALREADY_PAID


def test_cancel_order():
    """Test cancelling an order."""
    order = Order(order_id=ID.generate(), customer_id=ID.generate())
    order.add_item(
        product_id=ID.generate(),
        product_name="Product",
        quantity=1,
        unit_price=100.0
    )
    
    order.cancel(reason="Customer request")
    
    assert order.status == OrderStatus.CANCELLED
    assert order.cancelled_at is not None
    assert len(order.events) == 2  # OrderCreated + OrderCancelled


def test_cannot_cancel_paid_order():
    """Test that cancelling paid order raises error."""
    order = Order(order_id=ID.generate(), customer_id=ID.generate())
    order.add_item(
        product_id=ID.generate(),
        product_name="Product",
        quantity=1,
        unit_price=100.0
    )
    order.pay()
    
    with pytest.raises(DomainException) as exc_info:
        order.cancel()
    
    assert exc_info.value.error_code == OrderErrors.ORDER_ALREADY_PAID


def test_order_status_transitions():
    """Test order status transition validation."""
    # PENDING can transition to PAID or CANCELLED
    assert OrderStatus.PENDING.can_transition_to(OrderStatus.PAID)
    assert OrderStatus.PENDING.can_transition_to(OrderStatus.CANCELLED)
    assert not OrderStatus.PENDING.can_transition_to(OrderStatus.SHIPPED)
    
    # PAID can transition to SHIPPED or REFUNDED
    assert OrderStatus.PAID.can_transition_to(OrderStatus.SHIPPED)
    assert OrderStatus.PAID.can_transition_to(OrderStatus.REFUNDED)
    assert not OrderStatus.PAID.can_transition_to(OrderStatus.CANCELLED)
    
    # CANCELLED is terminal
    assert not OrderStatus.CANCELLED.can_transition_to(OrderStatus.PAID)
    assert not OrderStatus.CANCELLED.can_transition_to(OrderStatus.SHIPPED)


def test_order_to_dict():
    """Test converting order to dictionary."""
    order = Order(order_id=ID.generate(), customer_id=ID.generate())
    order.add_item(
        product_id=ID.generate(),
        product_name="Product A",
        quantity=2,
        unit_price=50.0
    )
    
    data = order.to_dict()
    
    assert "id" in data
    assert "customer_id" in data
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["items_count"] == 1
    assert data["total_amount"] == 100.0
    assert "created_at" in data

