"""OrderItem 聚合根单元测试"""

import pytest

from contexts.ordering.domain.models.orderitem import OrderItem


class TestOrderItem:
    """OrderItem 聚合根单元测试

    测试聚合根的不变量、业务规则和行为。
    遵循 AAA 模式：Arrange - Act - Assert
    """

    def test_create_valid_orderitem(self):
        """测试创建有效的实体"""
        # Arrange & Act
        orderitem = OrderItem(
            id="test-id-123",
            order_id="order-456",
            product_id="product-789",
            product_name="Test Product",
            quantity=2,
            unit_price=100.0,
        )

        # Assert
        assert orderitem.id == "test-id-123"
        assert orderitem.order_id == "order-456"
        assert orderitem.product_id == "product-789"
        assert orderitem.product_name == "Test Product"
        assert orderitem.quantity == 2
        assert orderitem.unit_price == 100.0
        assert orderitem.subtotal == 200.0

    def test_orderitem_invariants(self):
        """测试实体不变量"""
        # 产品ID不能为空
        with pytest.raises(ValueError, match="产品ID不能为空"):
            OrderItem(
                id="item-1",
                order_id="order-1",
                product_id="",
                product_name="Test",
                quantity=1,
                unit_price=100.0,
            )

        # 产品名称不能为空
        with pytest.raises(ValueError, match="产品名称不能为空"):
            OrderItem(
                id="item-1",
                order_id="order-1",
                product_id="product-1",
                product_name="",
                quantity=1,
                unit_price=100.0,
            )

        # 数量必须大于0
        with pytest.raises(ValueError, match="数量必须大于0"):
            OrderItem(
                id="item-1",
                order_id="order-1",
                product_id="product-1",
                product_name="Test",
                quantity=0,
                unit_price=100.0,
            )

        # 单价不能为负数
        with pytest.raises(ValueError, match="单价不能为负数"):
            OrderItem(
                id="item-1",
                order_id="order-1",
                product_id="product-1",
                product_name="Test",
                quantity=1,
                unit_price=-10.0,
            )

    def test_orderitem_business_rules(self):
        """测试业务规则"""
        orderitem = OrderItem(
            id="item-1",
            order_id="order-1",
            product_id="product-1",
            product_name="Test Product",
            quantity=2,
            unit_price=100.0,
        )

        # 测试更新数量
        orderitem.update_quantity(5)
        assert orderitem.quantity == 5
        assert orderitem.subtotal == 500.0

        # 测试更新价格
        orderitem.update_price(80.0)
        assert orderitem.unit_price == 80.0
        assert orderitem.subtotal == 400.0

        # 更新数量时数量必须大于0
        with pytest.raises(ValueError, match="数量必须大于0"):
            orderitem.update_quantity(0)

        # 更新价格时单价不能为负数
        with pytest.raises(ValueError, match="单价不能为负数"):
            orderitem.update_price(-10.0)

    def test_orderitem_subtotal_calculation(self):
        """测试小计计算"""
        orderitem = OrderItem(
            id="item-1",
            order_id="order-1",
            product_id="product-1",
            product_name="Test Product",
            quantity=3,
            unit_price=150.0,
        )

        assert orderitem.subtotal == 450.0
