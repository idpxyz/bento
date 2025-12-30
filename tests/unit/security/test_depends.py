"""Tests for security FastAPI depends."""

from __future__ import annotations

import pytest

from bento.security import CurrentUser
from bento.security.context import SecurityContext
from bento.security.depends import (
    get_current_user,
    get_optional_user,
    require_permissions,
    require_roles,
    require_any_role,
)
from bento.core.exceptions import DomainException

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def clear_context():
    """Clear security context before and after each test."""
    SecurityContext.clear()
    yield
    SecurityContext.clear()


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    async def test_returns_user_when_authenticated(self):
        """Should return user when authenticated."""
        user = CurrentUser(id="user-123", permissions=["read"])
        SecurityContext.set_user(user)

        result = await get_current_user()

        assert result.id == "user-123"

    async def test_raises_unauthorized_when_not_authenticated(self):
        """Should raise UNAUTHORIZED when not authenticated."""
        with pytest.raises(DomainException) as exc_info:
            await get_current_user()

        assert exc_info.value.reason_code == "UNAUTHORIZED"


class TestGetOptionalUser:
    """Tests for get_optional_user dependency."""

    async def test_returns_user_when_authenticated(self):
        """Should return user when authenticated."""
        user = CurrentUser(id="user-123")
        SecurityContext.set_user(user)

        result = await get_optional_user()

        assert result is not None
        assert result.id == "user-123"

    async def test_returns_none_when_not_authenticated(self):
        """Should return None when not authenticated."""
        result = await get_optional_user()

        assert result is None


class TestRequirePermissions:
    """Tests for require_permissions dependency factory."""

    async def test_returns_user_with_required_permissions(self):
        """Should return user when they have required permissions."""
        user = CurrentUser(id="user-123", permissions=["read", "write"])
        SecurityContext.set_user(user)

        dependency = require_permissions("read", "write")
        result = await dependency()

        assert result.id == "user-123"

    async def test_raises_forbidden_without_permissions(self):
        """Should raise FORBIDDEN when user lacks permissions."""
        user = CurrentUser(id="user-123", permissions=["read"])
        SecurityContext.set_user(user)

        dependency = require_permissions("read", "write")

        with pytest.raises(DomainException) as exc_info:
            await dependency()

        assert exc_info.value.reason_code == "FORBIDDEN"

    async def test_raises_unauthorized_when_not_authenticated(self):
        """Should raise UNAUTHORIZED when not authenticated."""
        dependency = require_permissions("read")

        with pytest.raises(DomainException) as exc_info:
            await dependency()

        assert exc_info.value.reason_code == "UNAUTHORIZED"


class TestRequireRoles:
    """Tests for require_roles dependency factory."""

    async def test_returns_user_with_all_roles(self):
        """Should return user when they have all required roles."""
        user = CurrentUser(id="user-123", roles=["admin", "moderator"])
        SecurityContext.set_user(user)

        dependency = require_roles("admin", "moderator")
        result = await dependency()

        assert result.id == "user-123"

    async def test_raises_forbidden_without_all_roles(self):
        """Should raise FORBIDDEN when user lacks any role."""
        user = CurrentUser(id="user-123", roles=["admin"])
        SecurityContext.set_user(user)

        dependency = require_roles("admin", "moderator")

        with pytest.raises(DomainException) as exc_info:
            await dependency()

        assert exc_info.value.reason_code == "FORBIDDEN"


class TestRequireAnyRole:
    """Tests for require_any_role dependency factory."""

    async def test_returns_user_with_any_role(self):
        """Should return user when they have any of the roles."""
        user = CurrentUser(id="user-123", roles=["moderator"])
        SecurityContext.set_user(user)

        dependency = require_any_role("admin", "moderator")
        result = await dependency()

        assert result.id == "user-123"

    async def test_raises_forbidden_without_any_role(self):
        """Should raise FORBIDDEN when user has none of the roles."""
        user = CurrentUser(id="user-123", roles=["user"])
        SecurityContext.set_user(user)

        dependency = require_any_role("admin", "moderator")

        with pytest.raises(DomainException) as exc_info:
            await dependency()

        assert exc_info.value.reason_code == "FORBIDDEN"
