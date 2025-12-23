"""Tenant filter mixin for multi-tenant repository support.

This mixin provides automatic tenant filtering for repository operations,
ensuring data isolation between tenants.

Example:
    ```python
    class ProductRepository(TenantFilterMixin, RepositoryAdapter[Product, ProductPO, ID]):
        pass

    # All operations automatically tenant-scoped
    TenantContext.set("tenant-123")
    products = await repo.find_all()  # Only tenant-123's products
    ```
"""

from __future__ import annotations

from typing import Any, TypeVar

from bento.domain.aggregate import AggregateRoot
from bento.persistence.specification import CompositeSpecification

AR = TypeVar("AR", bound=AggregateRoot)


class TenantFilterMixin:
    """Mixin for automatic tenant filtering in repositories.

    This mixin automatically:
    - Adds tenant_id filter to all queries
    - Sets tenant_id on save operations
    - Validates tenant on get operations

    Configuration:
        tenant_field: Name of the tenant field (default: "tenant_id")
        tenant_enabled: Whether tenant filtering is enabled (default: True)

    Example:
        ```python
        from bento.infrastructure.repository import RepositoryAdapter
        from bento.infrastructure.repository.mixins import TenantFilterMixin

        class OrderRepository(TenantFilterMixin, RepositoryAdapter[Order, OrderPO, ID]):
            tenant_field = "tenant_id"  # Optional, this is the default

        # Usage
        TenantContext.set("tenant-123")
        orders = await repo.find_all()  # Automatically filtered
        await repo.save(order)  # Automatically sets tenant_id
        ```
    """

    tenant_field: str = "tenant_id"
    """Name of the tenant field in aggregates and POs"""

    tenant_enabled: bool = True
    """Whether tenant filtering is enabled"""

    def _get_current_tenant(self) -> str | None:
        """Get current tenant from context.

        Returns:
            Current tenant ID or None
        """
        from bento.security.tenant import TenantContext
        return TenantContext.get()

    def _apply_tenant_filter(
        self,
        specification: CompositeSpecification[AR] | None,
    ) -> CompositeSpecification[AR] | None:
        """Add tenant filter to specification.

        Args:
            specification: Original specification (may be None)

        Returns:
            Specification with tenant filter applied, or None if no tenant
        """
        if not self.tenant_enabled:
            return specification

        tenant_id = self._get_current_tenant()
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

    def _inject_tenant_id(self, entity: Any) -> None:
        """Inject tenant_id into entity if not set.

        Args:
            entity: Entity to inject tenant_id into
        """
        if not self.tenant_enabled:
            return

        tenant_id = self._get_current_tenant()
        if not tenant_id:
            return

        if hasattr(entity, self.tenant_field):
            current_value = getattr(entity, self.tenant_field, None)
            if not current_value:
                setattr(entity, self.tenant_field, tenant_id)

    def _validate_tenant_ownership(self, entity: Any) -> bool:
        """Validate that entity belongs to current tenant.

        Args:
            entity: Entity to validate

        Returns:
            True if entity belongs to current tenant or no tenant context
        """
        if not self.tenant_enabled:
            return True

        tenant_id = self._get_current_tenant()
        if not tenant_id:
            return True  # No tenant context, allow access

        if hasattr(entity, self.tenant_field):
            entity_tenant = getattr(entity, self.tenant_field, None)
            if entity_tenant and entity_tenant != tenant_id:
                return False  # Entity belongs to different tenant

        return True
