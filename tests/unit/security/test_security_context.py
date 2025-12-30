"""Unit tests for SecurityContext."""

import pytest
from bento.security import SecurityContext, CurrentUser
from bento.core.exceptions import DomainException


class TestSecurityContextUser:
    """Test SecurityContext user functionality."""

    def setup_method(self):
        """Clear context before each test."""
        SecurityContext.clear()

    def test_set_and_get_user(self):
        """Test setting and getting user."""
        user = CurrentUser(
            id="user-1",
            permissions=["read", "write"],
            roles=["admin"],
        )

        SecurityContext.set_user(user)
        retrieved = SecurityContext.get_user()

        assert retrieved is not None
        assert retrieved.id == "user-1"
        assert retrieved.permissions == ["read", "write"]
        assert retrieved.roles == ["admin"]

    def test_get_user_returns_none_when_not_set(self):
        """Test get_user returns None when not set."""
        assert SecurityContext.get_user() is None

    def test_require_user_raises_when_not_set(self):
        """Test require_user raises exception when user not set."""
        with pytest.raises(DomainException) as exc_info:
            SecurityContext.require_user()
        assert exc_info.value.reason_code == "UNAUTHORIZED"

    def test_require_user_returns_user_when_set(self):
        """Test require_user returns user when set."""
        user = CurrentUser(id="user-1", permissions=[], roles=[])
        SecurityContext.set_user(user)

        retrieved = SecurityContext.require_user()
        assert retrieved.id == "user-1"

    def test_set_user_overwrites_previous(self):
        """Test setting user overwrites previous user."""
        user1 = CurrentUser(id="user-1", permissions=[], roles=[])
        user2 = CurrentUser(id="user-2", permissions=[], roles=[])

        SecurityContext.set_user(user1)
        retrieved1 = SecurityContext.get_user()
        assert retrieved1 is not None
        assert retrieved1.id == "user-1"

        SecurityContext.set_user(user2)
        retrieved2 = SecurityContext.get_user()
        assert retrieved2 is not None
        assert retrieved2.id == "user-2"

    def test_set_none_clears_user(self):
        """Test setting None clears user."""
        user = CurrentUser(id="user-1", permissions=[], roles=[])
        SecurityContext.set_user(user)
        assert SecurityContext.get_user() is not None

        SecurityContext.set_user(None)
        assert SecurityContext.get_user() is None

    def test_current_user_has_permission(self):
        """Test CurrentUser.has_permission method."""
        user = CurrentUser(
            id="user-1",
            permissions=["read", "write"],
            roles=["admin"],
        )

        assert user.has_permission("read") is True
        assert user.has_permission("write") is True
        assert user.has_permission("delete") is False

    def test_current_user_with_wildcard_permission(self):
        """Test CurrentUser with wildcard permission."""
        user = CurrentUser(
            id="user-1",
            permissions=["*"],
            roles=["admin"],
        )

        assert user.has_permission("read") is True
        assert user.has_permission("write") is True
        assert user.has_permission("delete") is True
        assert user.has_permission("any-permission") is True

    def test_current_user_with_empty_permissions(self):
        """Test CurrentUser with empty permissions."""
        user = CurrentUser(
            id="user-1",
            permissions=[],
            roles=[],
        )

        assert user.has_permission("read") is False
        assert user.has_permission("write") is False


class TestSecurityContextTenant:
    """Test SecurityContext tenant functionality."""

    def setup_method(self):
        """Clear context before each test."""
        SecurityContext.clear()

    def test_set_and_get_tenant(self):
        """Test setting and getting tenant."""
        SecurityContext.set_tenant("tenant-1")
        assert SecurityContext.get_tenant() == "tenant-1"

    def test_get_tenant_returns_none_when_not_set(self):
        """Test get_tenant returns None when not set."""
        assert SecurityContext.get_tenant() is None

    def test_require_tenant_raises_when_not_set(self):
        """Test require_tenant raises exception when tenant not set."""
        with pytest.raises(DomainException) as exc_info:
            SecurityContext.require_tenant()
        assert exc_info.value.reason_code == "TENANT_REQUIRED"

    def test_require_tenant_returns_tenant_when_set(self):
        """Test require_tenant returns tenant when set."""
        SecurityContext.set_tenant("tenant-1")
        assert SecurityContext.require_tenant() == "tenant-1"

    def test_set_tenant_overwrites_previous(self):
        """Test setting tenant overwrites previous tenant."""
        SecurityContext.set_tenant("tenant-1")
        assert SecurityContext.get_tenant() == "tenant-1"

        SecurityContext.set_tenant("tenant-2")
        assert SecurityContext.get_tenant() == "tenant-2"

    def test_set_none_clears_tenant(self):
        """Test setting None clears tenant."""
        SecurityContext.set_tenant("tenant-1")
        assert SecurityContext.get_tenant() is not None

        SecurityContext.set_tenant(None)
        assert SecurityContext.get_tenant() is None


class TestSecurityContextIntegration:
    """Test SecurityContext integration."""

    def setup_method(self):
        """Clear context before each test."""
        SecurityContext.clear()

    def test_user_and_tenant_coexist(self):
        """Test user and tenant can coexist."""
        user = CurrentUser(id="user-1", permissions=["read"], roles=["user"])
        SecurityContext.set_user(user)
        SecurityContext.set_tenant("tenant-1")

        retrieved_user = SecurityContext.get_user()
        assert retrieved_user is not None
        assert retrieved_user.id == "user-1"
        assert SecurityContext.get_tenant() == "tenant-1"

    def test_clear_clears_all(self):
        """Test clear clears both user and tenant."""
        user = CurrentUser(id="user-1", permissions=[], roles=[])
        SecurityContext.set_user(user)
        SecurityContext.set_tenant("tenant-1")

        assert SecurityContext.get_user() is not None
        assert SecurityContext.get_tenant() is not None

        SecurityContext.clear()
        assert SecurityContext.get_user() is None
        assert SecurityContext.get_tenant() is None

    def test_require_both_user_and_tenant(self):
        """Test requiring both user and tenant."""
        user = CurrentUser(id="user-1", permissions=[], roles=[])
        SecurityContext.set_user(user)
        SecurityContext.set_tenant("tenant-1")

        assert SecurityContext.require_user().id == "user-1"
        assert SecurityContext.require_tenant() == "tenant-1"

    def test_require_user_fails_when_tenant_set(self):
        """Test require_user fails independently of tenant."""
        SecurityContext.set_tenant("tenant-1")

        with pytest.raises(DomainException) as exc_info:
            SecurityContext.require_user()
        assert exc_info.value.reason_code == "UNAUTHORIZED"

    def test_require_tenant_fails_when_user_set(self):
        """Test require_tenant fails independently of user."""
        user = CurrentUser(id="user-1", permissions=[], roles=[])
        SecurityContext.set_user(user)

        with pytest.raises(DomainException) as exc_info:
            SecurityContext.require_tenant()
        assert exc_info.value.reason_code == "TENANT_REQUIRED"
