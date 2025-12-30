"""Product Repository Implementation using Bento's RepositoryAdapter"""

from bento.core.ids import ID
from bento.infrastructure.repository import RepositoryAdapter, repository_for
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.domain.models.product import Product
from contexts.catalog.infrastructure.mappers.product_mapper import ProductMapper
from contexts.catalog.infrastructure.models.product_po import ProductPO


@repository_for(Product)
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
    #   Returns: list[Product]
    # - async def paginate(...) -> Page[Product]
    # - async def count(specification) -> int
    # ... and many more from Mixins

    # Override exists to match IRepository interface
    async def exists(self, id: ID) -> bool:
        """Check if product exists by ID."""
        product = await self.get(id)
        return product is not None

    # ===== Domain-Specific Query Methods (from IProductRepository Protocol) ====

    async def find_by_category(self, category_id: ID) -> list[Product]:
        """Find products by category ID."""
        return await self.list_products(category_id=str(category_id))

    async def find_by_name(self, name: str) -> list[Product]:
        """Find products by name (fuzzy search)."""
        from bento.persistence.specification import EntitySpecificationBuilder

        # ✅ 使用 Specification 模式替代手动 SQL
        spec = EntitySpecificationBuilder().where("name", "like", f"%{name}%").build()
        return await self.find_all(spec)

    async def find_in_stock(self) -> list[Product]:
        """Find products that are in stock."""
        from bento.persistence.specification import EntitySpecificationBuilder

        # ✅ 使用 Specification 模式替代手动 SQL
        spec = EntitySpecificationBuilder().where("stock", ">", 0).build()
        return await self.find_all(spec)

    async def find_by_price_range(self, min_price: float, max_price: float) -> list[Product]:
        """Find products within price range."""
        from bento.persistence.specification import EntitySpecificationBuilder

        # ✅ 使用 Specification 模式替代手动 SQL
        spec = (
            EntitySpecificationBuilder()
            .where("price", ">=", min_price)
            .where("price", "<=", max_price)
            .build()
        )
        return await self.find_all(spec)

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
        # ✅ 使用 Framework 的 paginate() 便捷方法
        from bento.persistence.specification import EntitySpecificationBuilder

        spec = None
        if category_id:
            spec = (
                EntitySpecificationBuilder()
                .where("category_id", "=", category_id)
                .order_by("name")
                .build()
            )

        # Use Framework paginate() method instead of manual offset/limit
        page = (offset // limit) + 1
        page_result = await self.paginate(specification=spec, page=page, size=limit)

        return page_result.items

    # count() 方法已由 RepositoryAdapter 自动提供，无需重写
