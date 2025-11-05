"""用户领域实体

定义用户领域实体及其行为。
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from idp.framework.shared.utils.date_time import utc_now

from .user_id import UserId


@dataclass
class User:
    """用户实体

    领域模型中的用户实体，包含用户的核心属性和行为。

    Attributes:
        id: 用户ID
        username: 用户名
        email: 电子邮箱
        full_name: 全名
        is_active: 是否激活
        is_admin: 是否管理员
    """

    id: Optional[UserId]
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False

    def activate(self) -> None:
        """激活用户"""
        self.is_active = True
        self.updated_at = utc_now()

    def deactivate(self) -> None:
        """停用用户"""
        self.is_active = False
        self.updated_at = utc_now()

    def promote_to_admin(self) -> None:
        """提升为管理员"""
        self.is_admin = True
        self.updated_at = utc_now()

    def demote_from_admin(self) -> None:
        """取消管理员权限"""
        self.is_admin = False
        self.updated_at = utc_now()

    def update_profile(self, full_name: Optional[str] = None, email: Optional[str] = None) -> None:
        """更新用户资料

        Args:
            full_name: 新的全名，如果为None则保持不变
            email: 新的电子邮箱，如果为None则保持不变
        """
        if full_name is not None:
            self.full_name = full_name

        if email is not None:
            self.email = email

        self.updated_at = utc_now()

    def __str__(self) -> str:
        """字符串表示"""
        return f"User(id={self.id}, username={self.username}, email={self.email})"
