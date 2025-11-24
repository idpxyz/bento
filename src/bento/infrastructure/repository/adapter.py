"""Repository Adapter implementation.

This module provides the adapter that implements the Domain Repository Port
by bridging between Aggregate Roots and Persistence Objects using Mappers.

Architecture:
    Domain (AR) -> Adapter -> Mapper -> BaseRepository -> Database (PO)
"""

from __future__ import annotations

from typing import Protocol, cast, runtime_checkable

from bento.application.ports.mapper import Mapper
from bento.core.ids import EntityId
from bento.domain.entity import Entity
from bento.domain.ports.repository import Repository as IRepository
from bento.infrastructure.repository.mixins import (
    AggregateQueryMixin,
    BatchOperationsMixin,
    ConditionalUpdateMixin,
    GroupByQueryMixin,
    RandomSamplingMixin,
    SoftDeleteEnhancedMixin,
    SortingLimitingMixin,
    UniquenessChecksMixin,
)
from bento.persistence.repository.sqlalchemy import BaseRepository
from bento.persistence.specification import CompositeSpecification, Page, PageParams


@runtime_checkable
class HasVersion(Protocol):
    version: int | None


class RepositoryAdapter[AR: Entity, PO, ID: EntityId](
    # P0 Mixins
    BatchOperationsMixin,
    UniquenessChecksMixin,
    # P1 Mixins
    AggregateQueryMixin,
    SortingLimitingMixin,
    ConditionalUpdateMixin,
    # P2 Mixins
    GroupByQueryMixin,
    SoftDeleteEnhancedMixin,
    # P3 Mixins
    RandomSamplingMixin,
    # Base
    IRepository[AR, ID],
):
    """Repository Adapter implementing Domain Repository Port.

    This adapter provides the bridge between Domain layer (Aggregate Roots)
    and Infrastructure layer (Persistence Objects), using a Mapper for
    transformation and delegating to BaseRepository for database operations.

    Responsibilities:
    1. Implements domain.ports.Repository Protocol
    2. Uses Mapper for AR �?PO transformation
    3. Delegates to BaseRepository for PO database operations
    4. Handles errors and provides logging
    5. Manages Specification conversion (AR �?PO)

    Type Parameters:
        AR: Aggregate Root type (Domain)
        PO: Persistence Object type (Infrastructure)
        ID: ID type

    Example:
        ```python
        from sqlalchemy.ext.asyncio import AsyncSession
        from bento.infrastructure.repository import RepositoryAdapter
        from bento.application.mapper import MapperStrategy
        from bento.persistence.repository import BaseRepository
        from bento.persistence.interceptor import create_default_chain

        class UserRepository(RepositoryAdapter[User, UserPO, str]):
            def __init__(self, session: AsyncSession, actor: str = "system"):
                # Create mapper (inherit from MapperStrategy)
                mapper = UserMapper()  # Your custom Mapper[User, UserPO]

                # Create base repository
                base_repo = BaseRepository(
                    session=session,
                    po_type=UserPO,
                    actor=actor,
                    interceptor_chain=create_default_chain(actor)
                )

                # Initialize adapter
                super().__init__(repository=base_repo, mapper=mapper)

        # Usage
        async def main():
            repo = UserRepository(session, actor="admin@example.com")

            # Get
            user = await repo.get("user-001")  # DB �?PO �?AR

            # Save
            await repo.save(user)  # AR �?PO �?DB

            # Query with Specification
            spec = EntitySpecificationBuilder().is_active().build()
            users = await repo.list(spec)  # DB �?PO �?AR (batch)
        ```
    """

    def __init__(
        self,
        repository: BaseRepository[PO, ID],
        mapper: Mapper[AR, PO],
    ) -> None:
        """Initialize repository adapter.

        Args:
            repository: BaseRepository for PO database operations
            mapper: Mapper for AR �?PO transformation
        """
        self._repository = repository
        self._mapper = mapper

    # ==================== Properties ====================

    @property
    def repository(self) -> BaseRepository[PO, ID]:
        """Get underlying repository."""
        return self._repository

    @property
    def mapper(self) -> Mapper[AR, PO]:
        """Get mapper."""
        return self._mapper

    # ==================== IRepository Implementation ====================

    async def get(self, id: ID) -> AR | None:
        """Get aggregate root by ID.

        Flow: Database �?PO �?AR

        Args:
            id: Entity ID

        Returns:
            Aggregate root if found, None otherwise

        Example:
            ```python
            user = await repo.get("user-001")
            if user:
                print(user.name)
            ```
        """
        po = await self._repository.get_po_by_id(id)
        if po is None:
            return None
        return self._mapper.map_reverse(po)  # PO �?AR

    async def save(self, aggregate: AR) -> AR:
        """Save aggregate root (create or update).

        Flow: AR �?PO �?Database

        The adapter determines whether to create or update based on
        whether the aggregate has an ID.

        Args:
            aggregate: Aggregate root to save

        Returns:
            The saved aggregate root (same instance, for fluent API)

        Example:
            ```python
            user = User(id="user-001", name="John")
            saved_user = await repo.save(user)  # Creates or updates
            ```
        """
        # Convert AR �?PO
        po = self._mapper.map(aggregate)

        # Check if aggregate exists (has ID)
        aggregate_id = getattr(po, "id", None)

        if aggregate_id is None:
            # Create new
            await self._repository.create_po(po)
        else:
            # Check if exists in database
            existing = await self._repository.get_po_by_id(aggregate_id)
            if existing is None:
                # Create
                await self._repository.create_po(po)
            else:
                # Propagate current version to transient PO to satisfy optimistic lock interceptor
                try:
                    if isinstance(existing, HasVersion) and isinstance(po, HasVersion):
                        if po.version in (None, 0):
                            po.version = existing.version
                except Exception:
                    pass
                # Update
                await self._repository.update_po(po)

        # Ensure the current UoW can collect domain events from this aggregate
        try:
            session = self._repository.session  # AsyncSession
            sync_sess = getattr(session, "sync_session", None)
            info = sync_sess.info if sync_sess is not None else session.info
            uow = info.get("uow")
            if uow and hasattr(uow, "track"):
                uow.track(aggregate)  # type: ignore[no-any-return]
        except Exception:
            # Best-effort: do not block persistence if UoW is not available
            pass

        # Return the saved aggregate for fluent API and to match Repository protocol
        return aggregate

    async def list(self, specification: CompositeSpecification[AR] | None = None) -> list[AR]:
        """List aggregate roots matching specification.

        Flow: Database �?PO (batch) �?AR (batch)

        Args:
            specification: Optional specification to filter results.
                         If None, returns all entities.

        Returns:
            List of matching aggregate roots

        Example:
            ```python
            # All users
            all_users = await repo.list()

            # With specification
            spec = EntitySpecificationBuilder().is_active().build()
            active_users = await repo.list(spec)
            ```
        """
        if specification is None:
            # Query all
            pos = await self._repository.query_po_by_spec(None)  # type: ignore[arg-type]
        else:
            # Convert specification AR �?PO
            po_spec = self._convert_spec_to_po(specification)
            pos = await self._repository.query_po_by_spec(po_spec)

        # Batch convert PO �?AR
        return self._mapper.map_reverse_list(pos)

    # ==================== Extended Query Methods ====================

    async def find_one(self, specification: CompositeSpecification[AR]) -> AR | None:
        """Find single aggregate root matching specification.

        Args:
            specification: Specification to match

        Returns:
            First matching aggregate root or None

        Example:
            ```python
            spec = EntitySpecificationBuilder().equals("email", "john@example.com").build()
            user = await repo.find_one(spec)
            ```
        """
        # Add limit 1 to specification
        page_params = PageParams(page=1, size=1)
        limited_spec = specification.with_page(page_params)
        po_spec = self._convert_spec_to_po(limited_spec)

        pos = await self._repository.query_po_by_spec(po_spec)
        if not pos:
            return None

        return self._mapper.map_reverse(pos[0])

    async def find_all(self, specification: CompositeSpecification[AR]) -> list[AR]:
        """Find all aggregate roots matching specification.

        Alias for list() with specification.

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

        Example:
            ```python
            spec = EntitySpecificationBuilder().is_active().build()
            page = await repo.find_page(spec, PageParams(page=1, size=20))

            print(f"Total: {page.total}")
            print(f"Has next: {page.has_next}")
            for user in page.items:
                print(user.name)
            ```
        """
        # 1. Count total (without pagination)
        total = await self.count(specification)

        if total == 0:
            return Page.create(items=[], total=0, page=1, size=page_params.size)

        # 2. Query page of results
        paged_spec = specification.with_page(page_params)
        po_spec = self._convert_spec_to_po(paged_spec)
        pos = await self._repository.query_po_by_spec(po_spec)

        # 3. Convert PO �?AR (batch)
        items = self._mapper.map_reverse_list(pos)

        return Page.create(
            items=items,
            total=total,
            page=page_params.page,
            size=page_params.size,
        )

    async def count(self, specification: CompositeSpecification[AR]) -> int:
        """Count aggregate roots matching specification.

        Args:
            specification: Specification to match

        Returns:
            Count of matching entities

        Example:
            ```python
            spec = EntitySpecificationBuilder().is_active().build()
            count = await repo.count(spec)
            print(f"Active users: {count}")
            ```
        """
        po_spec = self._convert_spec_to_po(specification)
        return await self._repository.count_po_by_spec(po_spec)

    async def exists(self, specification: CompositeSpecification[AR]) -> bool:
        """Check if any aggregate roots match specification.

        Args:
            specification: Specification to match

        Returns:
            True if at least one entity matches

        Example:
            ```python
            spec = EntitySpecificationBuilder().equals("email", "test@example.com").build()
            if await repo.exists(spec):
                print("Email already exists")
            ```
        """
        count = await self.count(specification)
        return count > 0

    async def delete(self, aggregate: AR) -> None:
        """Delete aggregate root.

        Flow: AR �?PO �?Database (soft delete via interceptor)

        Args:
            aggregate: Aggregate root to delete

        Note:
            If SoftDeleteInterceptor is enabled, this will be a soft delete.
            In DDD, deleting an aggregate root should also handle the deletion
            of all entities within the aggregate boundary.

        Example:
            ```python
            user = await repo.get("user-001")
            await repo.delete(user)  # Soft deleted
            ```
        """
        po = self._mapper.map(aggregate)  # AR �?PO
        await self._repository.delete_po(po)

    # ==================== Batch Operations ====================

    async def save_all(self, aggregates: list[AR]) -> None:
        """Save multiple aggregate roots (batch operation).

        Args:
            aggregates: List of aggregate roots to save

        Example:
            ```python
            users = [User(...), User(...), User(...)]
            await repo.save_all(users)
            ```
        """
        if not aggregates:
            return

        pos = self._mapper.map_list(aggregates)  # AR �?PO (batch)
        await self._repository.batch_po_create(pos)

    async def delete_all(self, aggregates: list[AR]) -> None:
        """Delete multiple aggregate roots (batch operation).

        Args:
            aggregates: List of aggregate roots to delete

        Example:
            ```python
            old_users = await repo.find_all(old_users_spec)
            await repo.delete_all(old_users)
            ```
        """
        if not aggregates:
            return

        pos = self._mapper.map_list(aggregates)  # AR �?PO (batch)
        await self._repository.batch_po_delete(pos)

    # ==================== Helper Methods ====================

    def _convert_spec_to_po(
        self, ar_spec: CompositeSpecification[AR]
    ) -> CompositeSpecification[PO]:
        """Convert Specification from AR to PO.

        Note:
            This is a simplified implementation that assumes field names
            are identical between AR and PO. For complex mappings, this
            method should be overridden to handle field name transformations.

        Args:
            ar_spec: Specification for Aggregate Root

        Returns:
            Specification for Persistence Object
        """
        # Cast the specification to the PO type since the field names are identical
        # The type system sees these as different types due to Generic[T]
        return cast(CompositeSpecification[PO], ar_spec)
