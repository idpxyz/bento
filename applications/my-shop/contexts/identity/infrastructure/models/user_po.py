"""User 持久化对象 - 完全符合 Bento Framework 标准"""

from bento.persistence import (
    AuditFieldsMixin,
    Base,
    OptimisticLockFieldMixin,
    SoftDeleteFieldsMixin,
)
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class UserPO(Base, AuditFieldsMixin, SoftDeleteFieldsMixin, OptimisticLockFieldMixin):
    """
    User 持久化对象（Persistence Object）

    继承 Bento Framework 的 Mixins：
    - AuditFieldsMixin: created_at, updated_at, created_by, updated_by
    - SoftDeleteFieldsMixin: deleted_at, deleted_by, is_deleted property
    - OptimisticLockFieldMixin: version

    注意：
    - 所有 Mixin 字段由 Interceptor 在 repository 层自动填充
    - 不需要手动定义这些字段
    - 业务代码只需关注业务字段

    职责：
    - 定义数据库表结构
    - 映射到数据库列
    - 仅包含数据，不包含业务逻辑

    与领域模型分离：
    - UserPO: 数据库层，关注存储
    - User: 领域层，关注业务
    - UserMapper: 负责两者之间的转换（使用 AutoMapper）
    """

    __tablename__ = "users"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 业务字段
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # 不需要定义审计字段、版本字段、软删除字段！
    # 它们由 Mixins 提供：
    # - created_at, created_by, updated_at, updated_by (AuditFieldsMixin)
    # - deleted_at, deleted_by, is_deleted (SoftDeleteFieldsMixin)
    # - version (OptimisticLockFieldMixin)
