# app/routers/policy.py
from typing import Any, Dict, List, Optional

from application.services.policy import PolicyService
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter()


def get_policy_service():
    return PolicyService()


class PolicyEvaluateRequest(BaseModel):
    principal: Dict[str, Any]
    action: str
    resource: str
    context: Dict[str, Any] = {}


class PolicyEvaluateResponse(BaseModel):
    allow: bool
    obligations: Optional[List[str]] = None
    explain: Optional[str] = None


@router.post("/evaluate", response_model=PolicyEvaluateResponse)
async def evaluate(
    payload: PolicyEvaluateRequest,
    svc: PolicyService = Depends(get_policy_service)
) -> PolicyEvaluateResponse:
    allowed, meta = await svc.evaluate(
        payload.principal, payload.action, payload.resource, payload.context
    )
    return PolicyEvaluateResponse(
        allow=bool(allowed),
        obligations=meta.get("obligations"),
        explain=meta.get("reason")
    )
