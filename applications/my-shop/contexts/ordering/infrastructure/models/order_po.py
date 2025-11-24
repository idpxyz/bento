"""Order 持久化对象 - 符合 Bento Framework 标准"""

from datetime import datetime

from bento.persistence import (
    AuditFieldsMixin,
    Base,
    OptimisticLockFieldMixin,
    SoftDeleteFieldsMixin,
)
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column


class OrderPO(Base, AuditFieldsMixin, SoftDeleteFieldsMixin, OptimisticLockFieldMixin):
    """Order 持久化对象

    继承 Bento Framework 的 Mixins：
    - AuditFieldsMixin: created_at, updated_at, created_by, updated_by
    - SoftDeleteFieldsMixin: deleted_at, deleted_by
    - OptimisticLockFieldMixin: version
    """

    __tablename__ = "orders"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 业务字段
    customer_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    # 时间字段
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # 关系：一个订单包含多个订单项
    # items: Mapped[list["OrderItemPO"]] = relationship(
    #     "OrderItemPO", back_populates="order", cascade="all, delete-orphan"
    # )


# ============================================================================
# 实际项目中的实现示例
# ============================================================================
#
# 从框架统一的 Base 继承：
# from bento.persistence.sqlalchemy.base import Base
#
# class OrderPO(Base):
#     __tablename__: str = "orders"
#     # ... 字段定义
#
