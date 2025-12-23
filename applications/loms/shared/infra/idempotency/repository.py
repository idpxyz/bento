from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loms.shared.infra.idempotency.models import IdempotencyRecord

class IdempotencyRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, tenant_id: str, key: str) -> IdempotencyRecord | None:
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.tenant_id == tenant_id,
            IdempotencyRecord.idempotency_key == key,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_in_progress(self, tenant_id: str, key: str, request_hash: str) -> None:
        self._session.add(IdempotencyRecord(
            tenant_id=tenant_id,
            idempotency_key=key,
            request_hash=request_hash,
            status="IN_PROGRESS",
        ))

    async def mark_succeeded(self, tenant_id: str, key: str, status: int, body_json: str) -> None:
        rec = await self.get(tenant_id, key)
        if rec:
            rec.status = "SUCCEEDED"
            rec.response_status = status
            rec.response_body = body_json

    async def mark_failed(self, tenant_id: str, key: str, status: int, body_json: str | None) -> None:
        rec = await self.get(tenant_id, key)
        if rec:
            rec.status = "FAILED"
            rec.response_status = status
            rec.response_body = body_json
