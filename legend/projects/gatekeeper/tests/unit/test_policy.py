# tests/unit/test_policy.py
import pytest
from application.services.policy_service import PolicyService


@pytest.mark.asyncio
async def test_policy_fallback():
    svc = PolicyService(executor=None)
    principal = {"sub": "u1", "scope": ["orders:create"]}
    allowed, meta = await svc.evaluate(principal, "create", "orders", {})
    assert allowed is True
    assert meta["reason"] == "fallback_scope_only"
