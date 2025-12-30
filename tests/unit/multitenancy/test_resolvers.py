"""Tests for TenantResolver implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bento.multitenancy import (
    CompositeTenantResolver,
    HeaderTenantResolver,
    SubdomainTenantResolver,
    TokenTenantResolver,
)


@dataclass
class MockRequest:
    """Mock request for testing resolvers."""

    headers: dict = field(default_factory=dict)
    state: Any = None


class TestHeaderTenantResolver:
    """Tests for HeaderTenantResolver."""

    def test_resolves_from_default_header(self):
        """Should resolve tenant from X-Tenant-ID header."""
        resolver = HeaderTenantResolver()
        request = MockRequest(headers={"X-Tenant-ID": "tenant-123"})

        result = resolver.resolve(request)

        assert result == "tenant-123"

    def test_resolves_from_custom_header(self):
        """Should resolve tenant from custom header name."""
        resolver = HeaderTenantResolver(header_name="X-Organization-ID")
        request = MockRequest(headers={"X-Organization-ID": "org-456"})

        result = resolver.resolve(request)

        assert result == "org-456"

    def test_returns_none_when_header_missing(self):
        """Should return None when header is missing."""
        resolver = HeaderTenantResolver()
        request = MockRequest(headers={})

        result = resolver.resolve(request)

        assert result is None


class TestTokenTenantResolver:
    """Tests for TokenTenantResolver."""

    def test_resolves_from_user_metadata(self):
        """Should resolve tenant from request.state.user.metadata."""
        resolver = TokenTenantResolver()

        @dataclass
        class MockUser:
            metadata: dict = field(default_factory=dict)

        class MockState:
            user = MockUser(metadata={"tenant_id": "tenant-from-token"})
            claims = None

        request = MockRequest()
        request.state = MockState()

        result = resolver.resolve(request)

        assert result == "tenant-from-token"

    def test_resolves_from_claims(self):
        """Should resolve tenant from request.state.claims."""
        resolver = TokenTenantResolver()

        class MockState:
            user = None
            claims = {"tenant_id": "tenant-from-claims"}

        request = MockRequest()
        request.state = MockState()

        result = resolver.resolve(request)

        assert result == "tenant-from-claims"

    def test_custom_claim_name(self):
        """Should use custom claim name."""
        resolver = TokenTenantResolver(claim_name="organization_id")

        class MockState:
            user = None
            claims = {"organization_id": "org-123"}

        request = MockRequest()
        request.state = MockState()

        result = resolver.resolve(request)

        assert result == "org-123"

    def test_returns_none_when_no_tenant_in_token(self):
        """Should return None when tenant not in token."""
        resolver = TokenTenantResolver()
        request = MockRequest()

        result = resolver.resolve(request)

        assert result is None


class TestSubdomainTenantResolver:
    """Tests for SubdomainTenantResolver."""

    def test_resolves_from_subdomain(self):
        """Should resolve tenant from subdomain."""
        resolver = SubdomainTenantResolver()
        request = MockRequest(headers={"host": "acme.example.com"})

        result = resolver.resolve(request)

        assert result == "acme"

    def test_resolves_with_port(self):
        """Should handle host with port."""
        resolver = SubdomainTenantResolver()
        request = MockRequest(headers={"host": "acme.example.com:8080"})

        result = resolver.resolve(request)

        assert result == "acme"

    def test_returns_none_for_two_part_domain(self):
        """Should return None for domain without subdomain."""
        resolver = SubdomainTenantResolver()
        request = MockRequest(headers={"host": "example.com"})

        result = resolver.resolve(request)

        assert result is None

    def test_custom_min_parts(self):
        """Should use custom min_parts."""
        resolver = SubdomainTenantResolver(min_parts=2)
        request = MockRequest(headers={"host": "tenant.localhost"})

        result = resolver.resolve(request)

        assert result == "tenant"

    def test_returns_none_when_no_host(self):
        """Should return None when host header missing."""
        resolver = SubdomainTenantResolver()
        request = MockRequest(headers={})

        result = resolver.resolve(request)

        assert result is None


class TestCompositeTenantResolver:
    """Tests for CompositeTenantResolver."""

    def test_tries_resolvers_in_order(self):
        """Should try resolvers in order and return first match."""
        header_resolver = HeaderTenantResolver()
        subdomain_resolver = SubdomainTenantResolver()

        composite = CompositeTenantResolver([header_resolver, subdomain_resolver])

        # Header takes precedence
        request = MockRequest(
            headers={
                "X-Tenant-ID": "from-header",
                "host": "from-subdomain.example.com",
            }
        )

        result = composite.resolve(request)

        assert result == "from-header"

    def test_falls_back_to_next_resolver(self):
        """Should fall back to next resolver when first returns None."""
        header_resolver = HeaderTenantResolver()
        subdomain_resolver = SubdomainTenantResolver()

        composite = CompositeTenantResolver([header_resolver, subdomain_resolver])

        # No header, should fall back to subdomain
        request = MockRequest(headers={"host": "acme.example.com"})

        result = composite.resolve(request)

        assert result == "acme"

    def test_returns_none_when_all_fail(self):
        """Should return None when all resolvers fail."""
        header_resolver = HeaderTenantResolver()
        subdomain_resolver = SubdomainTenantResolver()

        composite = CompositeTenantResolver([header_resolver, subdomain_resolver])

        request = MockRequest(headers={"host": "example.com"})

        result = composite.resolve(request)

        assert result is None

    def test_empty_resolvers_list(self):
        """Should return None with empty resolvers list."""
        composite = CompositeTenantResolver([])
        request = MockRequest()

        result = composite.resolve(request)

        assert result is None
