"""{{Action}}{{Name}} Query Handler 单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from contexts.{{context}}.application.queries.{{action_lower}}_{{name_lower}} import (
    {{Action}}{{Name}}Query,
    {{Action}}{{Name}}Handler,
    {{Name}}Response,
)


class Test{{Action}}{{Name}}Handler:
    """{{Action}}{{Name}} Query Handler 单元测试
    
    测试 Query Handler 的数据读取逻辑（CQRS 读操作）。
    使用 Mock 隔离依赖（Repository、UnitOfWork 等）。
    
    测试原则：
    - Query 只读，不修改状态
    - 不触发领域事件
    - 不需要事务（除非读取一致性要求高）
    - 返回 DTO，不返回聚合根
    - 可以直接查询优化的读模型
    """

    @pytest.fixture
    def mock_repository(self):
        """Mock Repository"""
        repo = AsyncMock()
        repo.get = AsyncMock()
        repo.find_all = AsyncMock()
        repo.find_page = AsyncMock()
        return repo

    @pytest.fixture
    def mock_uow(self, mock_repository):
        """Mock Unit of Work"""
        uow = MagicMock()
        uow.repository = MagicMock(return_value=mock_repository)
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        return uow

    @pytest.fixture
    def handler(self, mock_uow):
        """Query Handler 实例"""
        return {{Action}}{{Name}}Handler(uow=mock_uow)

    @pytest.fixture
    def mock_{{name_lower}}(self):
        """Mock {{Name}} 聚合根"""
        from contexts.{{context}}.domain.model.{{name_lower}} import {{Name}}
        
        mock = MagicMock(spec={{Name}})
        mock.id = "{{name_lower}}-123"
        # TODO: 添加其他字段
        # mock.name = "Test {{Name}}"
        # mock.price = 99.99
        return mock

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_success(
        self, handler, mock_repository, mock_{{name_lower}}
    ):
        """测试成功场景 - Query 应该返回 DTO 数据"""
        # Arrange
        query = {{Action}}{{Name}}Query(
            # TODO: 添加查询参数
            # {{name_lower}}_id="{{name_lower}}-123",
        )
        
        # Mock repository 返回数据
        mock_repository.get.return_value = mock_{{name_lower}}

        # Act
        result = await handler.handle(query)

        # Assert - 验证返回 DTO
        assert isinstance(result, {{Name}}Response)
        # assert result.id == "{{name_lower}}-123"
        # assert result.name == "Test {{Name}}"
        
        # Assert - 验证只读取数据（没有修改）
        mock_repository.get.assert_called_once()
        # mock_repository.save.assert_not_called()  # Query 不应该保存

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_not_found(
        self, handler, mock_repository
    ):
        """测试未找到场景 - Query 应该抛出异常或返回 None"""
        # Arrange
        query = {{Action}}{{Name}}Query(
            # TODO: 添加查询参数
            # {{name_lower}}_id="non-existent-id",
        )
        
        # Mock repository 返回 None
        mock_repository.get.return_value = None

        # Act & Assert
        with pytest.raises(Exception):  # TODO: 使用具体的异常类型
            await handler.handle(query)

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_list(
        self, handler, mock_repository, mock_{{name_lower}}
    ):
        """测试列表查询 - Query 应该返回 DTO 列表"""
        # Arrange - 只在 List 类型的 Query 中使用
        if "{{Action}}" == "List":
            query = {{Action}}{{Name}}Query(
                # TODO: 添加过滤参数
                # category="electronics",
                # min_price=10.0,
            )
            
            # Mock repository 返回列表
            mock_repository.find_all.return_value = [mock_{{name_lower}}, mock_{{name_lower}}]

            # Act
            result = await handler.handle(query)

            # Assert
            # assert isinstance(result, list)
            # assert len(result) == 2
            # assert all(isinstance(item, {{Name}}Response) for item in result)

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_pagination(
        self, handler, mock_repository, mock_{{name_lower}}
    ):
        """测试分页查询 - Query 应该支持分页"""
        # Arrange - 只在支持分页的 Query 中使用
        if "{{Action}}" == "List":
            from bento.persistence.pagination import Page, PageParams
            
            query = {{Action}}{{Name}}Query(
                # TODO: 添加分页参数
                # page=1,
                # size=20,
            )
            
            # Mock repository 返回分页数据
            page_result = Page(
                items=[mock_{{name_lower}}, mock_{{name_lower}}],
                total=2,
                page=1,
                size=20,
            )
            mock_repository.find_page.return_value = page_result

            # Act
            result = await handler.handle(query)

            # Assert
            # assert result.total == 2
            # assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_no_side_effects(
        self, handler, mock_repository, mock_{{name_lower}}
    ):
        """测试无副作用 - Query 不应该修改任何数据"""
        # Arrange
        query = {{Action}}{{Name}}Query(
            # TODO: 添加查询参数
        )
        mock_repository.get.return_value = mock_{{name_lower}}

        # Act
        await handler.handle(query)

        # Assert - Query 不应该调用任何写操作
        mock_repository.save.assert_not_called()
        mock_repository.delete.assert_not_called()
        # TODO: 验证没有触发领域事件

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_dto_conversion(
        self, handler, mock_repository, mock_{{name_lower}}
    ):
        """测试 DTO 转换 - 聚合根应该正确转换为 DTO"""
        # Arrange
        query = {{Action}}{{Name}}Query(
            # TODO: 添加查询参数
        )
        mock_repository.get.return_value = mock_{{name_lower}}

        # Act
        result = await handler.handle(query)

        # Assert - 验证 DTO 包含正确的数据
        assert isinstance(result, {{Name}}Response)
        # TODO: 验证所有必要字段都被正确转换
        # assert result.id == mock_{{name_lower}}.id
        # assert result.name == mock_{{name_lower}}.name
