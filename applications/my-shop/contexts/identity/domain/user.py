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
        """
        if not new_name or len(new_name.strip()) == 0:
            raise ValueError("Name cannot be empty")

        old_name = self.name
        self.name = new_name.strip()

        # 可以发布领域事件
        # from contexts.identity.domain.events import UserNameChangedEvent
        # self.add_event(UserNameChangedEvent(
        #     user_id=self.id,
        #     old_name=old_name,
        #     new_name=self.name
        # ))

    def change_email(self, new_email: str) -> None:
        """更改邮箱地址"""
        if not new_email or "@" not in new_email:
            raise ValueError("Invalid email address")

        self.email = new_email.lower().strip()
