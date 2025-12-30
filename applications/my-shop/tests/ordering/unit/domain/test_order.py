"""Order 聚合根单元测试"""

import pytest

from contexts.ordering.domain.models.order import Order


class TestOrder:
    """Order 聚合根单元测试

    测试聚合根的不变量、业务规则和行为。
    遵循 AAA 模式：Arrange - Act - Assert
    """

    def test_create_valid_order(self):
        """测试创建有效的聚合根"""
        # Arrange & Act
        order = Order(
            id="test-id-123",
            customer_id="customer-456",
        )

        # Assert
        assert order.id == "test-id-123"
        assert order.customer_id == "customer-456"
        assert order.total == 0.0
        assert order.items == []
        assert order.created_at is not None

    def test_order_invariants(self):
        """测试聚合根不变量"""
        # 订单必须至少有一个商品才能支付
        order = Order(id="order-123", customer_id="customer-456")

        with pytest.raises(ValueError, match="订单必须至少有一个商品"):
            order.confirm_payment()

    def test_order_business_rules(self):
        """测试业务规则"""
        # 测试添加订单项和总额计算
        order = Order(id="order-123", customer_id="customer-456")

        # 添加订单项
        order.add_item(
            product_id="product-1",
            product_name="Test Product",
            quantity=2,
            unit_price=100.0,
        )

        assert len(order.items) == 1
        assert order.total == 200.0

        # 添加第二个订单项
        order.add_item(
            product_id="product-2",
            product_name="Another Product",
            quantity=1,
            unit_price=50.0,
        )

        assert len(order.items) == 2
        assert order.total == 250.0

    def test_order_raises_domain_events(self):
        """测试领域事件发布"""
        from contexts.ordering.domain.events.orderpaid_event import OrderPaidEvent

        order = Order(id="order-123", customer_id="customer-456")
        order.add_item(
            product_id="product-1",
            product_name="Test Product",
            quantity=1,
            unit_price=100.0,
        )

        # 确认支付应该发布事件
        order.confirm_payment()
        events = order.events

        assert len(events) == 1
        assert isinstance(events[0], OrderPaidEvent)
        assert events[0].order_id == "order-123"
        assert events[0].customer_id == "customer-456"
        assert events[0].total == 100.0
