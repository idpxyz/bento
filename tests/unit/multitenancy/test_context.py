"""Tests for TenantContext."""

from __future__ import annotations

import pytest

from bento.core.exceptions import DomainException
from bento.multitenancy import TenantContext


@pytest.fixture(autouse=True)
def clear_context():
    """Clear tenant context before and after each test."""
    TenantContext.clear()
    yield
    TenantContext.clear()


class TestTenantContext:
    """Tests for TenantContext."""

    def test_get_returns_none_when_not_set(self):
        """get() should return None when tenant is not set."""
        assert TenantContext.get() is None

    def test_set_and_get(self):
        """set() and get() should work together."""
        TenantContext.set("tenant-123")
        assert TenantContext.get() == "tenant-123"

    def test_require_returns_tenant_when_set(self):
        """require() should return tenant when set."""
        TenantContext.set("tenant-456")
        assert TenantContext.require() == "tenant-456"

    def test_require_raises_when_not_set(self):
        """require() should raise TENANT_REQUIRED when not set."""
        with pytest.raises(DomainException) as exc_info:
            TenantContext.require()

        assert exc_info.value.reason_code == "TENANT_REQUIRED"

    def test_clear(self):
        """clear() should remove tenant."""
        TenantContext.set("tenant-789")
        assert TenantContext.get() == "tenant-789"

        TenantContext.clear()
        assert TenantContext.get() is None

    def test_set_none_clears(self):
        """set(None) should clear tenant."""
        TenantContext.set("tenant-123")
        TenantContext.set(None)
        assert TenantContext.get() is None
