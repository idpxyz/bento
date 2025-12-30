"""Tests for security improvements (P0 and P1)."""

import pytest
from dataclasses import dataclass

from bento.security import (
    CurrentUser,
    SecurityContext,
    OwnershipAuthorizer,
    AdminBypassAuthorizer,
    check_resource_access,
)
from bento.core.exceptions import DomainException


@dataclass
class Order:
    """Test resource with created_by."""
    id: str
    created_by: str


@dataclass
class Article:
    """Test resource with user_id instead of owner_id."""
    id: str
    user_id: str


class TestPermissionCaching:
    """Test permission checking (simplified - caching is optional via Bento Cache)."""

    def test_permission_cache_hit(self):
        """Test that permission checks work correctly."""
        user = CurrentUser(
            id="user-1",
            permissions=("orders:*",),
        )

        # First check
        assert user.has_permission("orders:read") is True

        # Second check - should return same result
        assert user.has_permission("orders:read") is True

    def test_negative_permission_cached(self):
        """Test that negative permission checks work correctly."""
        user = CurrentUser(
            id="user-1",
            permissions=("orders:read",),
        )

        # Check for non-existent permission
        assert user.has_permission("products:write") is False

        # Second check - should return same result
        assert user.has_permission("products:write") is False

    def test_wildcard_permission_cached(self):
        """Test that wildcard matches work correctly."""
        user = CurrentUser(
            id="user-1",
            permissions=("orders:*",),
        )

        # Multiple wildcard matches
        assert user.has_permission("orders:read") is True
        assert user.has_permission("orders:write") is True
        assert user.has_permission("orders:delete") is True


class TestSecurityContextClear:
    """Test unified clear() behavior (P0-3)."""

    def setup_method(self):
        """Clear context before each test."""
        SecurityContext.clear()

    def test_clear_removes_both_user_and_tenant(self):
        """Test that clear() removes both user and tenant."""
        user = CurrentUser(id="user-1", permissions=(), roles=())
        SecurityContext.set_user(user)
        SecurityContext.set_tenant("tenant-1")

        # Both should be set
        assert SecurityContext.get_user() is not None
        assert SecurityContext.get_tenant() == "tenant-1"

        # Clear should remove both
        SecurityContext.clear()
        assert SecurityContext.get_user() is None
        assert SecurityContext.get_tenant() is None

    def test_clear_user_keeps_tenant(self):
        """Test that clear_user() keeps tenant."""
        user = CurrentUser(id="user-1", permissions=(), roles=())
        SecurityContext.set_user(user)
        SecurityContext.set_tenant("tenant-1")

        # Clear only user
        SecurityContext.clear_user()
        assert SecurityContext.get_user() is None
        assert SecurityContext.get_tenant() == "tenant-1"

    def test_clear_tenant_keeps_user(self):
        """Test that clear_tenant() keeps user."""
        user = CurrentUser(id="user-1", permissions=(), roles=())
        SecurityContext.set_user(user)
        SecurityContext.set_tenant("tenant-1")

        # Clear only tenant
        SecurityContext.clear_tenant()
        assert SecurityContext.get_user() is not None
        assert SecurityContext.get_tenant() is None


class TestOwnershipAuthorizerCustomField:
    """Test OwnershipAuthorizer with custom field (P1-1)."""

    @pytest.mark.asyncio
    async def test_default_owner_id_field(self):
        """Test default owner_id field."""
        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-1")

        result = await authorizer.authorize(user, "read", order)
        assert result is True

    @pytest.mark.asyncio
    async def test_custom_user_id_field(self):
        """Test custom user_id field."""
        authorizer = OwnershipAuthorizer(owner_field="user_id")
        user = CurrentUser(id="user-1", permissions=(), roles=())
        article = Article(id="article-1", user_id="user-1")

        result = await authorizer.authorize(user, "read", article)
        assert result is True

    @pytest.mark.asyncio
    async def test_custom_field_not_owned(self):
        """Test custom field when user doesn't own resource."""
        authorizer = OwnershipAuthorizer(owner_field="user_id")
        user = CurrentUser(id="user-1", permissions=(), roles=())
        article = Article(id="article-1", user_id="user-2")

        result = await authorizer.authorize(user, "read", article)
        assert result is False

    @pytest.mark.asyncio
    async def test_custom_field_not_present(self):
        """Test custom field when resource doesn't have the field."""
        authorizer = OwnershipAuthorizer(owner_field="nonexistent_field")
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-1")

        # Resource doesn't have 'nonexistent_field' field
        result = await authorizer.authorize(user, "read", order)
        assert result is False


