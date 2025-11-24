from __future__ import annotations

from bento.security.context import RequestContext


def test_request_context_fields():
    ctx = RequestContext(tenant_id="t1", user_id="u1", scopes=["a", "b"])
    assert ctx.tenant_id == "t1"
    assert ctx.user_id == "u1"
    assert ctx.scopes == ["a", "b"]
