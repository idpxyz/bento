"""Category Repository Implementation using Bento's RepositoryAdapter"""

from bento.core.ids import ID
from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.domain.category import Category
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

    # ==================== Inherited from RepositoryAdapter ====================
    # The following methods are inherited from RepositoryAdapter and match ICategoryRepository Protocol:
    # - async def get(self, id: ID) -> Category | None
    # - async def save(self, aggregate: Category) -> None
    # - async def delete(self, aggregate: Category) -> None
    # - async def list(specification: CompositeSpecification[Category] | None = None) -> list[Category]
    # - async def paginate(...) -> Page[Category]
    # - async def count(specification) -> int
    # ... and many more from Mixins

    # Additional custom query methods can be added here
    # For example:
    # async def find_by_parent_id(self, parent_id: str | None) -> list[Category]:
    #     """Find categories by parent ID."""
