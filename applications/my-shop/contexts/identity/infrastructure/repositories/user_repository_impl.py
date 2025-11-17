"""User Repository Implementation using Bento's RepositoryAdapter"""

from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.identity.domain.user import User
from contexts.identity.infrastructure.mappers.user_mapper import UserMapper
from contexts.identity.infrastructure.models.user_po import UserPO


class UserRepository(RepositoryAdapter[User, UserPO, str]):
    """
    User Repository using Bento's RepositoryAdapter.

    Provides:
    - Automatic CRUD operations via RepositoryAdapter
    - AR <-> PO mapping via UserMapper
    - Audit, soft delete, optimistic locking via interceptor chain
    - Additional custom queries (find_by_email, count, etc.)

    Framework Features:
    - Automatic audit fields (created_at, updated_at, created_by, updated_by)
    - Optimistic locking with version field
    - Soft deletion support
    - UnitOfWork integration for event collection
    """

    def __init__(self, session: AsyncSession, actor: str = "system"):
        """
        Initialize User Repository.

        Args:
            session: SQLAlchemy async session
            actor: Current user/system identifier for audit
        """
        # Create mapper
        mapper = UserMapper()

        # Create base repository with interceptor chain
        base_repo = BaseRepository(
            session=session,
            po_type=UserPO,
            actor=actor,
            interceptor_chain=create_default_chain(actor),
        )

        # Initialize adapter
        super().__init__(repository=base_repo, mapper=mapper)

    # ==================== Bento Framework Methods ====================
    # The following methods are inherited from RepositoryAdapter:
    # - async def get(self, id: str) -> User | None
    # - async def save(self, user: User) -> None
    # - async def list(self, specification=None) -> list[User]
    # - async def exists(self, id: str) -> bool
    # - async def delete(self, id: str) -> None
    # - async def paginate(...) -> Page[User]

    # ==================== Custom Query Methods ====================

    async def find_by_id(self, user_id: str) -> User | None:
        """
        Find user by ID (convenience method).
        Delegates to framework's get() method.
        """
        return await self.get(user_id)

    async def find_by_email(self, email: str) -> User | None:
        """
        Find user by email (custom query).

        Args:
            email: User email address

        Returns:
            User if found, None otherwise
        """
        result = await self.repository.session.execute(select(UserPO).where(UserPO.email == email))
        po = result.scalar_one_or_none()

        if not po:
            return None

        return self.mapper.map_reverse(po)  # PO -> AR

    async def count(self) -> int:
        """
        Count total users.

        Returns:
            Total count of users
        """
        result = await self.repository.session.execute(select(func.count()).select_from(UserPO))
        return result.scalar_one()

    async def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email to check

        Returns:
            True if email exists, False otherwise
        """
        result = await self.repository.session.execute(
            select(func.count()).select_from(UserPO).where(UserPO.email == email)
        )
        count = result.scalar_one()
        return count > 0

    async def list_paginated(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """
        List users with pagination (custom query).

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of User domain objects
        """
        query = select(UserPO).limit(limit).offset(offset).order_by(UserPO.name)

        result = await self.repository.session.execute(query)
        pos = result.scalars().all()

        return [self.mapper.map_reverse(po) for po in pos]  # PO -> AR (batch)
