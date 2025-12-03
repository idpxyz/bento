"""{{Action}}{{Name}} Command Handler 单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from contexts.{{context}}.application.commands.{{action_lower}}_{{name_lower}} import (
    {{Action}}{{Name}}Command,
    {{Action}}{{Name}}Handler,
)


class Test{{Action}}{{Name}}Handler:
    """{{Action}}{{Name}} Command Handler 单元测试
    
    测试 Command Handler 的业务流程编排逻辑（CQRS 写操作）。
    使用 Mock 隔离依赖（Repository、UnitOfWork 等）。
    
    测试原则：
    - Command 修改系统状态
    - 应该触发领域事件
    - 需要事务保护
    - 验证副作用（保存、更新、删除）
    """

    @pytest.fixture
    def mock_repository(self):
        """Mock Repository"""
        repo = AsyncMock()
        repo.save = AsyncMock()
        repo.get = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def mock_uow(self, mock_repository):
        """Mock Unit of Work"""
        uow = MagicMock()
        uow.repository = MagicMock(return_value=mock_repository)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        return uow

    @pytest.fixture
    def handler(self, mock_uow):
        """Command Handler 实例"""
        return {{Action}}{{Name}}Handler(uow=mock_uow)

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_success(
        self, handler, mock_repository, mock_uow
    ):
        """测试成功场景 - Command 应该修改状态并返回成功结果"""
        # Arrange
        command = {{Action}}{{Name}}Command(
            # TODO: 添加命令字段
            # name="Test Product",
            # price=99.99,
        )
        
        # Mock 返回值
        # mock_repository.save.return_value = mock_{{name_lower}}
        # mock_repository.get.return_value = mock_{{name_lower}}

        # Act
        result = await handler.execute(command)

        # Assert - 验证结果
        assert result.is_success
        # assert result.data is not None
        
        # Assert - 验证副作用
        # mock_repository.save.assert_called_once()
        # mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_validation_failure(self, handler):
        """测试验证失败场景 - 无效数据应该返回失败结果"""
        # Arrange - 创建无效命令
        invalid_command = {{Action}}{{Name}}Command(
            # TODO: 添加无效的命令数据
            # name="",  # 空名称
            # price=-10,  # 负价格
        )

        # Act
        result = await handler.execute(invalid_command)

        # Assert - 应该返回失败结果
        assert not result.is_success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_transaction_rollback(
        self, handler, mock_repository, mock_uow
    ):
        """测试事务回滚 - 异常时应该回滚事务"""
        # Arrange
        command = {{Action}}{{Name}}Command(
            # TODO: 添加命令数据
        )
        
        # Mock repository 抛出异常
        mock_repository.save.side_effect = Exception("Database error")

        # Act
        result = await handler.execute(command)

        # Assert - 应该返回失败并回滚
        assert not result.is_success
        # mock_uow.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_domain_events(
        self, handler, mock_repository, mock_uow
    ):
        """测试领域事件 - Command 应该触发领域事件"""
        # Arrange
        command = {{Action}}{{Name}}Command(
            # TODO: 添加命令数据
        )

        # Act
        result = await handler.execute(command)

        # Assert - 验证领域事件被记录
        # TODO: 验证聚合根收集的事件
        # assert len(aggregate.events) > 0
        # assert isinstance(aggregate.events[0], {{Name}}{{Action}}Event)
        pass

    @pytest.mark.asyncio
    async def test_{{action_lower}}_{{name_lower}}_idempotency(self, handler):
        """测试幂等性 - 相同命令多次执行应该产生相同结果"""
        # Arrange
        command = {{Action}}{{Name}}Command(
            # TODO: 添加命令数据（带唯一标识）
            # idempotency_key="unique-key-123",
        )

        # Act - 执行两次
        result1 = await handler.execute(command)
        result2 = await handler.execute(command)

        # Assert - 结果应该相同
        # assert result1.data == result2.data
        pass
