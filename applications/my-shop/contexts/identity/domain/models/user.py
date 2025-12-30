"""User 聚合根 - 完全符合 Bento Framework"""

from dataclasses import dataclass

from bento.domain.aggregate import AggregateRoot


@dataclass
class User(AggregateRoot):
    """User 聚合根

    使用 Bento Framework 的 AggregateRoot：
    - 自动事件收集
    - 自动 ID 管理
    - 自动与 UnitOfWork 集成

    领域模型只关注业务逻辑，不关心持久化细节。
    """

    id: str
    name: str
    email: str

    def __post_init__(self):
        """初始化聚合根"""
        super().__init__(id=self.id)

    # ==================== 业务方法 ====================

    def change_name(self, new_name: str) -> None:
        """
        更改用户名称

        这是一个业务方法示例，展示如何在领域模型中实现业务逻辑。

        发布 UserUpdated 事件以通知系统其他部分。
        """
        if not new_name or len(new_name.strip()) == 0:
            raise ValueError("Name cannot be empty")

        self.name = new_name.strip()

        # 发布领域事件
        from contexts.identity.domain.events import UserUpdated

        self.add_event(
            UserUpdated(
                user_id=self.id,
                updated_fields={"name": self.name},
            )
        )

    def change_email(self, new_email: str) -> None:
        """
        更改邮箱地址

        发布 UserEmailChanged 事件，因为邮箱变更通常需要特殊处理。
        """
        if not new_email or "@" not in new_email:
            raise ValueError("Invalid email address")

        old_email = self.email
        self.email = new_email.lower().strip()

        # 发布邮箱变更事件（独立事件）
        from contexts.identity.domain.events import UserEmailChanged

        self.add_event(
            UserEmailChanged(
                user_id=self.id,
                old_email=old_email,
                new_email=self.email,
            )
        )
