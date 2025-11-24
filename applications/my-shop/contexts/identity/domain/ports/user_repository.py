"""User repository port (interface).

Defines the contract for User repository implementations.
Domain layer defines the interface; infrastructure layer implements it.

Following Hexagonal Architecture and Domain-Driven Design principles:
- This interface is defined in the domain layer (port)
- Infrastructure layer provides the concrete implementation (adapter)
- Application layer depends on this interface, not implementation
"""

from __future__ import annotations

from typing import Protocol

from bento.core.ids import ID
from bento.domain.ports.repository import Repository

from contexts.identity.domain.models.user import User


class IUserRepository(Repository[User, ID], Protocol):
    """User repository interface (Secondary Port).

    继承 Bento 的 Repository[User, ID] 协议自动获得标准方法：
    - async def get(id: ID) -> User | None
    - async def save(entity: User) -> User
    - async def delete(entity: User) -> None
    - async def find_all() -> list[User]
    - async def exists(id: ID) -> bool
    - async def count() -> int

    Domain-specific query methods:
    """

    async def find_by_email(self, email: str) -> User | None:
        """Find user by email address.

        Args:
            email: User email address

        Returns:
            User if found, None otherwise
        """
        ...

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists.

        Args:
            email: Email to check

        Returns:
            True if email exists, False otherwise
        """
        ...


# ============================================================================
# 实现示例（需手动创建，放在 infrastructure/repositories/user_repository_impl.py）
# ============================================================================
#
# from bento.infrastructure.repository import RepositoryAdapter
# from bento.persistence.repository import BaseRepository
# from bento.persistence.interceptor import create_default_chain
# from contexts.identity.domain.user import User
# from contexts.identity.infrastructure.models.user_po import UserPO
# from contexts.identity.infrastructure.mappers.user_mapper import UserMapper
#
# class UserRepository(RepositoryAdapter[User, UserPO, str]):
#     """User 仓储实现
#
#     框架自动提供的功能：
#     - 领域对象 <-> 持久化对象映射
#     - 审计字段自动填充（created_at, updated_at, created_by, updated_by）
#     - 拦截器链（缓存、软删除、乐观锁等）
#     """
#
#     def __init__(self, session, actor: str = "system"):
#         mapper = UserMapper()
#         base_repo = BaseRepository(
#             session=session,
#             po_type=UserPO,
#             actor=actor,
#             interceptor_chain=create_default_chain(actor)
#         )
#         super().__init__(repository=base_repo, mapper=mapper)
#
