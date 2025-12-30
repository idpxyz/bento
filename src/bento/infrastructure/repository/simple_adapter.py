"""Simple Repository Adapter for AR = PO scenarios.

This module provides a simplified repository adapter for cases where
the Aggregate Root and Persistence Object are the same entity.

Use this adapter when:
- AR and PO structures are identical
- Simple CRUD operations
- Quick development / MVP phase
- Performance-sensitive scenarios (no conversion overhead)

This adapter implements the same domain.ports.Repository Protocol
as RepositoryAdapter, ensuring API consistency while reducing complexity.
"""

from __future__ import annotations

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.domain.ports.repository import IRepository
from bento.infrastructure.repository.mixins import TenantFilterMixin
from bento.persistence.repository.sqlalchemy import BaseRepository
from bento.persistence.specification import CompositeSpecification, Page, PageParams


class SimpleRepositoryAdapter[AR: AggregateRoot, ID: EntityId](
    TenantFilterMixin,
    IRepository[AR, ID],
):
    """Simple Repository Adapter for AR = PO scenarios.

    This adapter is designed for cases where the Aggregate Root and
    Persistence Object are the same (e.g., using SQLAlchemy
    DeclarativeBase with AggregateRoot).

    Key Features:
    - No Mapper needed (no AR �?PO conversion)
    - Direct delegation to BaseRepository
    - Same API as RepositoryAdapter (domain.ports.Repository)
    - Lower complexity and overhead
    - Better performance (no conversion cost)

    When to Use:
    - �?Simple CRUD entities
    - �?AR and PO structures match
    - �?Quick development / MVP
    - �?Performance-sensitive scenarios
    - �?Support/auxiliary domains (audit logs, configs, etc.)

    When NOT to Use:
    - �?Complex domain logic requiring AR �?PO separation
    - �?Need to support multiple persistence strategies
    - �?Complex ValueObject transformations
    - �?Core domain entities (use RepositoryAdapter instead)

    Example:
        ```python
        from sqlalchemy.orm import DeclarativeBase
        from bento.domain.entity import AggregateRoot
        from sqlalchemy import Column, String, Boolean
        from bento.infrastructure.repository import SimpleRepositoryAdapter
        from bento.persistence.repository import BaseRepository
        from bento.persistence.interceptor import create_default_chain

        # Domain + PO (same entity)
        class User(DeclarativeBase, AggregateRoot):
            __tablename__ = "users"

            id = Column(String, primary_key=True)
            name = Column(String)
            email = Column(String)
            is_active = Column(Boolean)

            # Business methods
            def activate(self):
                self.is_active = True

        # Repository (no Mapper needed)
        class UserRepository(SimpleRepositoryAdapter[User, str]):
            def __init__(self, session: AsyncSession, actor: str = "system"):
                base_repo = BaseRepository(
                    session=session,
                    po_type=User,  # Same as AR
                    actor=actor,
                    interceptor_chain=create_default_chain(actor)
                )
                super().__init__(repository=base_repo)

        # Usage (same API as RepositoryAdapter)
        repo = UserRepository(session, actor="admin")
        user = await repo.get("user-001")  # Direct return, no conversion
        await repo.save(user)  # Direct save, no conversion
        ```
    """

    def __init__(self, repository: BaseRepository[AR, ID]) -> None:
        """Initialize simple repository adapter.

        Args:
            repository: BaseRepository for PO operations
                       Note: AR here is both AR and PO (same entity)
        """
        self._repository = repository

    @property
    def repository(self) -> BaseRepository[AR, ID]:
        """Get underlying repository."""
        return self._repository

    # ==================== IRepository Implementation ====================

    async def get(self, id: ID) -> AR | None:
        """Get aggregate root by ID.

        Since AR = PO, directly return from repository without conversion.

        Args:
            id: Entity ID

        Returns:
            Aggregate root if found, None otherwise
        """
        return await self._repository.get_po_by_id(id)

    async def save(self, aggregate: AR) -> None:
        """Save aggregate root (create or update).

        Since AR = PO, directly save without conversion.

        Args:
            aggregate: Aggregate root to save
        """
        entity_id = getattr(aggregate, "id", None)

        if entity_id is None:
            # Create new
            await self._repository.create_po(aggregate)
        else:
            # Check if exists
            existing = await self._repository.get_po_by_id(entity_id)
            if existing is None:
                # Create
                await self._repository.create_po(aggregate)
            else:
                # Update
                await self._repository.update_po(aggregate)

    async def list(self, specification: CompositeSpecification[AR] | None = None) -> list[AR]:
        """List aggregate roots matching specification.

        Args:
            specification: Optional specification to filter results.
                         If None, returns all entities.

        Returns:
            List of matching aggregate roots
        """
        return await self._repository.query_po_by_spec(specification)  # type: ignore[arg-type]

    # ==================== Extended Query Methods ====================

    async def find_one(self, specification: CompositeSpecification[AR]) -> AR | None:
        """Find single aggregate root matching specification.

        Args:
            specification: Specification to match

        Returns:
            First matching aggregate root or None
        """
        page_params = PageParams(page=1, size=1)
        limited_spec = specification.with_page(page_params)
        results = await self._repository.query_po_by_spec(limited_spec)
        return results[0] if results else None

    async def find_all(self, specification: CompositeSpecification[AR]) -> list[AR]:
        """Find all aggregate roots matching specification.

        Args:
            specification: Specification to match

        Returns:
            List of matching aggregate roots
        """
        return await self.list(specification)

    async def find_page(
        self,
        specification: CompositeSpecification[AR],
        page_params: PageParams,
    ) -> Page[AR]:
        """Find paginated results matching specification.

        Args:
            specification: Specification to match
            page_params: Pagination parameters

        Returns:
            Page of results with metadata
        """
        # Get total count
        total = await self.count(specification)

        if total == 0:
            return Page.create(items=[], total=0, page=1, size=page_params.size)

        # Get page of results
        paged_spec = specification.with_page(page_params)
        items = await self._repository.query_po_by_spec(paged_spec)

        return Page.create(
            items=items,
            total=total,
            page=page_params.page,
            size=page_params.size,
        )

    async def count(self, specification: CompositeSpecification[AR] | None = None) -> int:
        """Count aggregate roots matching specification.

        Args:
            specification: Optional specification to match. If None, counts all entities.

        Returns:
            Count of matching entities
        """
        if specification is None:
            # 使用空 specification 计算所有项目
            from bento.persistence.specification import CompositeSpecification

            empty_spec = CompositeSpecification()
            return await self._repository.count_po_by_spec(empty_spec)
        return await self._repository.count_po_by_spec(specification)

    async def exists(self, specification: CompositeSpecification[AR]) -> bool:
        """Check if any aggregate roots match specification.

        Args:
            specification: Specification to match

        Returns:
            True if at least one entity matches
        """
        count = await self.count(specification)
        return count > 0

    async def paginate(
        self,
        specification: CompositeSpecification[AR] | None = None,
        page: int = 1,
        size: int = 20,
    ) -> Page[AR]:
        """Convenient pagination method without creating PageParams.

        This is a simplified version of find_page() that doesn't require
        creating a PageParams object. Ideal for simple pagination scenarios.

        Args:
            specification: Optional specification to filter results
            page: Page number, starting from 1 (default: 1)
            size: Page size (items per page) (default: 20)

        Returns:
            Page object with paginated data and metadata

        Example:
            ```python
            # Simple pagination
            page = await repo.paginate(page=1, size=20)

            # With specification
            spec = EntitySpecificationBuilder().where("status", "active").build()
            page = await repo.paginate(spec, page=2, size=10)
            ```
        """
        page_params = PageParams(page=page, size=size)

        # If no specification provided, create an empty one
        if specification is None:
            from bento.persistence.specification import CompositeSpecification

            specification = CompositeSpecification()

        return await self.find_page(specification, page_params)

    async def delete(self, aggregate: AR) -> None:
        """Delete aggregate root.

        Note:
            If SoftDeleteInterceptor is enabled, this will be a soft delete.

        Args:
            aggregate: Aggregate root to delete
        """
        await self._repository.delete_po(aggregate)

    # ==================== Batch Operations ====================

    async def save_all(self, aggregates: list[AR]) -> None:
        """Save multiple aggregate roots (batch operation).

        Args:
            aggregates: List of aggregate roots to save
        """
        if not aggregates:
            return

        await self._repository.batch_po_create(aggregates)

    async def delete_all(self, aggregates: list[AR]) -> None:
        """Delete multiple aggregate roots (batch operation).

        Args:
            aggregates: List of aggregate roots to delete
        """
        if not aggregates:
            return

        await self._repository.batch_po_delete(aggregates)
