"""SQLAlchemy base repository implementation.

This module provides persistence object (PO) repository implementation for SQLAlchemy,
integrating Specification pattern and Interceptor chain.

Note:
    This repository operates on Persistence Objects (PO) only.
    For Domain objects (Aggregate Roots), use RepositoryAdapter instead.
"""

from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bento.persistence.interceptor import (
    InterceptorChain,
    InterceptorContext,
    OperationType,
)
from bento.persistence.repository.sqlalchemy.mixins import (
    AggregateQueryMixin,
    BatchOperationsMixin,
    ConditionalUpdateMixin,
    GroupByQueryMixin,
    RandomSamplingMixin,
    SoftDeleteEnhancedMixin,
    SortingLimitingMixin,
    UniquenessChecksMixin,
)
from bento.persistence.specification import CompositeSpecification

# Type variables for Persistence Objects
PO = TypeVar("PO")  # Persistence Object
ID = TypeVar("ID")  # ID type


class BaseRepository[PO, ID](
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
):
    """Base repository for Persistence Object (PO) operations.

    This repository provides database operations for POs (SQLAlchemy models)
    with Specification and Interceptor support.

    Important:
        This repository does NOT implement domain.ports.Repository.
        It operates on POs, not Aggregate Roots.
        Use RepositoryAdapter to bridge Domain and Infrastructure layers.

    Type Parameters:
        PO: Persistence Object type (SQLAlchemy model)
        ID: ID type

    Example:
        ```python
        from bento.persistence.repository import BaseRepository
        from bento.persistence.interceptor import create_default_chain

        base_repo = BaseRepository(
            session=session,
            po_type=UserPO,
            actor="system",
            interceptor_chain=create_default_chain("system")
        )

        # PO operations
        po = await base_repo.get_po_by_id("user-001")
        await base_repo.create_po(po)
        ```
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        po_type: type[PO],
        actor: str = "system",
        interceptor_chain: InterceptorChain[PO] | None = None,
    ) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
            po_type: Type of persistence object (SQLAlchemy model)
            actor: Current actor/user for operations
            interceptor_chain: Optional custom interceptor chain
        """
        if not session:
            raise ValueError("Database session is required")

        self._session = session
        self._po_type = po_type
        self._actor = actor
        self._interceptor_chain = interceptor_chain

    @property
    def session(self) -> AsyncSession:
        """Get database session."""
        return self._session

    @property
    def po_type(self) -> type[PO]:
        """Get persistence object type."""
        return self._po_type

    @property
    def actor(self) -> str:
        """Get current actor."""
        return self._actor

    @property
    def interceptor_chain(self) -> InterceptorChain[PO] | None:
        """Get interceptor chain."""
        return self._interceptor_chain

    # ==================== PO Query Methods ====================

    async def get_po_by_id(self, id: ID) -> PO | None:
        """Get persistence object by ID.

        Uses session.get() for optimal performance.

        Args:
            id: Entity ID

        Returns:
            Persistence object if found, None otherwise
        """
        # Accept both raw PK (str/UUID/int) and ID-like wrappers that expose .value
        pk = getattr(id, "value", id)

        # Interceptor: allow cache short-circuit
        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.GET,
                actor=self._actor,
                context_data={"entity_id": pk},
            )
            cached = await self._interceptor_chain.execute_before(context)
            if cached is not None:
                return cached

        entity = await self._session.get(self._po_type, pk)

        if self._interceptor_chain and entity is not None:
            # Reuse same context when possible
            if "context" not in locals():
                context = InterceptorContext(
                    session=self._session,
                    entity_type=self._po_type,
                    operation=OperationType.GET,
                    actor=self._actor,
                    context_data={"entity_id": pk},
                )
            entity = await self._interceptor_chain.process_result(context, entity)

        return entity

    async def query_po_by_spec(self, spec: CompositeSpecification[PO]) -> list[PO]:
        """Query persistence objects using specification.

        Args:
            spec: Specification to match

        Returns:
            List of matching persistence objects
        """
        # Prepare context (optionally add serializable spec params if available)
        context = None
        if self._interceptor_chain:
            params: dict | None = None
            to_cache_params = getattr(spec, "to_cache_params", None)
            if callable(to_cache_params):
                try:
                    params = to_cache_params()

                except Exception:
                    params = None
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.QUERY,
                actor=self._actor,
                context_data={"query_params": params} if params else {},
            )
            cached = await self._interceptor_chain.execute_before(context)
            if cached is not None:
                return cached

        # Simplified implementation
        stmt = select(self._po_type)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        if self._interceptor_chain and context is not None and rows is not None:
            # Batch process to allow caching strategies
            rows = await self._interceptor_chain.process_batch_results(context, rows)

        return rows

    async def count_po_by_spec(self, spec: CompositeSpecification[PO]) -> int:
        """Count persistence objects matching specification.

        Args:
            spec: Specification to match

        Returns:
            Count of matching persistence objects
        """
        # Simplified implementation
        stmt = select(func.count()).select_from(self._po_type)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    # ==================== Write Operations ====================

    async def create_po(self, po: PO) -> PO:
        """Create persistence object with interceptor support.

        Args:
            po: Persistence object to create

        Returns:
            Created persistence object
        """
        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.CREATE,
                entity=po,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)

        self._session.add(po)
        await self._session.flush()
        if self._interceptor_chain:
            po = await self._interceptor_chain.process_result(context, po)

        return po

    async def update_po(self, po: PO) -> PO:
        """Update persistence object with interceptor support.

        Args:
            po: Persistence object to update

        Returns:
            Updated persistence object

        Raises:
            StaleDataError: If version conflict detected (SQLAlchemy native)

        Note:
            Optimistic locking is handled by SQLAlchemy's version_id_col.
            Enable it in your ORM model:
            ```python
            __mapper_args__ = {"version_id_col": "version"}
            ```
        """
        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.UPDATE,
                entity=po,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)

        merged = await self._session.merge(po)
        await self._session.flush()

        if self._interceptor_chain:
            merged = await self._interceptor_chain.process_result(context, merged)

        return merged

    async def delete_po(self, po: PO) -> None:
        """Delete persistence object.

        Note:
            If SoftDeleteInterceptor is enabled, this will be a soft delete.

        Args:
            po: Persistence object to delete
        """
        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.DELETE,
                entity=po,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)

        # Ensure the object is in the session before deleting
        merged_po = await self._session.merge(po)
        await self._session.delete(merged_po)
        await self._session.flush()

        # Trigger invalidation if needed
        if self._interceptor_chain:
            # pass through result None to allow invalidation logic in interceptors
            await self._interceptor_chain.process_result(context, po)

    # ==================== Batch Operations ====================

    async def batch_po_create(self, pos: list[PO]) -> list[PO]:
        """Batch create persistence objects.

        Args:
            pos: List of persistence objects to create

        Returns:
            List of created persistence objects
        """
        if not pos:
            return []

        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.BATCH_CREATE,
                entities=pos,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)

        for po in pos:
            self._session.add(po)

        await self._session.flush()

        if self._interceptor_chain:
            pos = await self._interceptor_chain.process_batch_results(context, pos)
        return pos

    async def batch_po_update(self, pos: list[PO]) -> list[PO]:
        """Batch update persistence objects.

        Args:
            pos: List of persistence objects to update

        Returns:
            List of updated persistence objects
        """
        if not pos:
            return []

        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.BATCH_UPDATE,
                entities=pos,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)

        for po in pos:
            await self._session.merge(po)

        await self._session.flush()
        if self._interceptor_chain:
            pos = await self._interceptor_chain.process_batch_results(context, pos)
        return pos

    async def batch_po_delete(self, pos: list[PO]) -> None:
        """Batch delete persistence objects.

        Args:
            pos: List of persistence objects to delete
        """
        if not pos:
            return

        if self._interceptor_chain:
            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.BATCH_DELETE,
                entities=pos,
                actor=self._actor,
            )
            await self._interceptor_chain.execute_before(context)

        for po in pos:
            merged_po = await self._session.merge(po)
            await self._session.delete(merged_po)

        await self._session.flush()
        if self._interceptor_chain:
            await self._interceptor_chain.process_batch_results(context, pos)
