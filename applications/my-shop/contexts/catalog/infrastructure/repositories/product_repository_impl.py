"""Product Repository Implementation using Bento's RepositoryAdapter"""

from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.domain.product import Product
from contexts.catalog.infrastructure.mappers.product_mapper import ProductMapper
from contexts.catalog.infrastructure.models.product_po import ProductPO


class ProductRepository(RepositoryAdapter[Product, ProductPO, str]):
    """
    Product Repository using Bento's RepositoryAdapter.

    Provides:
    - Automatic CRUD operations via RepositoryAdapter
    - AR <-> PO mapping via ProductMapper
    - Audit, soft delete, optimistic locking via interceptor chain
    - Additional custom queries (pagination, filtering, etc.)

    Framework Features:
    - Automatic audit fields (created_at, updated_at, created_by, updated_by)
    - Optimistic locking with version field
    - Soft deletion support
    - UnitOfWork integration for event collection
    """

    def __init__(self, session: AsyncSession, actor: str = "system"):
        """
        Initialize Product Repository.

        Args:
            session: SQLAlchemy async session
            actor: Current user/system identifier for audit
        """
        # Create mapper
        mapper = ProductMapper()

        # Create base repository with interceptor chain
        base_repo = BaseRepository(
            session=session,
            po_type=ProductPO,
            actor=actor,
            interceptor_chain=create_default_chain(actor),
        )

        # Initialize adapter
        super().__init__(repository=base_repo, mapper=mapper)

        # Get current UoW from ContextVar for automatic tracking
        from bento.persistence.uow import _current_uow

        self._uow = _current_uow.get()

    # ==================== Bento Framework Methods ====================
    # The following methods are inherited from RepositoryAdapter:
    # - async def get(self, id: str) -> Product | None
    async def save(self, product: Product) -> None:
        """Save product to database and track for event collection.

        Args:
            product: Product aggregate to save
        """
        product_po = ProductPO.from_domain(product)
        self._session.add(product_po)

        # Automatically track aggregate for event collection
        if self._uow:
            self._uow.track(product)

    # - async def list(self, specification=None) -> list[Product]
    # - async def exists(self, id: str) -> bool
    # - async def delete(self, id: str) -> None
    # - async def paginate(...) -> Page[Product]

    # ==================== Custom Query Methods ====================

    async def find_by_id(self, product_id: str) -> Product | None:
        """
        Find product by ID (convenience method).
        Delegates to framework's get() method.
        """
        return await self.get(product_id)

    async def list_products(
        self, limit: int = 100, offset: int = 0, category_id: str | None = None
    ) -> list[Product]:
        """
        List products with pagination.

        Args:
            limit: Maximum number of products to return
            offset: Number of products to skip
            category_id: Optional category filter

        Returns:
            List of Product domain objects
        """
        query = select(ProductPO)

        # Apply filters
        if category_id:
            query = query.where(ProductPO.category_id == category_id)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Order by name
        query = query.order_by(ProductPO.name)

        result = await self.repository.session.execute(query)
        pos = result.scalars().all()

        return [self.mapper.map_reverse(po) for po in pos]

    async def count(self, category_id: str | None = None) -> int:
        """
        Count total products.

        Args:
            category_id: Optional category filter

        Returns:
            Total count of products
        """
        query = select(func.count()).select_from(ProductPO)

        if category_id:
            query = query.where(ProductPO.category_id == category_id)

        result = await self.repository.session.execute(query)
        return result.scalar_one()
