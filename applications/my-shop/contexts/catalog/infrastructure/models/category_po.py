"""Category 持久化对象 - 完全符合 Bento Framework 标准"""

from bento.persistence import (
    AuditFieldsMixin,
    Base,
    OptimisticLockFieldMixin,
    SoftDeleteFieldsMixin,
)
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class CategoryPO(Base, AuditFieldsMixin, SoftDeleteFieldsMixin, OptimisticLockFieldMixin):
    """
    Category 持久化对象（Persistence Object）

    继承 Bento Framework 的 Mixins：
    - AuditFieldsMixin: created_at, updated_at, created_by, updated_by
    - SoftDeleteFieldsMixin: deleted_at, deleted_by, is_deleted property
    - OptimisticLockFieldMixin: version

    注意：
    - 所有 Mixin 字段由 Interceptor 在 repository 层自动填充
    - 不需要手动定义这些字段
    - 业务代码只需关注业务字段
    """

    __tablename__ = "categories"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 业务字段
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ============================================================================
# 实际项目中的实现示例
# ============================================================================
#
# 从框架统一的 Base 继承：
# from bento.persistence.sqlalchemy.base import Base
#
# class CategoryPO(Base):
#     __tablename__: str = "categorys"
#     # ... 字段定义
#
