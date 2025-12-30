"""Unit tests for resource-based authorization."""

from dataclasses import dataclass

import pytest

from bento.core.exceptions import DomainException
from bento.security import (
    AdminBypassAuthorizer,
    CurrentUser,
    OwnershipAuthorizer,
    check_resource_access,
)


@dataclass
class Order:
    """Test resource."""
    id: str
    created_by: str


class TestOwnershipAuthorizer:
    """Test OwnershipAuthorizer."""

    @pytest.mark.asyncio
    async def test_user_owns_resource(self):
        """Test user can access their own resource."""
        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-1")

        result = await authorizer.authorize(user, "read", order)
        assert result is True

    @pytest.mark.asyncio
    async def test_user_does_not_own_resource(self):
        """Test user cannot access others' resources."""
        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-2")

        result = await authorizer.authorize(user, "read", order)
        assert result is False

    @pytest.mark.asyncio
    async def test_resource_without_owner_id(self):
        """Test resource without owner_id attribute."""
        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())

        # Object without owner_id
        class NoOwner:
            pass

        result = await authorizer.authorize(user, "read", NoOwner())
        assert result is False


class TestAdminBypassAuthorizer:
    """Test AdminBypassAuthorizer."""

    @pytest.mark.asyncio
    async def test_admin_can_access_any_resource(self):
        """Test admin can access any resource."""
        base_authorizer = OwnershipAuthorizer()
        authorizer = AdminBypassAuthorizer(base_authorizer)

        admin = CurrentUser(id="admin-1", permissions=(), roles=("admin",))
        order = Order(id="order-1", created_by="user-1")

        result = await authorizer.authorize(admin, "delete", order)
        assert result is True

    @pytest.mark.asyncio
    async def test_non_admin_uses_base_authorizer(self):
        """Test non-admin uses base authorizer."""
        base_authorizer = OwnershipAuthorizer()
        authorizer = AdminBypassAuthorizer(base_authorizer)

        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-1")

        result = await authorizer.authorize(user, "read", order)
        assert result is True

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_others_resource(self):
        """Test non-admin cannot access others' resources."""
        base_authorizer = OwnershipAuthorizer()
        authorizer = AdminBypassAuthorizer(base_authorizer)

        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-2")

        result = await authorizer.authorize(user, "read", order)
        assert result is False


class TestCheckResourceAccess:
    """Test check_resource_access function."""

    @pytest.mark.asyncio
    async def test_authorized_access(self):
        """Test authorized access does not raise."""
        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-1")

        # Should not raise
        await check_resource_access(user, "read", order, authorizer)

    @pytest.mark.asyncio
    async def test_unauthorized_access_raises(self):
        """Test unauthorized access raises FORBIDDEN."""
        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-2")

        with pytest.raises(DomainException) as exc_info:
            await check_resource_access(user, "read", order, authorizer)

        assert exc_info.value.reason_code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_forbidden_includes_details(self):
        """Test FORBIDDEN exception includes action and resource type."""
        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-2")

        with pytest.raises(DomainException) as exc_info:
            await check_resource_access(user, "delete", order, authorizer)

        details = exc_info.value.details
        assert details["action"] == "delete"
        assert details["resource_type"] == "Order"
