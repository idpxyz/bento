"""OrderItem 持久化对象 - 符合 Bento Framework 标准"""

from bento.persistence import (
    AuditFieldsMixin,
    Base,
    OptimisticLockFieldMixin,
)
from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column


class OrderItemPO(Base, AuditFieldsMixin, OptimisticLockFieldMixin):
    """OrderItem 持久化对象

    订单项作为 Order 聚合的一部分，不需要软删除。
    """

    __tablename__ = "order_items"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 外键：关联到 Order
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )

    # 产品关联（通过 ID 引用，不是直接外键）
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # 业务字段
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


# ============================================================================
# 实际项目中的实现示例
# ============================================================================
#
# 从框架统一的 Base 继承：
# from bento.persistence.sqlalchemy.base import Base
#
# class OrderItemPO(Base):
#     __tablename__: str = "orderitems"
#     # ... 字段定义
#
