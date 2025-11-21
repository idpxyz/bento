"""User 仓储集成测试"""

import pytest

from contexts.identity.domain.models.user import User


@pytest.mark.integration
class TestUserRepository:
    """User 仓储集成测试

    测试仓储与实际数据库的交互。
    需要测试环境数据库支持。
    """

    @pytest.fixture
    async def repository(self, db_session):
        """仓储实例（需要实现数据库 fixture）"""
        # TODO: 创建实际的仓储实例
        # from contexts.identity.infrastructure.repositories.user_repository_impl import UserRepository
        # return UserRepository(session=db_session, actor="test-user")
        pytest.skip("需要实现数据库 fixture")

    @pytest.mark.asyncio
    async def test_save_and_get_user(self, repository):
        """测试保存和查询"""
        # Arrange
        user = User(
            id="test-id-123",
            # TODO: 添加字段
        )

        # Act
        await repository.save(user)
        retrieved = await repository.get("test-id-123")

        # Assert
        assert retrieved is not None
        assert retrieved.id == "test-id-123"
        # TODO: 验证其他字段

    @pytest.mark.asyncio
    async def test_delete_user(self, repository):
        """测试删除"""
        # Arrange
        user = User(id="test-delete-123")
        await repository.save(user)

        # Act
        await repository.delete("test-delete-123")

        # Assert
        retrieved = await repository.get("test-delete-123")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_users(self, repository):
        """测试列表查询"""
        # Arrange
        user_1 = User(id="list-test-1")
        user_2 = User(id="list-test-2")
        await repository.save(user_1)
        await repository.save(user_2)

        # Act
        results = await repository.list(limit=10)

        # Assert
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_exists_user(self, repository):
        """测试存在性检查"""
        # Arrange
        user = User(id="exists-test-123")
        await repository.save(user)

        # Act & Assert
        assert await repository.exists("exists-test-123") is True
        assert await repository.exists("non-existent-id") is False
