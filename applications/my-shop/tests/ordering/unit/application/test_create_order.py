"""CreateOrder 用例单元测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from bento.adapters.observability.noop import NoOpObservabilityProvider

from contexts.ordering.application.commands.create_order import (
    CreateOrderCommand,
    CreateOrderHandler,
    OrderItemInput,
)


class TestCreateOrderHandler:
    """CreateOrder 用例单元测试

    测试用例的业务流程编排逻辑。
    使用 Mock 隔离依赖（仓储、工作单元等）。
    """

    @pytest.fixture
    def mock_uow(self):
        """Mock 工作单元"""
        uow = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        uow.commit = AsyncMock()  # ✅ 添加 commit 方法

        # 创建一个 Mock Repository 并设置所需的异步方法
        mock_repo = MagicMock()
        mock_repo.save = AsyncMock()
        uow.repository = MagicMock(return_value=mock_repo)
        return uow

    @pytest.fixture
    def mock_product_catalog(self):
        """Mock 产品目录服务（反腐败层）"""
        return AsyncMock()

    @pytest.fixture
    def mock_observability(self):
        """Mock observability provider"""
        return NoOpObservabilityProvider()

    @pytest.fixture
    def usecase(self, mock_uow, mock_observability):
        """用例实例"""
        # Handler 需要 uow 和 observability 参数
        return CreateOrderHandler(uow=mock_uow, observability=mock_observability)

    @pytest.mark.asyncio
    async def test_create_order_success(self, usecase, mock_product_catalog, mock_uow):
        """测试成功场景 - 所有产品可用"""
        # Arrange
        command = CreateOrderCommand(
            customer_id="customer-001",
            items=[
                OrderItemInput(
                    product_id="product-001",
                    product_name="Product A",
                    quantity=2,
                    unit_price=100.0,
                )
            ],
        )

        # Mock product_catalog 通过 uow.port() 获取
        mock_product_catalog.check_products_available = AsyncMock(return_value=(
            ["product-001"],  # available
            [],  # unavailable
        ))
        mock_uow.port = MagicMock(return_value=mock_product_catalog)

        # Mock 仓储
        mock_repo = AsyncMock()
        mock_uow.repository.return_value = mock_repo

        # Act
        result = await usecase.execute(command)

        # Assert
        assert result is not None
        assert result.customer_id == "customer-001"
        assert len(result.items) == 1
        assert result.total == 200.0
        mock_product_catalog.check_products_available.assert_called_once_with(["product-001"])
        mock_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_product_not_found(self, usecase, mock_product_catalog, mock_uow):
        """测试产品不存在的场景"""
        # Arrange
        command = CreateOrderCommand(
            customer_id="customer-001",
            items=[
                OrderItemInput(
                    product_id="nonexistent-product",
                    product_name="Product X",
                    quantity=1,
                    unit_price=100.0,
                )
            ],
        )

        # Mock product_catalog 通过 uow.port() 获取
        mock_product_catalog.check_products_available = AsyncMock(return_value=(
            [],  # available
            ["nonexistent-product"],  # unavailable
        ))
        mock_uow.port = MagicMock(return_value=mock_product_catalog)

        # Act & Assert
        from bento.core.exceptions import ApplicationException

        with pytest.raises(ApplicationException) as exc_info:
            await usecase.execute(command)

        assert "nonexistent-product" in str(exc_info.value.details)

    @pytest.mark.asyncio
    async def test_create_order_validation_failure(self, usecase):
        """测试验证失败场景 - 空订单项"""
        # Arrange
        invalid_command = CreateOrderCommand(
            customer_id="customer-001",
            items=[],  # 空订单项列表
        )

        # Act & Assert
        from bento.core.exceptions import ApplicationException

        with pytest.raises(ApplicationException) as exc_info:
            await usecase.execute(invalid_command)

        assert "items" in str(exc_info.value.details)

    @pytest.mark.asyncio
    async def test_create_order_transaction_rollback(self, usecase, mock_uow):
        """测试事务回滚"""
        # TODO: 测试异常时事务回滚
        # 模拟仓储抛出异常，验证工作单元回滚
        pass
