# application/services/audit_service.py
from infrastructure.persistence import AuditRepo


class AuditService:
    def __init__(self, repo: AuditRepo):
        self.repo = repo

    async def write(self, ev: dict):
        await self.repo.insert(ev)

    async def query(self, filters: dict):
        return await self.repo.query(filters)
