"""OrderItem 仓储集成测试"""
import pytest
from contexts.ordering.domain.orderitem import OrderItem


@pytest.mark.integration
class TestOrderItemRepository:
    """OrderItem 仓储集成测试

    测试仓储与实际数据库的交互。
    需要测试环境数据库支持。
    """

    @pytest.fixture
    async def repository(self, db_session):
        """仓储实例（需要实现数据库 fixture）"""
        # TODO: 创建实际的仓储实例
        # from contexts.ordering.infrastructure.repositories.orderitem_repository_impl import OrderItemRepository
        # return OrderItemRepository(session=db_session, actor="test-user")
        pytest.skip("需要实现数据库 fixture")

    @pytest.mark.asyncio
    async def test_save_and_get_orderitem(self, repository):
        """测试保存和查询"""
        # Arrange
        orderitem = OrderItem(
            id="test-id-123",
            # TODO: 添加字段
        )

        # Act
        await repository.save(orderitem)
        retrieved = await repository.get("test-id-123")

        # Assert
        assert retrieved is not None
        assert retrieved.id == "test-id-123"
        # TODO: 验证其他字段

    @pytest.mark.asyncio
    async def test_delete_orderitem(self, repository):
        """测试删除"""
        # Arrange
        orderitem = OrderItem(id="test-delete-123")
        await repository.save(orderitem)

        # Act
        await repository.delete("test-delete-123")

        # Assert
        retrieved = await repository.get("test-delete-123")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_orderitems(self, repository):
        """测试列表查询"""
        # Arrange
        orderitem_1 = OrderItem(id="list-test-1")
        orderitem_2 = OrderItem(id="list-test-2")
        await repository.save(orderitem_1)
        await repository.save(orderitem_2)

        # Act
        results = await repository.list(limit=10)

        # Assert
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_exists_orderitem(self, repository):
        """测试存在性检查"""
        # Arrange
        orderitem = OrderItem(id="exists-test-123")
        await repository.save(orderitem)

        # Act & Assert
        assert await repository.exists("exists-test-123") is True
        assert await repository.exists("non-existent-id") is False