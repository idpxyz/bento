"""CreateCategory 用例"""
from dataclasses import dataclass


@dataclass
class CreateCategoryCommand:
    """CreateCategory 命令

    命令对象封装用户意图，包含执行操作所需的所有数据。
    遵循 CQRS 模式，命令不返回业务数据。
    """
    # TODO: 添加命令字段
    # 例如:
    # name: str
    # email: str
    # age: int
    pass


class CreateCategoryUseCase:
    """CreateCategory 用例

    应用层用例编排业务流程，协调领域对象完成业务逻辑。

    职责：
    1. 验证命令参数
    2. 加载领域对象
    3. 执行业务逻辑
    4. 持久化结果
    5. 发布领域事件

    依赖注入：
    - 仓储接口（从 domain 层获取协议）
    - 工作单元（事务管理）
    """

    def __init__(self, repository, unit_of_work):
        """
        参数：
            repository: ICategoryRepository - 仓储协议实例
            unit_of_work: IUnitOfWork - 工作单元协议实例
        """
        self._repository = repository
        self._uow = unit_of_work

    async def validate(self, command: CreateCategoryCommand) -> None:
        """验证命令（可选）

        在执行前验证业务规则，例如：
        - 必填字段检查
        - 格式验证（邮箱、手机号等）
        - 业务约束检查（唯一性、范围等）
        """
        # TODO: 添加验证逻辑
        pass

    async def execute(self, command: CreateCategoryCommand) -> str:
        """执行用例

        返回：
            聚合根ID（字符串类型）
        """
        await self.validate(command)

        async with self._uow:
            # TODO: 实现业务逻辑
            # 示例（Create 操作）:
            # from contexts.catalog.domain.category import Category
            # category = Category(
            #     id=generate_id(),
            #     name=command.name,
            #     email=command.email
            # )
            # await self._repository.save(category)
            # await self._uow.commit()
            # return category.id

            raise NotImplementedError("Please implement business logic")


# ============================================================================
# 使用框架 BaseUseCase 的实现示例（可选）
# ============================================================================
#
# from bento.application.usecase import BaseUseCase
# from bento.core.ids import ID
#
# class CreateCategoryUseCase(BaseUseCase[CreateCategoryCommand, ID]):
#     """使用 Bento 框架 BaseUseCase
#
#     框架自动提供：
#     - 事务管理（通过 self.uow）
#     - 事件收集和发布（通过 Outbox）
#     - 错误处理和回滚
#     - 幂等性支持（可选）
#     """
#
#     async def handle(self, command: CreateCategoryCommand) -> ID:
#         repo = self.uow.repository(Category)
#         category = Category(...)
#         await repo.save(category)
#         return category.id
#