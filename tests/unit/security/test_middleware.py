from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bento.security.context import SecurityContext
from bento.security.middleware import add_security_middleware
from bento.security.models import CurrentUser
from bento.security.ports import IAuthenticator


class DummyAuthenticator(IAuthenticator):
    def __init__(self, user: CurrentUser | None):
        self._user = user

    async def authenticate(self, request):
        return self._user


def test_security_middleware_requires_auth_when_configured():
    app = FastAPI()
    add_security_middleware(
        app,
        authenticator=DummyAuthenticator(None),
        require_auth=True,
        exclude_paths=["/health"],
    )

    @app.get("/protected")
    async def protected():  # pragma: no cover  # accessed via routing
        return {"ok": True}

    client = TestClient(app)

    # Excluded path bypasses auth
    assert client.get("/health").status_code != 401

    # Protected path should return 401 when no user and require_auth=True
    resp = client.get("/protected")
    assert resp.status_code == 401
    assert resp.json()["reason_code"] == "UNAUTHORIZED"


def test_security_middleware_sets_and_clears_context():
    app = FastAPI()
    user = CurrentUser(id="u1", permissions=["p"], roles=["r"])
    add_security_middleware(app, authenticator=DummyAuthenticator(user), require_auth=False)

    @app.get("/me")
    async def me():  # pragma: no cover  # accessed via routing
        current = SecurityContext.get_user()
        return {"user": current.id if current else None}

    client = TestClient(app)

    resp = client.get("/me")
    assert resp.status_code == 200
    assert resp.json()["user"] == "u1"

    # Context should be cleared after request
    assert SecurityContext.get_user() is None
