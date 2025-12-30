"""{{Name}} 持久化对象（数据库模型）"""
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from bento.persistence.po.base import Base


class {{Name}}PO(Base):
    """{{Name}} 数据库表

    持久化对象（PO）仅包含数据结构，不包含业务逻辑。
    与领域模型分离，通过 Mapper 进行转换。
    """
    __tablename__: str = "{{table_name}}"

{{fields}}

    # 审计字段（拦截器自动填充）
    created_at: Mapped[datetime | None]
    created_by: Mapped[str | None]
    updated_at: Mapped[datetime | None]
    updated_by: Mapped[str | None]


# ============================================================================
# 使用 Bento Framework Mixins 增强功能
# ============================================================================
#
# 从框架提供的 Mixins 继承更多功能：
#
# from bento.persistence.po.base import Base
# from bento.persistence.po.mixins import (
#     AuditFieldsMixin,          # 审计字段（created_at, updated_at, created_by, updated_by）
#     SoftDeleteFieldsMixin,     # 软删除（deleted_at, is_deleted）
#     OptimisticLockFieldMixin,  # 乐观锁（version）
# )
#
# class {{Name}}PO(Base, AuditFieldsMixin, SoftDeleteFieldsMixin, OptimisticLockFieldMixin):
#     """{{Name}} 数据库表（带完整功能）
#     
#     自动继承的字段：
#     - created_at, updated_at, created_by, updated_by (审计)
#     - deleted_at, is_deleted (软删除)
#     - version (乐观锁)
#     
#     这些字段由 Bento Framework 的拦截器自动管理，无需手动处理。
#     """
#     __tablename__: str = "{{table_name}}"
#     
#     # 业务字段
#     # id: Mapped[str] = mapped_column(primary_key=True)
#     # name: Mapped[str]
#     # price: Mapped[float]
#
