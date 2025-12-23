"""Tenant-aware repository adapter for multi-tenant applications.

This module provides a repository adapter that automatically filters
and injects tenant_id for all operations.

Example:
    ```python
    from bento.infrastructure.repository.tenant_aware import TenantAwareRepositoryAdapter

    class ProductRepository(TenantAwareRepositoryAdapter[Product, ProductPO]):
        pass

    # All queries automatically filtered by current tenant
    products = await repo.find_all()  # Only current tenant's products
    ```
"""

from __future__ import annotations

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.infrastructure.repository.adapter import RepositoryAdapter
from bento.persistence.po import Base
from bento.persistence.specification import CompositeSpecification
from bento.security.tenant import TenantContext


class TenantAwareRepositoryAdapter[AR: AggregateRoot, PO: Base, ID: EntityId](
    RepositoryAdapter[AR, PO, ID]
):
    """Repository adapter with automatic tenant filtering.

    This adapter automatically:
    - Adds tenant_id filter to all queries
    - Sets tenant_id on save operations
    - Validates tenant on get operations

    Example:
        ```python
        class OrderRepository(TenantAwareRepositoryAdapter[Order, OrderPO]):
            pass

        # Setup
        TenantContext.set("tenant-123")

        # All operations are tenant-scoped
        orders = await repo.find_all()  # Only tenant-123's orders
        await repo.save(order)  # Automatically sets tenant_id
        ```
    """

    tenant_field: str = "tenant_id"
    """Name of the tenant field in aggregates and POs"""

    async def find_all(
        self,
        specification: CompositeSpecification[AR] | None = None,
    ) -> list[AR]:
        """Find all entities with automatic tenant filtering.

        Args:
            specification: Optional query specification

        Returns:
            List of entities belonging to current tenant
        """
        specification = self._apply_tenant_filter(specification)
        return await super().find_all(specification)

    async def find_page(
        self,
        specification: CompositeSpecification[AR],
        page_params,
    ):
        """Find page with automatic tenant filtering.

        Args:
            specification: Query specification
            page_params: Pagination parameters

        Returns:
            Page of entities belonging to current tenant
        """
        filtered_spec = self._apply_tenant_filter(specification)
        return await super().find_page(filtered_spec or specification, page_params)

    async def paginate(
        self,
        specification: CompositeSpecification[AR] | None = None,
        page: int = 1,
        size: int = 20,
    ):
        """Paginate with automatic tenant filtering.

        Args:
            specification: Optional query specification
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Page of entities belonging to current tenant
        """
        specification = self._apply_tenant_filter(specification)
        return await super().paginate(specification, page, size)

    async def count(
        self,
        specification: CompositeSpecification[AR] | None = None,
    ) -> int:
        """Count entities with automatic tenant filtering.

        Args:
            specification: Optional query specification

        Returns:
            Count of entities belonging to current tenant
        """
        specification = self._apply_tenant_filter(specification)
        return await super().count(specification)

    async def get(self, id):
        """Get entity by ID with tenant validation.

        Args:
            id: Entity ID

        Returns:
            Entity if found and belongs to current tenant, None otherwise
        """
        entity = await super().get(id)
        if entity is None:
            return None

        # Validate tenant ownership
        if hasattr(entity, self.tenant_field):
            entity_tenant = getattr(entity, self.tenant_field)
            current_tenant = TenantContext.get()
            if current_tenant and entity_tenant != current_tenant:
                return None  # Entity belongs to different tenant

        return entity

    async def save(self, aggregate: AR) -> AR:
        """Save entity with automatic tenant_id injection.

        Args:
            aggregate: Entity to save

        Returns:
            Saved entity with tenant_id set
        """
        self._inject_tenant_id(aggregate)
        return await super().save(aggregate)

    def _apply_tenant_filter(
        self,
        specification: CompositeSpecification[AR] | None,
    ) -> CompositeSpecification[AR] | None:
        """Add tenant filter to specification.

        Args:
            specification: Original specification

        Returns:
            Specification with tenant filter applied
        """
        tenant_id = TenantContext.get()
        if not tenant_id:
            return specification

        from bento.persistence.specification import EntitySpecificationBuilder

        tenant_spec = (
            EntitySpecificationBuilder()
            .where(self.tenant_field, "=", tenant_id)
            .build()
        )

        if specification is None:
            return tenant_spec

        return specification.and_(tenant_spec)

    def _inject_tenant_id(self, aggregate: AR) -> None:
        """Inject tenant_id into aggregate if not set.

        Args:
            aggregate: Entity to inject tenant_id into
        """
        tenant_id = TenantContext.get()
        if not tenant_id:
            return

        if hasattr(aggregate, self.tenant_field):
            current_value = getattr(aggregate, self.tenant_field, None)
            if not current_value:
                setattr(aggregate, self.tenant_field, tenant_id)
