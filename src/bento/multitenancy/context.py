"""Tenant context for multi-tenant applications.

This module provides tenant context management using ContextVar
for async-safe, request-scoped tenant storage.

Example:
    ```python
    from bento.multitenancy import TenantContext

    # Set tenant (usually in middleware)
    TenantContext.set("tenant-123")

    # Get tenant (in business code)
    tenant_id = TenantContext.get()  # May be None
    tenant_id = TenantContext.require()  # Raises if None
    ```
"""

from __future__ import annotations

from contextvars import ContextVar

from bento.core.exceptions import DomainException


class TenantContext:
    """Tenant context - stores current request's tenant information.

    Uses ContextVar for async-safe, request-scoped tenant storage.

    Example:
        ```python
        # Set tenant (usually in middleware)
        TenantContext.set("tenant-123")

        # Get tenant (in business code)
        tenant_id = TenantContext.get()  # May be None
        tenant_id = TenantContext.require()  # Raises if None
        ```
    """

    _current_tenant: ContextVar[str | None] = ContextVar(
        'current_tenant', default=None
    )

    @classmethod
    def get(cls) -> str | None:
        """Get current tenant ID.

        Returns:
            Current tenant ID or None if not set
        """
        return cls._current_tenant.get()

    @classmethod
    def require(cls) -> str:
        """Get current tenant ID, raising if not set.

        Returns:
            Current tenant ID

        Raises:
            DomainException: If tenant is not set (TENANT_REQUIRED)
        """
        tenant_id = cls._current_tenant.get()
        if not tenant_id:
            raise DomainException(reason_code="TENANT_REQUIRED")
        return tenant_id

    @classmethod
    def set(cls, tenant_id: str | None) -> None:
        """Set current tenant ID.

        Args:
            tenant_id: Tenant ID to set, or None to clear
        """
        cls._current_tenant.set(tenant_id)

    @classmethod
    def clear(cls) -> None:
        """Clear current tenant."""
        cls._current_tenant.set(None)
