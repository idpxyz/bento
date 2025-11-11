import hashlib
import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Request, status
from infrastructure.cache import get_cache  # Placeholder for cache invalidation

# from application.services.audit import AuditService  # Uncomment if audit supplement needed

router = APIRouter()

LOGTO_WEBHOOK_SECRET = os.getenv("LOGTO_WEBHOOK_SECRET", "your-secret")


def verify_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        LOGTO_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/logto", status_code=status.HTTP_204_NO_CONTENT)
async def logto_webhook(
    request: Request,
    x_logto_signature: str = Header(None)
) -> None:
    raw_body = await request.body()
    if not x_logto_signature or not verify_signature(raw_body, x_logto_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    payload = await request.json()
    event_type = payload.get("event_type")
    # 1. 失效相关缓存（示例：全部清空，实际可按 event_type 精细化）
    cache = get_cache()
    cache.clear()
    # 2. 补审计（如有需要，可调用 AuditService）
    # TODO: 调用审计服务写入审计
    return
