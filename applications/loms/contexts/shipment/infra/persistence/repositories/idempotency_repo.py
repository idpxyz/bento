from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loms.shared.infra.idempotency.models import IdempotencyRecord

class IdempotencyRepositoryImpl:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, tenant_id: str, key: str, method: str, path: str):
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.tenant_id==tenant_id,
            IdempotencyRecord.idempotency_key==key,
            IdempotencyRecord.method==method,
            IdempotencyRecord.path==path
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def upsert(self, *, tenant_id: str, key: str, method: str, path: str, request_hash: str, status_code: int, response_body: dict):
        rec = await self.get(tenant_id, key, method, path)
        if rec is None:
            rec = IdempotencyRecord(
                tenant_id=tenant_id, idempotency_key=key, method=method, path=path, request_hash=request_hash,
                status_code=status_code, response_body=response_body
            )
            self.session.add(rec)
        else:
            rec.request_hash = request_hash
            rec.status_code = status_code
            rec.response_body = response_body