class TestPermissionValidation:
    """Test permission format validation (P1-3)."""

    def test_valid_permissions(self):
        """Test that valid permissions are accepted."""
        user = CurrentUser(
            id="user-1",
            permissions=("orders:read", "products:*", "*:admin"),
            roles=("user",),
        )
        assert user.id == "user-1"

    def test_invalid_empty_permission(self):
        """Test that empty permissions are rejected."""
        with pytest.raises(ValueError) as exc_info:
            CurrentUser(
                id="user-1",
                permissions=("",),
                roles=(),
            )
        assert "Invalid permission format" in str(exc_info.value)

    def test_invalid_whitespace_permission(self):
        """Test that whitespace-only permissions are rejected."""
        with pytest.raises(ValueError) as exc_info:
            CurrentUser(
                id="user-1",
                permissions=("   ",),
                roles=(),
            )
        assert "Invalid permission format" in str(exc_info.value)

    def test_invalid_too_long_permission(self):
        """Test that too-long permissions are rejected."""
        with pytest.raises(ValueError) as exc_info:
            CurrentUser(
                id="user-1",
                permissions=("a" * 257,),  # > 256 chars
                roles=(),
            )
        assert "Invalid permission format" in str(exc_info.value)

    def test_valid_roles(self):
        """Test that valid roles are accepted."""
        user = CurrentUser(
            id="user-1",
            permissions=(),
            roles=("admin", "user", "moderator"),
        )
        assert user.id == "user-1"

    def test_invalid_empty_role(self):
        """Test that empty roles are rejected."""
        with pytest.raises(ValueError) as exc_info:
            CurrentUser(
                id="user-1",
                permissions=(),
                roles=("",),
            )
        assert "Invalid role format" in str(exc_info.value)

    def test_invalid_too_long_role(self):
        """Test that too-long roles are rejected."""
        with pytest.raises(ValueError) as exc_info:
            CurrentUser(
                id="user-1",
                permissions=(),
                roles=("a" * 129,),  # > 128 chars
            )
        assert "Invalid role format" in str(exc_info.value)


class TestAuthorizationAuditLogging:
    """Test authorization audit logging (P1-2)."""

    @pytest.mark.asyncio
    async def test_authorized_access_logged(self, caplog):
        """Test that authorized access is logged at DEBUG level by default."""
        import logging
        caplog.set_level(logging.DEBUG)

        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-1")

        await check_resource_access(user, "read", order, authorizer)

        # Check that authorization was logged at DEBUG level
        assert any("Access granted" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_denied_access_logged(self, caplog):
        """Test that denied access is logged at warning level."""
        import logging
        caplog.set_level(logging.WARNING)

        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-1", created_by="user-2")

        with pytest.raises(DomainException):
            await check_resource_access(user, "read", order, authorizer)

        # Check that denial was logged
        assert any("Access denied" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_log_includes_resource_details(self, caplog):
        """Test that denied access log includes resource details."""
        import logging
        caplog.set_level(logging.WARNING)

        authorizer = OwnershipAuthorizer()
        user = CurrentUser(id="user-1", permissions=(), roles=())
        order = Order(id="order-123", created_by="user-2")  # Different owner

        with pytest.raises(DomainException):
            await check_resource_access(user, "read", order, authorizer)

        # Find the denied access log record
        auth_records = [r for r in caplog.records if "Access denied" in r.message]
        assert len(auth_records) > 0

        # Check extra fields
        record = auth_records[0]
        assert record.user_id == "user-1"
        assert record.action == "read"
        assert record.resource_type == "Order"
        assert record.resource_id == "order-123"
        assert record.authorized is False
