"""Category Repository Implementation using Bento's RepositoryAdapter"""

from bento.core.ids import ID
from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.domain.models.category import Category
from contexts.catalog.infrastructure.mappers.category_mapper import CategoryMapper
from contexts.catalog.infrastructure.models.category_po import CategoryPO


class CategoryRepository(RepositoryAdapter[Category, CategoryPO, ID]):
    """
    Category Repository using Bento's RepositoryAdapter.

    Provides:
    - Automatic CRUD operations via RepositoryAdapter
    - AR <-> PO mapping via CategoryMapper
    - Audit, soft delete, optimistic locking via interceptor chain
    - Support for hierarchical categories (parent_id)

    Framework Features:
    - Automatic audit fields (created_at, updated_at, created_by, updated_by)
    - Optimistic locking with version field
    - Soft deletion support
    - UnitOfWork integration for event collection
    """

    def __init__(self, session: AsyncSession, actor: str = "system"):
        """
        Initialize Category Repository.

        Args:
            session: SQLAlchemy async session
            actor: Current user/system identifier for audit
        """
        # Create mapper
        mapper = CategoryMapper()

        # Create base repository with interceptors
        base_repo = BaseRepository(
            session=session,
            po_type=CategoryPO,
            actor=actor,
            interceptor_chain=create_default_chain(actor),
        )

        # Initialize RepositoryAdapter
        super().__init__(repository=base_repo, mapper=mapper)

        # Get current UoW from ContextVar for automatic tracking
        from bento.persistence.uow import _current_uow

        self._uow = _current_uow.get()

    # ==========================================================================
    # Inherited from RepositoryAdapter
    # ==========================================================================
    # The following methods are inherited from RepositoryAdapter
    # and match ICategoryRepository Protocol:
    # - async def get(self, id: ID) -> Category | None
    # - async def save(self, entity: Category) -> Category
    # - async def delete(self, entity: Category) -> None
    # - async def find_all() -> list[Category]
    # - async def exists(id: ID) -> bool
    # - async def count() -> int

    # ==========================================================================
    # Domain-Specific Query Methods (from ICategoryRepository Protocol)
    # ==========================================================================

    async def find_by_name(self, name: str) -> Category | None:
        """Find category by exact name."""
        from sqlalchemy import select

        query = select(CategoryPO).where(CategoryPO.name == name)
        result = await self.repository.session.execute(query)
        po = result.scalars().first()

        return self.mapper.map_reverse(po) if po else None

    async def find_root_categories(self) -> list[Category]:
        """Find all root categories (categories without parent)."""
        from sqlalchemy import select

        query = select(CategoryPO).where(CategoryPO.parent_id.is_(None))
        result = await self.repository.session.execute(query)
        pos = result.scalars().all()

        return [self.mapper.map_reverse(po) for po in pos]

    async def find_subcategories(self, parent_id: ID) -> list[Category]:
        """Find subcategories of a parent category."""
        from sqlalchemy import select

        query = select(CategoryPO).where(CategoryPO.parent_id == str(parent_id))
        result = await self.repository.session.execute(query)
        pos = result.scalars().all()

        return [self.mapper.map_reverse(po) for po in pos]
