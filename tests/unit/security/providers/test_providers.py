"""Tests for security providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bento.security.providers import (
    LogtoAuthenticator,
    Auth0Authenticator,
    KeycloakAuthenticator,
    JWTAuthenticatorBase,
)
from bento.security.providers.base import JWTConfig
from bento.security import CurrentUser


@dataclass
class MockRequest:
    """Mock request for testing."""

    headers: dict = field(default_factory=dict)


class TestLogtoAuthenticator:
    """Tests for LogtoAuthenticator."""

    def test_config_initialization(self):
        """Should initialize with correct JWKS and issuer URLs."""
        auth = LogtoAuthenticator(
            endpoint="https://app.logto.app",
            app_id="my-app",
        )

        assert auth.config.jwks_url == "https://app.logto.app/oidc/.well-known/jwks.json"
        assert auth.config.issuer == "https://app.logto.app/oidc"
        assert auth.config.audience == "my-app"

    def test_endpoint_trailing_slash(self):
        """Should handle trailing slash in endpoint."""
        auth = LogtoAuthenticator(
            endpoint="https://app.logto.app/",
            app_id="my-app",
        )

        assert auth.config.jwks_url == "https://app.logto.app/oidc/.well-known/jwks.json"

    def test_extract_user_from_claims(self):
        """Should extract user from Logto claims."""
        auth = LogtoAuthenticator(
            endpoint="https://app.logto.app",
            app_id="my-app",
        )

        claims = {
            "sub": "user-123",
            "permissions": ["read", "write"],
            "roles": ["admin"],
            "email": "user@example.com",
            "name": "Test User",
            "tenant_id": "tenant-456",
        }

        user = auth._extract_user_from_claims(claims)

        assert user.id == "user-123"
        assert user.permissions == ["read", "write"]
        assert user.roles == ["admin"]
        assert user.metadata["email"] == "user@example.com"
        assert user.metadata["tenant_id"] == "tenant-456"

    def test_custom_claim_names(self):
        """Should use custom claim names."""
        auth = LogtoAuthenticator(
            endpoint="https://app.logto.app",
            app_id="my-app",
            permissions_claim="scopes",
            roles_claim="groups",
        )

        claims = {
            "sub": "user-123",
            "scopes": ["api:read"],
            "groups": ["developers"],
        }

        user = auth._extract_user_from_claims(claims)

        assert user.permissions == ["api:read"]
        assert user.roles == ["developers"]


class TestAuth0Authenticator:
    """Tests for Auth0Authenticator."""

    def test_config_initialization(self):
        """Should initialize with correct JWKS and issuer URLs."""
        auth = Auth0Authenticator(
            domain="tenant.auth0.com",
            audience="https://api.example.com",
        )

        assert auth.config.jwks_url == "https://tenant.auth0.com/.well-known/jwks.json"
        assert auth.config.issuer == "https://tenant.auth0.com/"
        assert auth.config.audience == "https://api.example.com"

    def test_extract_user_from_claims_standard(self):
        """Should extract user from standard Auth0 claims."""
        auth = Auth0Authenticator(
            domain="tenant.auth0.com",
            audience="https://api.example.com",
        )

        claims = {
            "sub": "auth0|user-123",
            "permissions": ["read:orders", "write:orders"],
            "email": "user@example.com",
        }

        user = auth._extract_user_from_claims(claims)

        assert user.id == "auth0|user-123"
        assert user.permissions == ["read:orders", "write:orders"]

    def test_extract_user_with_namespace(self):
        """Should extract user from namespaced claims."""
        auth = Auth0Authenticator(
            domain="tenant.auth0.com",
            audience="https://api.example.com",
            namespace="https://myapp.com/",
        )

        claims = {
            "sub": "auth0|user-123",
            "https://myapp.com/permissions": ["admin"],
            "https://myapp.com/roles": ["superuser"],
            "https://myapp.com/tenant_id": "tenant-789",
        }

        user = auth._extract_user_from_claims(claims)

        assert user.permissions == ["admin"]
        assert user.roles == ["superuser"]
        assert user.metadata["tenant_id"] == "tenant-789"


class TestKeycloakAuthenticator:
    """Tests for KeycloakAuthenticator."""

    def test_config_initialization(self):
        """Should initialize with correct JWKS and issuer URLs."""
        auth = KeycloakAuthenticator(
            server_url="https://keycloak.example.com",
            realm="my-realm",
            client_id="my-client",
        )

        assert auth.config.jwks_url == "https://keycloak.example.com/realms/my-realm/protocol/openid-connect/certs"
        assert auth.config.issuer == "https://keycloak.example.com/realms/my-realm"
        assert auth.config.audience == "my-client"

    def test_extract_realm_roles(self):
        """Should extract realm roles."""
        auth = KeycloakAuthenticator(
            server_url="https://keycloak.example.com",
            realm="my-realm",
            client_id="my-client",
            use_realm_roles=True,
            use_client_roles=False,
        )

        claims = {
            "sub": "user-uuid",
            "realm_access": {
                "roles": ["admin", "user"],
            },
        }

        user = auth._extract_user_from_claims(claims)

        assert user.roles == ["admin", "user"]

    def test_extract_client_roles(self):
        """Should extract client-specific roles."""
        auth = KeycloakAuthenticator(
            server_url="https://keycloak.example.com",
            realm="my-realm",
            client_id="my-client",
            use_realm_roles=False,
            use_client_roles=True,
        )

        claims = {
            "sub": "user-uuid",
            "resource_access": {
                "my-client": {
                    "roles": ["client-admin"],
                },
            },
        }

        user = auth._extract_user_from_claims(claims)

        assert user.roles == ["client-admin"]

    def test_extract_combined_roles(self):
        """Should combine realm and client roles."""
        auth = KeycloakAuthenticator(
            server_url="https://keycloak.example.com",
            realm="my-realm",
            client_id="my-client",
        )

        claims = {
            "sub": "user-uuid",
            "realm_access": {
                "roles": ["user"],
            },
            "resource_access": {
                "my-client": {
                    "roles": ["editor"],
                },
            },
        }

        user = auth._extract_user_from_claims(claims)

        assert "user" in user.roles
        assert "editor" in user.roles

    def test_extract_scopes_as_permissions(self):
        """Should extract scopes as permissions."""
        auth = KeycloakAuthenticator(
            server_url="https://keycloak.example.com",
            realm="my-realm",
            client_id="my-client",
        )

        claims = {
            "sub": "user-uuid",
            "scope": "openid profile email",
        }

        user = auth._extract_user_from_claims(claims)

        assert "openid" in user.permissions
        assert "profile" in user.permissions
        assert "email" in user.permissions


class TestJWTAuthenticatorBase:
    """Tests for JWTAuthenticatorBase."""

    def test_extract_token_with_bearer(self):
        """Should extract token from Bearer header."""

        class TestAuth(JWTAuthenticatorBase):
            def _extract_user_from_claims(self, claims):
                return CurrentUser(id=claims["sub"])

        auth = TestAuth(JWTConfig(
            jwks_url="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
        ))

        request = MockRequest(headers={"Authorization": "Bearer my-token"})
        token = auth._extract_token(request)

        assert token == "my-token"

    def test_extract_token_without_bearer(self):
        """Should return None without Bearer prefix."""

        class TestAuth(JWTAuthenticatorBase):
            def _extract_user_from_claims(self, claims):
                return CurrentUser(id=claims["sub"])

        auth = TestAuth(JWTConfig(
            jwks_url="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
        ))

        request = MockRequest(headers={"Authorization": "Basic abc123"})
        token = auth._extract_token(request)

        assert token is None

    def test_extract_token_missing_header(self):
        """Should return None when Authorization header is missing."""

        class TestAuth(JWTAuthenticatorBase):
            def _extract_user_from_claims(self, claims):
                return CurrentUser(id=claims["sub"])

        auth = TestAuth(JWTConfig(
            jwks_url="https://example.com/.well-known/jwks.json",
            issuer="https://example.com",
        ))

        request = MockRequest(headers={})
        token = auth._extract_token(request)

        assert token is None
