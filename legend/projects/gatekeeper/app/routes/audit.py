# app/routers/audit.py
from typing import Any, Dict, Optional

from application.services.audit import AuditService
from fastapi import APIRouter, Depends
from infrastructure.persistence import AuditRepo
from pydantic import BaseModel

router = APIRouter()
repo = AuditRepo()


def get_audit_service():
    return AuditService(repo)


class AuditEventRequest(BaseModel):
    actor_sub: str
    org_id: Optional[str] = None
    action: str
    resource_id: Optional[str] = None
    decision: str
    reason: Optional[str] = None
    req_id: str
    extra: Optional[Dict[str, Any]] = None


@router.post("/", status_code=201)
async def write_audit(
    event: AuditEventRequest,
    svc: AuditService = Depends(get_audit_service)
) -> dict:
    await svc.write(event.dict())
    return {"status": "ok"}


@router.get("/events")
async def get_audit_events(actor_sub: str, svc: AuditService = Depends(get_audit_service)):
    events = await svc.query({"actor_sub": actor_sub})
    return {"events": events}
