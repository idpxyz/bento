"""用户持久化对象

定义用户的持久化对象，用于ORM映射。
"""

import uuid
from typing import Optional

from infrastructure.persistence.sqlalchemy.po.base import FullFeatureBasePO
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from idp.framework.infrastructure.persistence.sqlalchemy.po import BasePO
from idp.framework.shared.utils.date_time import utc_now


class UserPO(FullFeatureBasePO):
    """用户持久化对象

    用于SQLAlchemy ORM映射的用户表实体类。

    Attributes:
        id: 主键
        username: 用户名
        email: 电子邮箱
        full_name: 全名
        is_active: 是否激活
        is_admin: 是否管理员
    """

    # 表名需要与直接SQL创建的表名完全匹配
    __tablename__ = "users_repo"

    # 列定义需要与SQL创建语句匹配
    id: Mapped[str] = mapped_column(String(36), primary_key=True, nullable=False,
                                    default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)

    def __init__(self, **kwargs):
        """初始化持久化对象

        如果未提供ID，则自动生成UUID。
        """
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"UserPO(id={self.id}, username={self.username}, email={self.email}, full_name={self.full_name}, is_active={self.is_active}, is_admin={self.is_admin})"
