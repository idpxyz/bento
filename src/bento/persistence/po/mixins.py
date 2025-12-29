"""SQLAlchemy persistence object field mixins.

这些 Mixin 提供标准的审计、软删除和乐观锁字段定义。
它们只定义字段结构，不包含任何业务逻辑。

实际的字段值填充由 Interceptor 系统自动处理。

重要提示:
    - 这些 Mixin 只用于 Persistence Object (PO)，不应该用于 Domain Entity
    - Domain Entity 应该保持纯净，不包含这些技术字段
    - Mapper 负责在 Domain Entity 和 PO 之间转换时过滤这些字段

Example:
    ```python
    from sqlalchemy.orm import Mapped, mapped_column
    from bento.persistence.mixins import FullAuditMixin
    from bento.persistence.interceptor import create_default_chain
    from bento.persistence.repository import BaseRepository

    # 1. 定义 PO（使用 Mixin）
    class OrderPO(Base, FullAuditMixin):
        __tablename__ = "orders"
        id: Mapped[str] = mapped_column(String(50), primary_key=True)
        customer_id: Mapped[str] = mapped_column(String(50))
        status: Mapped[str] = mapped_column(String(20))
        # ✅ 审计字段已通过 FullAuditMixin 继承

    # 2. 使用 Repository + Interceptor（自动填充字段值）
    repo = BaseRepository(
        session=session,
        po_type=OrderPO,
        interceptor_chain=create_default_chain(actor="user-123")
    )

    # 3. CRUD 操作（Interceptor 自动处理）
    order = OrderPO(id="order-1", customer_id="cust-1", status="pending")
    await repo.create_po(order)
    # ✅ Interceptor 自动设置：
    #    order.created_at = now()
    #    order.created_by = "user-123"
    #    order.updated_at = now()
    #    order.updated_by = "user-123"
    #    order.version = 1

    await repo.update_po(order)
    # ✅ Interceptor 自动更新：
    #    order.updated_at = now()
    #    order.updated_by = "user-123"
    #    order.version = 2

    await repo.delete_po(order)
    # ✅ Interceptor 自动软删除：
    #    order.deleted_at = now()
    #    order.deleted_by = "user-123"
    ```

架构说明:
    ```
    Domain Layer (领域层)
    ┌─────────────────────────────┐
    │  Order (AggregateRoot)      │ ← 纯业务字段
    │  - id: ID                   │
    │  - customer_id: ID          │
    │  - status: OrderStatus      │
    │  - place_order()            │
    └──────────┬──────────────────┘
               │ Mapper (过滤技术字段)
               ▼
    Persistence Layer (持久化层)
    ┌─────────────────────────────┐
    │  OrderPO (SQLAlchemy Model) │
    │  - id: str                  │
    │  - customer_id: str         │
    │  - status: str              │
    │  + created_at               │ ← 技术字段（Mixin）
    │  + updated_at               │
    │  + created_by               │
    │  + updated_by               │
    │  + deleted_at               │
    │  + version                  │
    └─────────────────────────────┘
                   ▲
                   │ Interceptor (自动填充值)
    ```
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, Integer, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

if TYPE_CHECKING:
    pass  # 预留用于类型检查的导入


class AuditFieldsMixin:
    """审计字段 Mixin（创建和更新时间/操作人）.

    提供标准的审计跟踪字段：
    - created_at: 创建时间
    - updated_at: 最后更新时间
    - created_by: 创建者标识（用户ID/系统标识）
    - updated_by: 最后更新者标识

    这些字段的值由 AuditInterceptor 自动填充，无需手动设置。

    Example:
        ```python
        class UserPO(Base, AuditFieldsMixin):
            __tablename__ = "users"
            id: Mapped[str] = mapped_column(String(50), primary_key=True)
            username: Mapped[str] = mapped_column(String(100))
            # ✅ created_at, updated_at, created_by, updated_by 已继承

        # 使用
        repo = BaseRepository(
            session=session,
            po_type=UserPO,
            interceptor_chain=create_default_chain(actor="admin")
        )
        user = UserPO(id="user-1", username="john")
        await repo.create_po(user)
        # ✅ user.created_at = 2024-01-01 10:00:00
        # ✅ user.created_by = "admin"
        ```

    Notes:
        - created_at/updated_at: 使用数据库时间戳类型（带时区）
        - created_by/updated_by: 可空字符串，默认为 "system"
        - 字段值由 AuditInterceptor 管理，不要手动设置
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        doc="创建时间（由 AuditInterceptor 自动设置）",
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        doc="最后更新时间（由 AuditInterceptor 自动设置）",
    )

    created_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="创建者标识（由 AuditInterceptor 自动设置，默认 'system'）",
    )

    updated_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="最后更新者标识（由 AuditInterceptor 自动设置，默认 'system'）",
    )


