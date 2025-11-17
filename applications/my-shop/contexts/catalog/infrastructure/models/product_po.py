"""Product 持久化对象（数据库模型）"""
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    """临时 Base 类 - 实际项目应从框架统一的 Base 继承"""
    pass


class ProductPO(Base):
    """Product 数据库表

    持久化对象（PO）仅包含数据结构，不包含业务逻辑。
    与领域模型分离，通过 Mapper 进行转换。
    """
    __tablename__: str = "products"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    price: Mapped[float]

    # 审计字段（拦截器自动填充）
    created_at: Mapped[datetime | None]
    created_by: Mapped[str | None]
    updated_at: Mapped[datetime | None]
    updated_by: Mapped[str | None]


# ============================================================================
# 实际项目中的实现示例
# ============================================================================
#
# 从框架统一的 Base 继承：
# from bento.persistence.sqlalchemy.base import Base
#
# class ProductPO(Base):
#     __tablename__: str = "products"
#     # ... 字段定义
#