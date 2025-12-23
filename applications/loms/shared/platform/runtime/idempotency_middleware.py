from __future__ import annotations

import json
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.responses import JSONResponse

from loms.shared.infra.db.session import AsyncSessionMaker
from loms.shared.infra.idempotency.repository import IdempotencyRepository
from loms.shared.infra.idempotency.service import IdempotencyService
from loms.shared.platform.errors.exceptions import AppError

IDEMPOTENCY_HEADER = "x-idempotency-key"

def _is_write_method(method: str) -> bool:
    return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}

async def idempotency_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    key = request.headers.get(IDEMPOTENCY_HEADER)
    if not key or not _is_write_method(request.method):
        return await call_next(request)

    body_bytes = await request.body()

    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}
    request._receive = receive  # type: ignore[attr-defined]

    try:
        body_obj = json.loads(body_bytes.decode("utf-8") or "{}") if body_bytes else {}
    except Exception:
        body_obj = {"_raw": body_bytes.decode("utf-8", errors="ignore")}

    tenant_id = getattr(request.state, "tenant_id", "demo-tenant")

    async with AsyncSessionMaker() as session:
        repo = IdempotencyRepository(session)
        svc = IdempotencyService(repo)
        req_hash = svc.hash_request(body_obj if isinstance(body_obj, dict) else {"body": body_obj})

        mode, rec = await svc.begin(tenant_id, key, req_hash)
        await session.commit()

        if mode == "REPLAY" and rec and rec.response_status is not None:
            headers = {"X-Idempotent-Replay": "1"}
            try:
                content = json.loads(rec.response_body) if rec.response_body else None
            except Exception:
                content = rec.response_body
            return JSONResponse(status_code=int(rec.response_status), content=content, headers=headers)

        response = await call_next(request)

        # Best-effort store: for JSONResponse store its body bytes; otherwise store empty
        stored = ""
        if isinstance(response, JSONResponse):
            try:
                stored = response.body.decode("utf-8") if isinstance(response.body, (bytes, bytearray)) else str(response.body)
            except Exception:
                stored = ""

        async with AsyncSessionMaker() as session2:
            repo2 = IdempotencyRepository(session2)
            if response.status_code < 500:
                await repo2.mark_succeeded(tenant_id, key, int(response.status_code), stored)
            else:
                await repo2.mark_failed(tenant_id, key, int(response.status_code), stored or None)
            await session2.commit()

        return response
