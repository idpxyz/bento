"""Tenant-aware simple repository adapter for multi-tenant applications.

This module provides a simple repository adapter with automatic tenant filtering
for cases where AR = PO (no mapping needed).

Example:
    ```python
    from bento.infrastructure.repository import TenantAwareSimpleAdapter

    class ConfigRepository(TenantAwareSimpleAdapter[Config, ID]):
        pass

    # All queries automatically filtered by current tenant
    TenantContext.set("tenant-123")
    configs = await repo.find_all()  # Only tenant-123's configs
    ```
"""

from __future__ import annotations

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.infrastructure.repository.mixins import TenantFilterMixin
from bento.infrastructure.repository.simple_adapter import SimpleRepositoryAdapter
from bento.persistence.specification import CompositeSpecification


class TenantAwareSimpleAdapter[AR: AggregateRoot, ID: EntityId](
    TenantFilterMixin,
    SimpleRepositoryAdapter[AR, ID],
):
    """Simple repository adapter with automatic tenant filtering.

    Uses TenantFilterMixin to provide:
    - Automatic tenant_id filter on all queries
    - Automatic tenant_id injection on save
    - Tenant validation on get operations

    Use this when AR = PO (no mapping needed) and you need tenant isolation.

    Example:
        ```python
        from bento.infrastructure.repository import TenantAwareSimpleAdapter

        class AuditLogRepository(TenantAwareSimpleAdapter[AuditLog, ID]):
            tenant_field = "tenant_id"  # Optional, this is the default

        # Usage
        TenantContext.set("tenant-123")
        logs = await repo.find_all()  # Automatically filtered
        await repo.save(log)  # Automatically sets tenant_id
        ```
    """

    async def find_all(
        self,
        specification: CompositeSpecification[AR] | None = None,
    ) -> list[AR]:
        """Find all with automatic tenant filtering."""
        filtered = self._apply_tenant_filter(specification)
        return await super().find_all(filtered)

    async def find_page(self, specification: CompositeSpecification[AR], page_params):
        """Find page with automatic tenant filtering."""
        filtered = self._apply_tenant_filter(specification)
        return await super().find_page(filtered or specification, page_params)

    async def paginate(
        self,
        specification: CompositeSpecification[AR] | None = None,
        page: int = 1,
        size: int = 20,
    ):
        """Paginate with automatic tenant filtering."""
        filtered = self._apply_tenant_filter(specification)
        return await super().paginate(filtered, page, size)

    async def count(
        self,
        specification: CompositeSpecification[AR] | None = None,
    ) -> int:
        """Count with automatic tenant filtering."""
        filtered = self._apply_tenant_filter(specification)
        return await super().count(filtered)

    async def get(self, id):
        """Get by ID with tenant validation."""
        entity = await super().get(id)
        if entity and not self._validate_tenant_ownership(entity):
            return None
        return entity

    async def save(self, aggregate: AR) -> None:
        """Save with automatic tenant_id injection."""
        self._inject_tenant_id(aggregate)
        await super().save(aggregate)
