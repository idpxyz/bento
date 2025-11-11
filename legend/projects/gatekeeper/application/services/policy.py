# application/services/policy_service.py
from infrastructure.cache import get_cache
from infrastructure.opa_client import OPAExecutor


class PolicyService:
    def __init__(self, executor=None, ttl=5):
        self.exec = executor or OPAExecutor()
        self.cache = get_cache(maxsize=5000, ttl=ttl)

    async def evaluate(self, principal, action, resource, context):
        key = (principal.get("sub"), action, resource, principal.get("org_id"))
        if key in self.cache:
            return self.cache[key]
        try:
            allowed, meta = await self.exec.allow({
                "user": principal, "action": action, "resource": resource, "context": context
            })
        except Exception:
            scopes = set(principal.get("scope", []))
            need = f"{resource}:{action}"
            allowed, meta = (need in scopes, {"reason": "fallback_scope_only"})
        self.cache[key] = (allowed, meta)
        return allowed, meta
