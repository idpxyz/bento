"""Product Repository Implementation with Pagination Support"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.domain.product import Product
from contexts.catalog.infrastructure.mappers.product_mapper import ProductMapper
from contexts.catalog.infrastructure.models.product_po import ProductPO


class ProductRepository:
    """
    Product Repository Implementation.

    Provides database operations for Product aggregate with:
    - CRUD operations
    - Pagination support
    - Async SQLAlchemy integration
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = ProductMapper()

    async def find_by_id(self, product_id: str) -> Product | None:
        """Find product by ID"""
        result = await self.session.execute(select(ProductPO).where(ProductPO.id == product_id))
        po = result.scalar_one_or_none()

        if not po:
            return None

        return self.mapper.to_domain(po)

    async def save(self, product: Product) -> None:
        """Save or update product"""
        # Check if exists
        existing = await self.session.execute(select(ProductPO).where(ProductPO.id == product.id))
        existing_po = existing.scalar_one_or_none()

        if existing_po:
            # Update
            existing_po.name = product.name
            existing_po.price = product.price
            existing_po.stock = product.stock
            existing_po.description = product.description
            existing_po.category_id = product.category_id
        else:
            # Insert
            po = self.mapper.to_po(product)
            self.session.add(po)

    async def delete(self, product: Product) -> None:
        """Delete product"""
        po = await self.session.execute(select(ProductPO).where(ProductPO.id == product.id))
        po_obj = po.scalar_one_or_none()

        if po_obj:
            await self.session.delete(po_obj)

    async def list(
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

        result = await self.session.execute(query)
        pos = result.scalars().all()

        return [self.mapper.to_domain(po) for po in pos]

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

        result = await self.session.execute(query)
        return result.scalar_one()

    async def exists(self, product_id: str) -> bool:
        """Check if product exists"""
        result = await self.session.execute(
            select(func.count()).select_from(ProductPO).where(ProductPO.id == product_id)
        )
        count = result.scalar_one()
        return count > 0
