"""User repository port (interface).

Defines the contract for User repository implementations.
Domain layer defines the interface; infrastructure layer implements it.

Following Hexagonal Architecture:
- This interface is in domain/ports (Port)
- Implementation is in infrastructure/repositories (Adapter)
- Application layer depends on this interface, not implementation
"""

from typing import Protocol

from contexts.identity.domain.user import User


class IUserRepository(Protocol):
    """User repository interface (port).

    This is the contract that infrastructure adapters must implement.
    The domain layer depends on this interface, not the concrete implementation.

    Standard repository operations:
    - get(id) - Find aggregate by ID
    - save(aggregate) - Save aggregate (create or update)
    - delete(aggregate) - Delete aggregate (soft delete)
    - exists(id) - Check if aggregate exists
    - list(...) - Query list of aggregates

    Following Dependency Inversion Principle:
    - Domain layer defines the interface
    - Infrastructure layer implements it
    - Application layer depends on interface
    """

    async def get(self, id: str) -> User | None:
        """Get user by ID.

        Args:
            id: User identifier

        Returns:
            User if found, None otherwise
        """
        ...

    async def save(self, user: User) -> None:
        """Save user (create or update).

        Args:
            user: User aggregate to save
        """
        ...

    async def delete(self, user: User) -> None:
        """Delete user (soft delete).

        Args:
            user: User aggregate to delete
        """
        ...

    async def exists(self, id: str) -> bool:
        """Check if user exists.

        Args:
            id: User identifier

        Returns:
            True if user exists, False otherwise
        """
        ...

    async def list(self, limit: int = 100, offset: int = 0) -> list[User]:
        """List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of matching users
        """
        ...

    # Custom query methods specific to User domain
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
