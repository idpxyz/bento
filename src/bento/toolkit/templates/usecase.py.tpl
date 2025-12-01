"""{{Action}}{{Name}} 用例 - 遵循 Bento Framework 标准"""
from dataclasses import dataclass

from bento.application import ApplicationService, ApplicationServiceResult
from bento.persistence.uow import UnitOfWork


@dataclass
class {{Action}}{{Name}}Command:
    """{{Action}}{{Name}} 命令

    命令对象封装用户意图，包含执行操作所需的所有数据。
    遵循 CQRS 模式，命令不返回业务数据。
    """
    # TODO: 添加命令字段
    # 例如:
    # name: str
    # email: str
    # age: int
    pass


@dataclass
class {{Name}}Result:
    """{{Name}} 操作结果"""
    {{name_lower}}_id: str
    # TODO: 添加其他结果字段

    @classmethod
    def from_aggregate(cls, {{name_lower}}):
        """从聚合根创建结果"""
        return cls({{name_lower}}_id=str({{name_lower}}.id))


class {{Action}}{{Name}}UseCase(ApplicationService[{{Action}}{{Name}}Command, {{Name}}Result]):
    """{{Action}}{{Name}} 用例

    应用层用例编排业务流程，协调领域对象完成业务逻辑。

    职责：
    1. 验证命令参数
    2. 加载领域对象
    3. 执行业务逻辑
    4. 持久化结果
    5. 发布领域事件

    遵循 Bento Framework 标准：
    - 使用 UnitOfWork 进行事务管理
    - 返回 ApplicationServiceResult 统一结果格式
    - 自动事件发布和错误处理
    """

    def __init__(self, uow: UnitOfWork):
        """初始化用例

        参数：
            uow: UnitOfWork - Bento Framework 统一工作单元
        """
        super().__init__(uow)

    async def handle(self, command: {{Action}}{{Name}}Command) -> {{Name}}Result:
        """处理业务逻辑 - 纯业务逻辑，框架自动处理事务和错误

        返回：
            {{Name}}Result - 业务结果（框架会自动包装为ApplicationServiceResult）
        """
        # 纯业务逻辑 - 框架自动处理UoW、验证、错误包装
        {{name_lower}}_repo = self.uow.repository({{Name}})

        # TODO: 实现业务逻辑
        # 示例（Create 操作）:
        # from contexts.{{context}}.domain.{{name_lower}} import {{Name}}
        # {{name_lower}} = {{Name}}.create_new(
        #     name=command.name,
        #     email=command.email
        # )
        #
        # # 应用业务规则（如果需要）
        # # {{Name}}DomainService.validate_creation({{name_lower}})
        #
        # # 保存聚合根
        # saved_{{name_lower}} = await {{name_lower}}_repo.save({{name_lower}})
        #
        # # 返回业务结果（框架自动commit和包装）
        # return {{Name}}Result.from_aggregate(saved_{{name_lower}})

        raise NotImplementedError("Please implement business logic")


# ============================================================================
# 使用说明
# ============================================================================
#
# 这个服务使用了 Bento Framework 的 ApplicationService 模式：
#
# ✅ 优势:
# - 只需实现 handle() 方法，专注业务逻辑
# - 框架自动处理事务管理（UoW）
# - 框架自动处理错误包装
# - 框架自动发布领域事件
# - 统一的 ApplicationServiceResult 返回格式
#
# 📝 使用方式:
# service = {{Action}}{{Name}}UseCase(uow)
# result = await service.execute(command)
#
# if result.is_success:
#     data = result.data  # {{Name}}Result
# else:
#     error = result.error  # 错误信息
#
