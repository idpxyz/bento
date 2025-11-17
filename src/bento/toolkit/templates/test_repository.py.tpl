"""{{Name}} 仓储集成测试"""
import pytest
from contexts.{{context}}.domain.{{name_lower}} import {{Name}}


@pytest.mark.integration
class Test{{Name}}Repository:
    """{{Name}} 仓储集成测试

    测试仓储与实际数据库的交互。
    需要测试环境数据库支持。
    """

    @pytest.fixture
    async def repository(self, db_session):
        """仓储实例（需要实现数据库 fixture）"""
        # TODO: 创建实际的仓储实例
        # from infrastructure.repositories.{{name_lower}}_repository_impl import {{Name}}Repository
        # return {{Name}}Repository(session=db_session, actor="test-user")
        pytest.skip("需要实现数据库 fixture")

    @pytest.mark.asyncio
    async def test_save_and_get_{{name_lower}}(self, repository):
        """测试保存和查询"""
        # Arrange
        {{name_lower}} = {{Name}}(
            id="test-id-123",
            # TODO: 添加字段
        )

        # Act
        await repository.save({{name_lower}})
        retrieved = await repository.get("test-id-123")

        # Assert
        assert retrieved is not None
        assert retrieved.id == "test-id-123"
        # TODO: 验证其他字段

    @pytest.mark.asyncio
    async def test_delete_{{name_lower}}(self, repository):
        """测试删除"""
        # Arrange
        {{name_lower}} = {{Name}}(id="test-delete-123")
        await repository.save({{name_lower}})

        # Act
        await repository.delete("test-delete-123")

        # Assert
        retrieved = await repository.get("test-delete-123")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_{{name_lower}}s(self, repository):
        """测试列表查询"""
        # Arrange
        {{name_lower}}_1 = {{Name}}(id="list-test-1")
        {{name_lower}}_2 = {{Name}}(id="list-test-2")
        await repository.save({{name_lower}}_1)
        await repository.save({{name_lower}}_2)

        # Act
        results = await repository.list(limit=10)

        # Assert
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_exists_{{name_lower}}(self, repository):
        """测试存在性检查"""
        # Arrange
        {{name_lower}} = {{Name}}(id="exists-test-123")
        await repository.save({{name_lower}})

        # Act & Assert
        assert await repository.exists("exists-test-123") is True
        assert await repository.exists("non-existent-id") is False
