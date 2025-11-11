# domain/models.py
from typing import Dict, Optional


class AuditEvent:
    def __init__(self, actor_sub: str, org_id: str, action: str, resource_id: Optional[str], decision: str, reason: str, req_id: str, extra: Optional[Dict] = None):
        self.actor_sub = actor_sub
        self.org_id = org_id
        self.action = action
        self.resource_id = resource_id
        self.decision = decision
        self.reason = reason
        self.req_id = req_id
        self.extra = extra or {}


class PolicyInput:
    def __init__(self, principal: dict, action: str, resource: str, context: dict):
        self.principal = principal
        self.action = action
        self.resource = resource
        self.context = context
