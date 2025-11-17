"""User Repository Implementation"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.identity.domain.user import User
from contexts.identity.infrastructure.mappers.user_mapper import UserMapper
from contexts.identity.infrastructure.models.user_po import UserPO


class UserRepository:
    """
    User Repository Implementation.

    Provides database operations for User aggregate with:
    - CRUD operations
    - Pagination support
    - Email lookup
    - Async SQLAlchemy integration
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = UserMapper()

    async def find_by_id(self, user_id: str) -> User | None:
        """Find user by ID"""
        result = await self.session.execute(select(UserPO).where(UserPO.id == user_id))
        po = result.scalar_one_or_none()

        if not po:
            return None

        return self.mapper.to_domain(po)

    async def find_by_email(self, email: str) -> User | None:
        """Find user by email"""
        result = await self.session.execute(select(UserPO).where(UserPO.email == email))
        po = result.scalar_one_or_none()

        if not po:
            return None

        return self.mapper.to_domain(po)

    async def save(self, user: User) -> None:
        """Save or update user"""
        # Check if exists
        existing = await self.session.execute(select(UserPO).where(UserPO.id == user.id))
        existing_po = existing.scalar_one_or_none()

        if existing_po:
            # Update
            existing_po.name = user.name
            existing_po.email = user.email
        else:
            # Insert
            po = self.mapper.to_po(user)
            self.session.add(po)

    async def delete(self, user: User) -> None:
        """Delete user"""
        po = await self.session.execute(select(UserPO).where(UserPO.id == user.id))
        po_obj = po.scalar_one_or_none()

        if po_obj:
            await self.session.delete(po_obj)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """
        List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of User domain objects
        """
        query = select(UserPO)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Order by name
        query = query.order_by(UserPO.name)

        result = await self.session.execute(query)
        pos = result.scalars().all()

        return [self.mapper.to_domain(po) for po in pos]

    async def count(self) -> int:
        """
        Count total users.

        Returns:
            Total count of users
        """
        result = await self.session.execute(select(func.count()).select_from(UserPO))
        return result.scalar_one()

    async def exists(self, user_id: str) -> bool:
        """Check if user exists"""
        result = await self.session.execute(
            select(func.count()).select_from(UserPO).where(UserPO.id == user_id)
        )
        count = result.scalar_one()
        return count > 0

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        result = await self.session.execute(
            select(func.count()).select_from(UserPO).where(UserPO.email == email)
        )
        count = result.scalar_one()
        return count > 0
