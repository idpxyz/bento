"""Order Read Model - P3 高级特性：CQRS 读模型"""

from datetime import datetime

from bento.persistence import Base
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column


class OrderReadModel(Base):
    """Order 读模型 - 优化查询性能

    P3 高级特性：CQRS 读模型

    优势：
    - total_amount 存储在数据库 → 可以 WHERE/ORDER BY
    - 无需 JOIN items 表 → 查询更快
    - 专门的索引 → 优化常见查询

    数据同步：
    - 通过事件投影器同步（OrderProjection）
    - 最终一致性（事件驱动）
    """

    __tablename__ = "order_read_models"

    # 主键
    id: Mapped[str] = mapped_column(primary_key=True)

    # 基本信息
    customer_id: Mapped[str]
    status: Mapped[str]  # OrderStatus enum value

    # ⭐ 预计算字段 - 关键优势
    total_amount: Mapped[float]  # 从 items 计算，存储以便数据库过滤
    items_count: Mapped[int]  # 订单商品数量

    # 时间戳
    created_at: Mapped[datetime]
    paid_at: Mapped[datetime | None] = mapped_column(default=None)
    shipped_at: Mapped[datetime | None] = mapped_column(default=None)

    # 索引优化
    __table_args__ = (
        Index("idx_order_read_customer", "customer_id"),
        Index("idx_order_read_status", "status"),
        Index("idx_order_read_total", "total_amount"),
        Index("idx_order_read_created", "created_at"),
    )
