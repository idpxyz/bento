"""Idempotency middleware for FastAPI applications.

This middleware provides automatic request deduplication using the
IdempotencyRecord persistence layer.

Usage:
    ```python
    from bento.runtime.middleware.idempotency import IdempotencyMiddleware

    app = FastAPI()
    app.add_middleware(
        IdempotencyMiddleware,
        header_name="x-idempotency-key",
        ttl_seconds=86400,
    )
    ```
"""

from __future__ import annotations

import hashlib
import json
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from bento.persistence.idempotency.record import (
    IdempotencyConflictException,
    SqlAlchemyIdempotency,
)


def _is_write_method(method: str) -> bool:
    """Check if the HTTP method is a write operation."""
    return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}


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


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic request deduplication.

    Intercepts write operations (POST, PUT, PATCH, DELETE) with an
    idempotency key header and ensures they are processed exactly once.

    Features:
    - Automatic response caching
    - Request hash validation (prevents parameter tampering)
    - Configurable TTL for cached responses
    - Multi-tenant support

    Args:
        app: FastAPI application
        header_name: Name of the idempotency key header (default: x-idempotency-key)
        ttl_seconds: Time-to-live for cached responses in seconds (default: 86400 = 24h)
        tenant_id: Default tenant ID (default: "default")
    """

    def __init__(
        self,
        app,
        header_name: str = "x-idempotency-key",
        ttl_seconds: int = 86400,
        tenant_id: str = "default",
    ):
        super().__init__(app)
        self.header_name = header_name.lower()
        self.ttl_seconds = ttl_seconds
        self.tenant_id = tenant_id

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with idempotency support."""
        idempotency_key = request.headers.get(self.header_name)

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

        # Get database session from BentoRuntime container
        try:
            # Import here to avoid circular dependency
            from runtime.bootstrap_v2 import get_runtime
            runtime = get_runtime()
            session_factory = runtime.container.get("db.session_factory")
        except Exception:
            # No runtime or session factory available, skip idempotency check
            return await call_next(request)

        # Get tenant ID from request state (if available)
        tenant_id = getattr(request.state, "tenant_id", self.tenant_id)

        # Create session for this request
        async with session_factory() as session:
            # Create idempotency service
            idempotency = SqlAlchemyIdempotency(session, tenant_id=tenant_id)

            try:
                # Check if request was already processed
                existing = await idempotency.lock(
                    idempotency_key=idempotency_key,
                    operation=f"{request.method} {request.url.path}",
                    request_hash=request_hash,
                    ttl_seconds=self.ttl_seconds,
                )

                if existing and existing.state == "COMPLETED":
                    # Return cached response
                    return JSONResponse(
                        content=existing.response,
                        status_code=existing.status_code,
                        headers={"X-Idempotent-Replay": "1"},
                    )

                # Process request
                response = await call_next(request)

                # Store response if successful
                if response.status_code < 500:
                    # Extract response body
                    response_body = {}
                    if isinstance(response, JSONResponse):
                        try:
                            body_content = response.body
                            if isinstance(body_content, (bytes, bytearray)):
                                response_body = json.loads(body_content.decode("utf-8"))
                            else:
                                response_body = json.loads(str(body_content))
                        except Exception:
                            response_body = {"_raw": str(response.body)}

                    # Store response
                    await idempotency.store_response(
                        idempotency_key=idempotency_key,
                        response=response_body,
                        status_code=response.status_code,
                        operation=f"{request.method} {request.url.path}",
                        request_hash=request_hash,
                        ttl_seconds=self.ttl_seconds,
                    )

                    # Commit the transaction
                    await session.commit()

                    # Add header to indicate successful processing
                    response.headers["X-Idempotent-Processed"] = "1"
                else:
                    # Mark as failed (allows retry)
                    await idempotency.mark_failed(idempotency_key)
                    await session.commit()

                return response

            except IdempotencyConflictException as e:
                # Idempotency key conflict (same key, different request)
                return JSONResponse(
                    content={
                        "error": "IDEMPOTENCY_CONFLICT",
                        "message": str(e),
                        "details": e.details,
                    },
                    status_code=409,
                )
            except Exception as e:
                # Rollback on error
                await session.rollback()
                raise
