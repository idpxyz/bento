from fastapi import APIRouter, Depends
from loms.shared.infra.db.session import get_session
from loms.shared.platform.runtime.health.checks import contracts_check, db_check

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live():
    return {"status": "ok"}


@router.get("/ready")
async def ready(session=Depends(get_session)):
    ok = (await db_check(session)) and contracts_check()
    return {"status": "ok" if ok else "not_ready"}
