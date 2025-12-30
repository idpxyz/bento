"""Unit tests for wildcard permission support."""

import pytest
from bento.security import CurrentUser


class TestWildcardPermissions:
    """Test wildcard permission matching."""

    def test_exact_permission_match(self):
        """Test exact permission matching."""
        user = CurrentUser(
            id="user-1",
            permissions=["orders:read", "orders:write"],
        )
        
        assert user.has_permission("orders:read") is True
        assert user.has_permission("orders:write") is True
        assert user.has_permission("products:read") is False

    def test_wildcard_suffix_match(self):
        """Test wildcard suffix matching (e.g., 'orders:*')."""
        user = CurrentUser(
            id="user-1",
            permissions=["orders:*"],
        )
        
        assert user.has_permission("orders:read") is True
        assert user.has_permission("orders:write") is True
        assert user.has_permission("orders:delete") is True
        assert user.has_permission("products:read") is False

    def test_wildcard_prefix_match(self):
        """Test wildcard prefix matching (e.g., '*:read')."""
        user = CurrentUser(
            id="user-1",
            permissions=["*:read"],
        )
        
        assert user.has_permission("orders:read") is True
        assert user.has_permission("products:read") is True
        assert user.has_permission("users:read") is True
        assert user.has_permission("orders:write") is False

    def test_full_wildcard_match(self):
        """Test full wildcard matching (e.g., '*')."""
        user = CurrentUser(
            id="user-1",
            permissions=["*"],
        )
        
        assert user.has_permission("orders:read") is True
        assert user.has_permission("products:write") is True
        assert user.has_permission("users:delete") is True
        assert user.has_permission("anything") is True

    def test_mixed_exact_and_wildcard(self):
        """Test mixed exact and wildcard permissions."""
        user = CurrentUser(
            id="user-1",
            permissions=["orders:*", "products:read", "users:admin:*"],
        )
        
        # Exact matches
        assert user.has_permission("products:read") is True
        
        # Wildcard matches
        assert user.has_permission("orders:write") is True
        assert user.has_permission("users:admin:create") is True
        assert user.has_permission("users:admin:delete") is True
        
        # Non-matches
        assert user.has_permission("products:write") is False
        assert user.has_permission("users:read") is False

    def test_question_mark_wildcard(self):
        """Test question mark wildcard (single character)."""
        user = CurrentUser(
            id="user-1",
            permissions=["order?:read"],
        )
        
        assert user.has_permission("orders:read") is True
        assert user.has_permission("ordert:read") is True
        assert user.has_permission("order:read") is False
        assert user.has_permission("orderss:read") is False

    def test_bracket_pattern(self):
        """Test bracket pattern matching."""
        user = CurrentUser(
            id="user-1",
            permissions=["[op]rders:*"],
        )
        
        assert user.has_permission("orders:read") is True
        assert user.has_permission("prders:read") is True
        assert user.has_permission("arders:read") is False

    def test_performance_exact_match_first(self):
        """Test that exact match is checked first (performance optimization)."""
        user = CurrentUser(
            id="user-1",
            permissions=["orders:read", "orders:*"],
        )
        
        # Should match via exact match (fast path)
        assert user.has_permission("orders:read") is True
        
        # Should match via wildcard
        assert user.has_permission("orders:write") is True

    def test_empty_permissions(self):
        """Test with empty permissions."""
        user = CurrentUser(
            id="user-1",
            permissions=[],
        )
        
        assert user.has_permission("orders:read") is False
        assert user.has_permission("*") is False

    def test_case_sensitive_matching(self):
        """Test that matching is case-sensitive."""
        user = CurrentUser(
            id="user-1",
            permissions=["Orders:*"],
        )
        
        assert user.has_permission("Orders:read") is True
        assert user.has_permission("orders:read") is False

    def test_has_any_permission_with_wildcards(self):
        """Test has_any_permission with wildcard support."""
        user = CurrentUser(
            id="user-1",
            permissions=["orders:*"],
        )
        
        # Should work with wildcard permissions
        assert user.has_any_permission(["orders:read", "products:write"]) is True
        assert user.has_any_permission(["products:read", "users:write"]) is False

    def test_has_all_permissions_with_wildcards(self):
        """Test has_all_permissions with wildcard support."""
        user = CurrentUser(
            id="user-1",
            permissions=["orders:*", "products:*"],
        )
        
        # Should work with wildcard permissions
        assert user.has_all_permissions(["orders:read", "products:write"]) is True
        assert user.has_all_permissions(["orders:read", "users:write"]) is False
