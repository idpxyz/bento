"""Product Repository Implementation using Bento's RepositoryAdapter"""

from bento.core.ids import ID
from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.domain.product import Product
from contexts.catalog.infrastructure.mappers.product_mapper import ProductMapper
from contexts.catalog.infrastructure.models.product_po import ProductPO


class ProductRepository(RepositoryAdapter[Product, ProductPO, ID]):
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

        # ✅ 框架自动处理：
        # - UoW 追踪：RepositoryAdapter.save() 自动调用 uow.track()
        # - 事件收集：框架自动从聚合根收集领域事件
        # - 审计字段：拦截器链自动填充 created_at, updated_at 等

        # ❌ 不需要手动获取 UoW
        # ❌ 不需要重写 save() 方法
        # ❌ 不需要手动追踪实体

    # ==================== Inherited from RepositoryAdapter ====================
    # The following methods are inherited from RepositoryAdapter
    # and match IProductRepository Protocol:
    # - async def get(self, id: ID) -> Product | None
    # - async def save(self, aggregate: Product) -> None
    # - async def delete(self, aggregate: Product) -> None
    # - async def list(self, specification: CompositeSpecification[Product] | None = None)
    # -> list[Product]
    # - async def paginate(...) -> Page[Product]
    # - async def count(specification) -> int
    # ... and many more from Mixins

    # ==================== Domain-Specific Query Methods (from IProductRepository Protocol) ====================

    async def find_by_category(self, category_id: ID) -> list[Product]:
        """Find products by category ID."""
        return await self.list_products(category_id=str(category_id))

    async def find_by_name(self, name: str) -> list[Product]:
        """Find products by name (fuzzy search)."""
        query = select(ProductPO).where(ProductPO.name.contains(name))
        result = await self.repository.session.execute(query)
        pos = result.scalars().all()
        return [self.mapper.map_reverse(po) for po in pos]

    async def find_in_stock(self) -> list[Product]:
        """Find products that are in stock."""
        query = select(ProductPO).where(ProductPO.stock > 0)
        result = await self.repository.session.execute(query)
        pos = result.scalars().all()
        return [self.mapper.map_reverse(po) for po in pos]

    async def find_by_price_range(self, min_price: float, max_price: float) -> list[Product]:
        """Find products within price range."""
        query = select(ProductPO).where(ProductPO.price >= min_price, ProductPO.price <= max_price)
        result = await self.repository.session.execute(query)
        pos = result.scalars().all()
        return [self.mapper.map_reverse(po) for po in pos]

    # ==================== Custom Query Methods ====================

    async def find_by_id(self, product_id: ID) -> Product | None:
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
