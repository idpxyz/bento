"""Tests for M2M authentication."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

import pytest

from bento.security.providers.m2m import M2MAuthMixin, M2MConfig
from bento.security import CurrentUser

pytestmark = pytest.mark.asyncio


@dataclass
class MockRequest:
    """Mock request for testing."""

    headers: dict = field(default_factory=dict)


class TestM2MConfig:
    """Tests for M2MConfig."""

    def test_config_creation(self):
        """Should create M2M config."""
        config = M2MConfig(
            token_url="https://auth.example.com/token",
            client_id="client-123",
            client_secret="secret-456",
            default_permissions=["read", "write"],
            default_roles=["service"],
        )

        assert config.token_url == "https://auth.example.com/token"
        assert config.client_id == "client-123"
        assert config.client_secret == "secret-456"
        assert config.default_permissions == ["read", "write"]
        assert config.default_roles == ["service"]


class TestM2MAuthMixin:
    """Tests for M2MAuthMixin."""

    def _create_mixin_with_config(
        self,
        client_id: str = "client-123",
        client_secret: str = "secret-456",
    ) -> M2MAuthMixin:
        """Create a mixin instance with config."""
        mixin = M2MAuthMixin()
        mixin.m2m_config = M2MConfig(
            token_url="https://auth.example.com/token",
            client_id=client_id,
            client_secret=client_secret,
            default_permissions=["m2m:access"],
            default_roles=["service"],
        )
        return mixin

    def test_supports_m2m_with_config(self):
        """Should return True when config is set."""
        mixin = self._create_mixin_with_config()
        assert mixin.supports_m2m() is True

    def test_supports_m2m_without_config(self):
        """Should return False when config is not set."""
        mixin = M2MAuthMixin()
        assert mixin.supports_m2m() is False

    def test_should_use_m2m_with_explicit_header(self):
        """Should detect M2M from X-M2M-Auth header."""
        mixin = self._create_mixin_with_config()
        request = MockRequest(headers={"X-M2M-Auth": "true"})

        assert mixin.should_use_m2m_auth(request) is True

    def test_should_use_m2m_with_client_id_header(self):
        """Should detect M2M from X-Client-ID header."""
        mixin = self._create_mixin_with_config()
        request = MockRequest(headers={"X-Client-ID": "client-123"})

        assert mixin.should_use_m2m_auth(request) is True

    def test_should_use_m2m_with_basic_auth(self):
        """Should detect M2M from Basic auth header."""
        mixin = self._create_mixin_with_config()
        credentials = base64.b64encode(b"client:secret").decode()
        request = MockRequest(headers={"Authorization": f"Basic {credentials}"})

        assert mixin.should_use_m2m_auth(request) is True

    def test_should_not_use_m2m_with_bearer_token(self):
        """Should not detect M2M with Bearer token."""
        mixin = self._create_mixin_with_config()
        request = MockRequest(headers={"Authorization": "Bearer token123"})

        assert mixin.should_use_m2m_auth(request) is False

    def test_should_not_use_m2m_without_config(self):
        """Should not detect M2M without config."""
        mixin = M2MAuthMixin()
        request = MockRequest(headers={"X-M2M-Auth": "true"})

        assert mixin.should_use_m2m_auth(request) is False

    async def test_authenticate_m2m_with_headers(self):
        """Should authenticate M2M with X-Client headers."""
        mixin = self._create_mixin_with_config()
        request = MockRequest(headers={
            "X-Client-ID": "client-123",
            "X-Client-Secret": "secret-456",
        })

        user = await mixin.authenticate_m2m(request)

        assert user is not None
        assert user.id == "m2m:client-123"
        assert user.permissions == ["m2m:access"]
        assert user.roles == ["service"]
        assert user.metadata["type"] == "m2m"

    async def test_authenticate_m2m_with_basic_auth(self):
        """Should authenticate M2M with Basic auth."""
        mixin = self._create_mixin_with_config()
        credentials = base64.b64encode(b"client-123:secret-456").decode()
        request = MockRequest(headers={
            "Authorization": f"Basic {credentials}",
        })

        user = await mixin.authenticate_m2m(request)

        assert user is not None
        assert user.id == "m2m:client-123"

    async def test_authenticate_m2m_invalid_credentials(self):
        """Should return None for invalid credentials."""
        mixin = self._create_mixin_with_config()
        request = MockRequest(headers={
            "X-Client-ID": "wrong-client",
            "X-Client-Secret": "wrong-secret",
        })

        user = await mixin.authenticate_m2m(request)

        assert user is None

    async def test_authenticate_m2m_missing_secret(self):
        """Should return None when secret is missing."""
        mixin = self._create_mixin_with_config()
        request = MockRequest(headers={
            "X-Client-ID": "client-123",
        })

        user = await mixin.authenticate_m2m(request)

        assert user is None


class TestProviderM2MIntegration:
    """Tests for M2M integration in providers."""

    def test_logto_m2m_config(self):
        """Logto should configure M2M when credentials provided."""
        from bento.security.providers import LogtoAuthenticator

        auth = LogtoAuthenticator(
            endpoint="https://app.logto.app",
            app_id="app-123",
            client_id="m2m-client",
            client_secret="m2m-secret",
            m2m_permissions=["api:access"],
        )

        assert auth.supports_m2m() is True
        assert auth.m2m_config.client_id == "m2m-client"
        assert auth.m2m_config.default_permissions == ["api:access"]

    def test_logto_no_m2m_without_credentials(self):
        """Logto should not enable M2M without credentials."""
        from bento.security.providers import LogtoAuthenticator

        auth = LogtoAuthenticator(
            endpoint="https://app.logto.app",
            app_id="app-123",
        )

        assert auth.supports_m2m() is False

    def test_auth0_m2m_config(self):
        """Auth0 should configure M2M when credentials provided."""
        from bento.security.providers import Auth0Authenticator

        auth = Auth0Authenticator(
            domain="tenant.auth0.com",
            audience="https://api.example.com",
            client_id="m2m-client",
            client_secret="m2m-secret",
        )

        assert auth.supports_m2m() is True
        assert auth.m2m_config.token_url == "https://tenant.auth0.com/oauth/token"

    def test_keycloak_m2m_config(self):
        """Keycloak should configure M2M when secret provided."""
        from bento.security.providers import KeycloakAuthenticator

        auth = KeycloakAuthenticator(
            server_url="https://keycloak.example.com",
            realm="my-realm",
            client_id="my-client",
            client_secret="my-secret",
        )

        assert auth.supports_m2m() is True
        assert "protocol/openid-connect/token" in auth.m2m_config.token_url
