"""Product 持久化对象 - 完全符合 Bento Framework 标准"""

from bento.persistence import (
    AuditFieldsMixin,
    Base,
    OptimisticLockFieldMixin,
    SoftDeleteFieldsMixin,
)
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column


class ProductPO(Base, AuditFieldsMixin, SoftDeleteFieldsMixin, OptimisticLockFieldMixin):
    """
    Product 持久化对象（Persistence Object）

    继承 Bento Framework 的 Mixins：
    - AuditFieldsMixin: created_at, updated_at, created_by, updated_by
    - SoftDeleteFieldsMixin: deleted_at, deleted_by, is_deleted property
    - OptimisticLockFieldMixin: version

    注意：
    - 所有 Mixin 字段由 Interceptor 在 repository 层自动填充
    - 不需要手动定义这些字段
    - 业务代码只需关注业务字段
    """

    __tablename__ = "products"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 业务字段
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    stock: Mapped[int | None] = mapped_column(nullable=True, default=0)
    category_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