class SoftDeleteFieldsMixin:
    """软删除字段 Mixin（逻辑删除标记）.

    提供软删除功能所需的字段：
    - deleted_at: 删除时间（NULL 表示未删除）
    - deleted_by: 删除者标识

    这些字段的值由 SoftDeleteInterceptor 自动填充。
    当调用 repository.delete_po(entity) 时，不会真正删除记录，
    而是设置 deleted_at 和 deleted_by。

    Example:
        ```python
        class ProductPO(Base, SoftDeleteFieldsMixin):
            __tablename__ = "products"
            id: Mapped[str] = mapped_column(String(50), primary_key=True)
            name: Mapped[str] = mapped_column(String(200))
            # ✅ deleted_at, deleted_by 已继承

        # 使用
        repo = BaseRepository(
            session=session,
            po_type=ProductPO,
            interceptor_chain=create_default_chain(actor="admin")
        )
        product = ProductPO(id="prod-1", name="Laptop")
        await repo.create_po(product)
        await repo.delete_po(product)
        # ✅ product.deleted_at = 2024-01-01 10:00:00
        # ✅ product.deleted_by = "admin"
        # ❌ 数据库记录仍然存在（逻辑删除）
        ```

    Notes:
        - deleted_at 为 NULL 表示记录未被删除
        - deleted_at 有值表示记录已被软删除
        - 查询时需要添加 WHERE deleted_at IS NULL 过滤软删除的记录
        - SoftDeleteInterceptor 会自动处理 DELETE 操作
    """

    __abstract__ = True

    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=None,
        doc="删除时间（NULL=未删除，由 SoftDeleteInterceptor 自动设置）",
    )

    deleted_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        doc="删除者标识（由 SoftDeleteInterceptor 自动设置）",
    )

    @property
    def is_deleted(self) -> bool:
        """检查记录是否已被软删除.

        Returns:
            True 如果记录已被软删除（deleted_at 不为 NULL）

        Example:
            ```python
            product = await repo.get_po_by_id("prod-1")
            if product.is_deleted:
                print("This product has been deleted")
            ```
        """
        return self.deleted_at is not None


class OptimisticLockFieldMixin:
    """乐观锁字段 Mixin（版本号并发控制）.

    提供乐观锁功能所需的版本号字段：
    - version: 版本号（每次更新时递增）

    这个字段由 OptimisticLockInterceptor 自动管理。
    用于防止并发更新冲突（Lost Update Problem）。

    工作原理:
        1. 读取记录时获取当前版本号（version=1）
        2. 更新时检查版本号是否匹配
        3. 如果匹配，更新记录并递增版本号（version=2）
        4. 如果不匹配，抛出 OptimisticLockException

    Example:
        ```python
        class AccountPO(Base, OptimisticLockFieldMixin):
            __tablename__ = "accounts"
            id: Mapped[str] = mapped_column(String(50), primary_key=True)
            balance: Mapped[int] = mapped_column(Integer)
            # ✅ version 已继承

        # 使用
        repo = BaseRepository(
            session=session,
            po_type=AccountPO,
            interceptor_chain=create_default_chain(actor="system")
        )

        # 并发场景
        # 线程 A 读取
        account_a = await repo.get_po_by_id("acc-1")  # version=1, balance=100

        # 线程 B 读取
        account_b = await repo.get_po_by_id("acc-1")  # version=1, balance=100

        # 线程 A 更新成功
        account_a.balance = 150
        await repo.update_po(account_a)  # ✅ version 更新为 2

        # 线程 B 更新失败（版本号已变）
        account_b.balance = 120
        await repo.update_po(account_b)  # ❌ 抛出 OptimisticLockException
        ```

    Notes:
        - 初始版本号为 1（由 OptimisticLockInterceptor 设置）
        - 每次 UPDATE 操作版本号自动递增
        - 版本号不匹配时会抛出 OptimisticLockException
        - 适用于高并发更新场景
    """

    __abstract__ = True

    # Enable SQLAlchemy native optimistic locking
    # This generates: UPDATE ... WHERE id = ? AND version = ?
    # If no rows affected, raises StaleDataError
    @declared_attr.directive
    def __mapper_args__(cls) -> dict:  # type: ignore[misc]
        return {"version_id_col": cls.__table__.c.version}  # type: ignore[attr-defined]

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="版本号（由 SQLAlchemy version_id_col 自动管理）",
    )


class FullAuditMixin(AuditFieldsMixin, SoftDeleteFieldsMixin, OptimisticLockFieldMixin):
    """完整审计功能 Mixin（组合所有审计字段）.

    这是最常用的 Mixin，提供完整的审计、软删除和乐观锁功能。
    包含以下所有字段：
    - created_at, updated_at, created_by, updated_by（审计）
    - deleted_at, deleted_by（软删除）
    - version（乐观锁）

    Example:
        ```python
        # 最简单的用法：一次性获得所有功能
        class OrderPO(Base, FullAuditMixin):
            __tablename__ = "orders"
            id: Mapped[str] = mapped_column(String(50), primary_key=True)
            customer_id: Mapped[str] = mapped_column(String(50))
            total_amount: Mapped[int] = mapped_column(Integer)

        # 使用标准 Repository + Interceptor
        repo = BaseRepository(
            session=session,
            po_type=OrderPO,
            interceptor_chain=create_default_chain(actor="user-123")
        )

        # 所有功能自动可用
        order = OrderPO(id="order-1", customer_id="cust-1", total_amount=1000)

        await repo.create_po(order)
        # ✅ created_at, created_by, updated_at, updated_by, version=1

        await repo.update_po(order)
        # ✅ updated_at, updated_by, version=2

        await repo.delete_po(order)
        # ✅ deleted_at, deleted_by（软删除）

        # 检查状态
        if order.is_deleted:
            print(f"Order deleted by {order.deleted_by}")
        ```

    Notes:
        - 这是推荐的默认选择，除非有特殊需求
        - 所有字段都由对应的 Interceptor 自动管理
        - 适用于大多数需要完整审计追踪的业务表
    """

    __abstract__ = True


# 导出所有 Mixin
__all__ = [
    "AuditFieldsMixin",
    "SoftDeleteFieldsMixin",
    "OptimisticLockFieldMixin",
    "FullAuditMixin",
]
