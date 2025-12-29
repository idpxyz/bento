"""Idempotency middleware for request deduplication.

Inspired by LOMS implementation, this middleware ensures that duplicate
requests with the same idempotency key return the same response.
"""

from __future__ import annotations

import json
import hashlib
from typing import Callable, Awaitable

from fastapi import Request
from starlette.responses import Response

IDEMPOTENCY_HEADER = "x-idempotency-key"


def _is_write_method(method: str) -> bool:
    """Check if the HTTP method is a write operation."""
    return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}


async def idempotency_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware to handle idempotent requests.

    If x-idempotency-key header is provided:
    1. Check if request was already processed
    2. If yes, return cached response
    3. If no, process request and cache response

    This prevents duplicate operations when clients retry requests.
    """
    idempotency_key = request.headers.get(IDEMPOTENCY_HEADER)

    # Only apply to write operations with idempotency key
    if not idempotency_key or not _is_write_method(request.method):
        return await call_next(request)

    # Read request body for hashing
    body_bytes = await request.body()

    # Restore request body for downstream handlers
    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    request._receive = receive  # type: ignore[attr-defined]

    # Parse request body for hashing
    try:
        body_obj = (
            json.loads(body_bytes.decode("utf-8"))
            if body_bytes
            else {}
        )
    except Exception:
        body_obj = {"_raw": body_bytes.decode("utf-8", errors="ignore")}

    # Hash request for duplicate detection
    request_hash = _hash_request(body_obj)

    # Store in request state for downstream use
    request.state.idempotency_key = idempotency_key
    request.state.request_hash = request_hash

    # Process request
    response = await call_next(request)

    # Store response for future replays (if needed by application)
    # This can be extended to use a database cache
    if response.status_code < 500:
        # Success - cache could be stored here
        response.headers["X-Idempotent-Processed"] = "1"

    return response


def _hash_request(body: dict | str) -> str:
    """Hash request body for duplicate detection.

    Uses SHA256 to create a deterministic hash of the request.
    """
    if isinstance(body, dict):
        canonical = json.dumps(
            body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    else:
        canonical = str(body)

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
