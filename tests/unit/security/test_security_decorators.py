from __future__ import annotations

from dataclasses import dataclass

import pytest

pytestmark = pytest.mark.asyncio

from bento.core.exceptions import DomainException
from bento.security import (
    CurrentUser,
    SecurityContext,
    require_all_permissions,
    require_all_roles,
    require_any_permission,
    require_any_role,
    require_auth,
    require_owner_or_role,
    require_permission,
    require_role,
)


@pytest.fixture(autouse=True)
def clear_context():
    """Clear security context before and after each test."""
    SecurityContext.clear()
    yield
    SecurityContext.clear()


class TestRequireAuth:
    """Tests for @require_auth decorator."""

    async def test_allows_authenticated_user(self):
        user = CurrentUser(id="user-123")
        SecurityContext.set_user(user)

        @require_auth
        async def protected():
            return "success"

        result = await protected()
        assert result == "success"

    async def test_raises_unauthorized_when_not_authenticated(self):
        @require_auth
        async def protected():
            return "success"

        with pytest.raises(DomainException) as exc_info:
            await protected()

        assert exc_info.value.reason_code == "UNAUTHORIZED"


class TestRequirePermission:
    """Tests for @require_permission decorator."""

    async def test_allows_user_with_permission(self):
        user = CurrentUser(id="user-123", permissions=["orders:write"])
        SecurityContext.set_user(user)

        @require_permission("orders:write")
        async def create_order():
            return "created"

        result = await create_order()
        assert result == "created"

    async def test_raises_forbidden_without_permission(self):
        user = CurrentUser(id="user-123", permissions=["orders:read"])
        SecurityContext.set_user(user)

        @require_permission("orders:write")
        async def create_order():
            return "created"

        with pytest.raises(DomainException) as exc_info:
            await create_order()

        assert exc_info.value.reason_code == "FORBIDDEN"
        assert exc_info.value.details["required_permission"] == "orders:write"

    async def test_raises_unauthorized_when_not_authenticated(self):
        @require_permission("orders:write")
        async def create_order():
            return "created"

        with pytest.raises(DomainException) as exc_info:
            await create_order()

        assert exc_info.value.reason_code == "UNAUTHORIZED"


class TestRequireAnyPermission:
    """Tests for @require_any_permission decorator."""

    async def test_allows_user_with_any_permission(self):
        user = CurrentUser(id="user-123", permissions=["orders:admin"])
        SecurityContext.set_user(user)

        @require_any_permission("orders:read", "orders:admin")
        async def view_order():
            return "viewed"

        result = await view_order()
        assert result == "viewed"

    async def test_raises_forbidden_without_any_permission(self):
        user = CurrentUser(id="user-123", permissions=["products:read"])
        SecurityContext.set_user(user)

        @require_any_permission("orders:read", "orders:admin")
        async def view_order():
            return "viewed"

        with pytest.raises(DomainException) as exc_info:
            await view_order()

        assert exc_info.value.reason_code == "FORBIDDEN"
        assert exc_info.value.details["mode"] == "any"


class TestRequireAllPermissions:
    """Tests for @require_all_permissions decorator."""

    async def test_allows_user_with_all_permissions(self):
        user = CurrentUser(id="user-123", permissions=["orders:read", "orders:write"])
        SecurityContext.set_user(user)

        @require_all_permissions("orders:read", "orders:write")
        async def manage_order():
            return "managed"

        result = await manage_order()
        assert result == "managed"

    async def test_raises_forbidden_without_all_permissions(self):
        user = CurrentUser(id="user-123", permissions=["orders:read"])
        SecurityContext.set_user(user)

        @require_all_permissions("orders:read", "orders:write")
        async def manage_order():
            return "managed"

        with pytest.raises(DomainException) as exc_info:
            await manage_order()

        assert exc_info.value.reason_code == "FORBIDDEN"
        assert exc_info.value.details["mode"] == "all"


