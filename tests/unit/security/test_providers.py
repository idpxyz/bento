from __future__ import annotations

import pytest

from bento.security.models import CurrentUser
from bento.security.providers.base import JWTAuthenticatorBase, JWTConfig
from bento.security.providers.auth0 import Auth0Authenticator
from bento.security.providers.logto import LogtoAuthenticator
from bento.security.providers.m2m import M2MAuthMixin, M2MConfig


class DummyRequest:
    def __init__(self, headers: dict[str, str] | None = None):
        self.headers = headers or {}


class DummyAuthenticator(JWTAuthenticatorBase):
    def __init__(self):
        super().__init__(
            JWTConfig(
                jwks_url="https://example.com/jwks",
                issuer="https://example.com/",
                audience=None,
            )
        )

    def _extract_user_from_claims(self, claims: dict) -> CurrentUser:
        return CurrentUser(id=claims["sub"])


@pytest.mark.asyncio
async def test_jwt_authenticator_base_returns_user_on_success(monkeypatch):
    auth = DummyAuthenticator()

    # Force token extraction and verification without real JWT parsing
    monkeypatch.setattr(auth, "_extract_token", lambda request: "token")

    async def fake_verify(token: str):
        return {"sub": "user-1"}

    monkeypatch.setattr(auth, "_verify_token", fake_verify)

    user = await auth.authenticate(DummyRequest())
    assert user is not None
    assert user.id == "user-1"


@pytest.mark.asyncio
async def test_jwt_authenticator_base_returns_none_without_token():
    auth = DummyAuthenticator()
    user = await auth.authenticate(DummyRequest())
    assert user is None


@pytest.mark.asyncio
async def test_logto_authenticator_prefers_m2m(monkeypatch):
    auth = LogtoAuthenticator(
        endpoint="https://logto.example",
        app_id="app",
        client_id="cid",
        client_secret="secret",
    )

    # Force M2M branch
    monkeypatch.setattr(auth, "should_use_m2m_auth", lambda request: True)

    async def fake_m2m(request):
        return CurrentUser(id="m2m")

    monkeypatch.setattr(auth, "authenticate_m2m", fake_m2m)

    user = await auth.authenticate(DummyRequest())
    assert user is not None
    assert user.id == "m2m"


@pytest.mark.asyncio
async def test_logto_authenticator_falls_back_to_jwt(monkeypatch):
    auth = LogtoAuthenticator(endpoint="https://logto.example", app_id="app")

    # Skip M2M, force base authenticate result
    monkeypatch.setattr(auth, "should_use_m2m_auth", lambda request: False)
    monkeypatch.setattr(auth, "_extract_token", lambda request: "token")

    async def fake_verify(token: str):
        return {"sub": "jwt-user"}

    monkeypatch.setattr(auth, "_verify_token", fake_verify)

    user = await auth.authenticate(DummyRequest())
    assert user is not None
    assert user.id == "jwt-user"


def test_m2m_should_use_and_validate_credentials():
    class DummyM2M(M2MAuthMixin):
        def __init__(self):
            self.m2m_config = M2MConfig(
                token_url="https://example.com/token",
                client_id="cid",
                client_secret="secret",
                default_permissions=["p1"],
                default_roles=["r1"],
            )

    auth = DummyM2M()
    req = DummyRequest(headers={"X-Client-ID": "cid", "X-Client-Secret": "secret"})

    assert auth.supports_m2m() is True
    assert auth.should_use_m2m_auth(req) is True
    assert auth._validate_client_credentials("cid", "secret") is True
    user = auth._create_m2m_user("cid")
    assert user.id == "m2m:cid"
    assert "p1" in user.permissions
    assert "r1" in user.roles


def test_auth0_extract_user_from_claims():
    auth = Auth0Authenticator(domain="tenant.auth0.com", audience="api")
    claims = {
        "sub": "auth0|u1",
        "permissions": ["read"],
        "roles": ["admin"],
        "email": "u@example.com",
        "name": "User",
    }
    user = auth._extract_user_from_claims(claims)
    assert user.id == "auth0|u1"
    assert "read" in user.permissions
    assert "admin" in user.roles
    assert user.metadata["email"] == "u@example.com"
