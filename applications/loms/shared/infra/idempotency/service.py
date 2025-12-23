import hashlib, json
from loms.shared.platform.errors.exceptions import AppError

class IdempotencyService:
    def __init__(self, repo):
        self._repo = repo

    def hash_request(self, body: dict) -> str:
        canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def begin(self, tenant_id: str, key: str, request_hash: str):
        rec = await self._repo.get(tenant_id, key)
        if rec is None:
            await self._repo.create_in_progress(tenant_id, key, request_hash)
            return ("NEW", None)

        if rec.request_hash != request_hash:
            raise AppError("IDEMPOTENCY_KEY_MISMATCH", "Idempotency key mismatch")

        if rec.status == "SUCCEEDED":
            return ("REPLAY", rec)

        if rec.status == "IN_PROGRESS":
            raise AppError("STATE_CONFLICT", "Request is in progress")

        return ("RETRY", rec)