class TestRequireRole:
    """Tests for @require_role decorator."""

    async def test_allows_user_with_role(self):
        user = CurrentUser(id="user-123", roles=["admin"])
        SecurityContext.set_user(user)

        @require_role("admin")
        async def admin_only():
            return "admin access"

        result = await admin_only()
        assert result == "admin access"

    async def test_raises_forbidden_without_role(self):
        user = CurrentUser(id="user-123", roles=["user"])
        SecurityContext.set_user(user)

        @require_role("admin")
        async def admin_only():
            return "admin access"

        with pytest.raises(DomainException) as exc_info:
            await admin_only()

        assert exc_info.value.reason_code == "FORBIDDEN"
        assert exc_info.value.details["required_role"] == "admin"


class TestRequireAnyRole:
    """Tests for @require_any_role decorator."""

    async def test_allows_user_with_any_role(self):
        user = CurrentUser(id="user-123", roles=["moderator"])
        SecurityContext.set_user(user)

        @require_any_role("admin", "moderator")
        async def moderation():
            return "moderated"

        result = await moderation()
        assert result == "moderated"

    async def test_raises_forbidden_without_any_role(self):
        user = CurrentUser(id="user-123", roles=["user"])
        SecurityContext.set_user(user)

        @require_any_role("admin", "moderator")
        async def moderation():
            return "moderated"

        with pytest.raises(DomainException) as exc_info:
            await moderation()

        assert exc_info.value.reason_code == "FORBIDDEN"
        assert exc_info.value.details["mode"] == "any"


class TestRequireAllRoles:
    """Tests for @require_all_roles decorator."""

    async def test_allows_user_with_all_roles(self):
        user = CurrentUser(id="user-123", roles=["admin", "super_admin"])
        SecurityContext.set_user(user)

        @require_all_roles("admin", "super_admin")
        async def super_admin_action():
            return "success"

        result = await super_admin_action()
        assert result == "success"

    async def test_raises_forbidden_without_all_roles(self):
        user = CurrentUser(id="user-123", roles=["admin"])
        SecurityContext.set_user(user)

        @require_all_roles("admin", "super_admin")
        async def super_admin_action():
            return "success"

        with pytest.raises(DomainException) as exc_info:
            await super_admin_action()

        assert exc_info.value.reason_code == "FORBIDDEN"
        assert exc_info.value.details["mode"] == "all"

    async def test_raises_unauthorized_when_not_authenticated(self):
        @require_all_roles("admin")
        async def admin_action():
            return "success"

        with pytest.raises(DomainException) as exc_info:
            await admin_action()

        assert exc_info.value.reason_code == "UNAUTHORIZED"


class TestRequireOwnerOrRole:
    """Tests for @require_owner_or_role decorator."""

    @dataclass
    class Order:
        id: str
        owner_id: str

    async def test_allows_owner(self):
        user = CurrentUser(id="user-123", roles=[])
        SecurityContext.set_user(user)

        order = self.Order(id="order-1", owner_id="user-123")

        @require_owner_or_role("admin")
        async def update_order(o):
            return "updated"

        result = await update_order(order)
        assert result == "updated"

    async def test_allows_admin_non_owner(self):
        user = CurrentUser(id="admin-456", roles=["admin"])
        SecurityContext.set_user(user)

        order = self.Order(id="order-1", owner_id="user-123")

        @require_owner_or_role("admin")
        async def update_order(o):
            return "updated"

        result = await update_order(order)
        assert result == "updated"

    async def test_raises_forbidden_for_non_owner_non_admin(self):
        user = CurrentUser(id="other-789", roles=["user"])
        SecurityContext.set_user(user)

        order = self.Order(id="order-1", owner_id="user-123")

        @require_owner_or_role("admin")
        async def update_order(o):
            return "updated"

        with pytest.raises(DomainException) as exc_info:
            await update_order(order)

        assert exc_info.value.reason_code == "FORBIDDEN"

    async def test_custom_owner_getter(self):
        @dataclass
        class Item:
            id: str
            created_by: str

        user = CurrentUser(id="user-123", roles=[])
        SecurityContext.set_user(user)

        item = Item(id="item-1", created_by="user-123")

        @require_owner_or_role("admin", owner_getter=lambda i: i.created_by)
        async def delete_item(i):
            return "deleted"

        result = await delete_item(item)
        assert result == "deleted"
