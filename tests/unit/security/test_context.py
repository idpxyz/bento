from __future__ import annotations

from bento.security import CurrentUser, SecurityContext


def test_security_context_set_get_user():
    """Test setting and getting user from SecurityContext."""
    user = CurrentUser(id="user-123", permissions=["read"], roles=["admin"])

    # Initially no user
    assert SecurityContext.get_user() is None
    assert SecurityContext.is_authenticated() is False

    # Set user
    SecurityContext.set_user(user)

    # Now user is available
    assert SecurityContext.get_user() == user
    assert SecurityContext.is_authenticated() is True
    assert SecurityContext.require_user() == user

    # Clear user
    SecurityContext.clear()
    assert SecurityContext.get_user() is None


def test_security_context_permissions():
    """Test permission checks via SecurityContext."""
    user = CurrentUser(id="user-123", permissions=["orders:read", "orders:write"])
    SecurityContext.set_user(user)

    assert SecurityContext.has_permission("orders:read") is True
    assert SecurityContext.has_permission("orders:delete") is False

    SecurityContext.clear()

    # No user, no permissions
    assert SecurityContext.has_permission("orders:read") is False


def test_security_context_roles():
    """Test role checks via SecurityContext."""
    user = CurrentUser(id="user-123", roles=["admin", "user"])
    SecurityContext.set_user(user)

    assert SecurityContext.has_role("admin") is True
    assert SecurityContext.has_role("superadmin") is False

    SecurityContext.clear()


def test_current_user_permission_methods():
    """Test CurrentUser permission helper methods."""
    user = CurrentUser(
        id="user-123",
        permissions=["orders:read", "orders:write", "products:read"],
        roles=["admin"],
    )

    assert user.has_permission("orders:read") is True
    assert user.has_permission("users:read") is False

    assert user.has_any_permission(["orders:read", "users:read"]) is True
    assert user.has_any_permission(["users:read", "users:write"]) is False

    assert user.has_all_permissions(["orders:read", "orders:write"]) is True
    assert user.has_all_permissions(["orders:read", "users:read"]) is False

    assert user.has_role("admin") is True
    assert user.has_any_role(["admin", "superadmin"]) is True
