"""Order repository implementation using RepositoryAdapter.

This repository automatically inherits all CRUD methods from RepositoryAdapter:
- get(id), save(order), delete(order)
- list(spec), find_one(spec), find_page(spec, page)
- count(spec), exists(spec)
- save_all(orders), delete_all(orders)

Features:
- Automatic Interceptor support (audit/soft-delete/optimistic-lock)
- Domain ↔ Persistence mapping via AutoMapper
- Specification-based queries with FluentSpecificationBuilder
- Only need to define custom business queries
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.persistence.mappers import OrderMapper
from applications.ecommerce.modules.order.persistence.models import OrderModel
from bento.core.ids import ID
from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from bento.persistence.specification import CompositeSpecification, Page, PageParams
from bento.persistence.specification.builder import FluentSpecificationBuilder


class OrderRepository(RepositoryAdapter[Order, OrderModel, ID]):
    """Order repository using RepositoryAdapter pattern.

    Example:
        ```python
        # Initialize
        repo = OrderRepository(session, actor="user@example.com")

        # Use inherited CRUD methods
        order = await repo.get(ID("order-001"))
        await repo.save(order)
        await repo.delete(order)

        # Query with Specification
        spec = FluentSpecificationBuilder(OrderModel).equals("status", "paid").build()
        paid_orders = await repo.list(spec)

        # Pagination
        page = await repo.find_page(spec, PageParams(page=1, size=20))

        # Custom queries
        unpaid_orders = await repo.find_unpaid()
        customer_orders = await repo.find_by_customer(customer_id)
        ```
    """

    def __init__(self, session: AsyncSession, actor: str = "system"):
        """Initialize order repository.

        Args:
            session: SQLAlchemy async session
            actor: Actor performing operations (for audit fields)
        """
        # Create mapper and base repository with interceptors
        mapper = OrderMapper()
        base_repo = BaseRepository(
            session=session,
            po_type=OrderModel,
            actor=actor,
            interceptor_chain=create_default_chain(actor),
        )

        # Initialize adapter
        super().__init__(repository=base_repo, mapper=mapper)
        self._session = session

    async def get(self, id: ID) -> Order | None:
        """Override get to eager load items relationship."""
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == id.value)
            .options(selectinload(OrderModel.items))
        )
        result = await self._session.execute(stmt)
        po = result.scalar_one_or_none()

        if po is None:
            return None
        return self._mapper.map_reverse(po)

    async def list(self, specification: CompositeSpecification | None = None) -> list[Order]:
        """Override list to eager load items relationship."""
        if specification is None:
            stmt = select(OrderModel).options(selectinload(OrderModel.items))
            result = await self._session.execute(stmt)
            pos = result.scalars().all()
        else:
            # Query with specification, then re-query with eager loading
            po_spec = self._convert_spec_to_po(specification)
            temp_pos = await self._repository.query_po_by_spec(po_spec)

            if not temp_pos:
                return []

            ids = [po.id for po in temp_pos]
            stmt = (
                select(OrderModel)
                .where(OrderModel.id.in_(ids))
                .options(selectinload(OrderModel.items))
            )
            result = await self._session.execute(stmt)
            pos = result.scalars().all()

        return [self._mapper.map_reverse(po) for po in pos]

    async def find_page(
        self,
        specification: CompositeSpecification,
        page_params: PageParams,
    ) -> Page[Order]:
        """Override find_page to handle pagination with eager loading."""
        total = await self.count(specification)

        if total == 0:
            return Page.create(items=[], total=0, page=1, size=page_params.size)

        paged_spec = specification.with_page(page_params)
        items = await self.list(paged_spec)

        return Page.create(
            items=items,
            total=total,
            page=page_params.page,
            size=page_params.size,
        )

    # ==================== Custom Queries ====================

    async def find_unpaid(self) -> list[Order]:
        """Find all unpaid orders (status = pending)."""
        spec = (
            FluentSpecificationBuilder(OrderModel)
            .equals("status", "pending")
            .order_by("created_at", descending=True)
            .build()
        )
        return await self.list(spec)

    async def find_by_customer(self, customer_id: ID) -> list[Order]:
        """Find all orders for a specific customer."""
        spec = (
            FluentSpecificationBuilder(OrderModel)
            .equals("customer_id", customer_id.value)
            .order_by("created_at", descending=True)
            .build()
        )
        return await self.list(spec)

    async def find_by_status(self, status: str) -> list[Order]:
        """Find orders by status."""
        spec = (
            FluentSpecificationBuilder(OrderModel)
            .equals("status", status)
            .order_by("created_at", descending=True)
            .build()
        )
        return await self.list(spec)

    async def find_recent(self, limit: int = 10) -> list[Order]:
        """Find most recent orders."""
        spec = (
            FluentSpecificationBuilder(OrderModel)
            .order_by("created_at", descending=True)
            .limit(limit)
            .build()
        )
        return await self.list(spec)

    async def count_by_status(self, status: str) -> int:
        """Count orders by status."""
        spec = FluentSpecificationBuilder(OrderModel).equals("status", status).build()
        return await self.count(spec)

    async def has_customer_orders(self, customer_id: ID) -> bool:
        """Check if customer has any orders."""
        spec = (
            FluentSpecificationBuilder(OrderModel).equals("customer_id", customer_id.value).build()
        )
        return await self.exists(spec)
