"""Request ID middleware for distributed tracing.

This middleware generates or extracts a unique request ID for each request,
enabling end-to-end request tracking across distributed systems.

Usage:
    ```python
    from bento.runtime.middleware import RequestIDMiddleware

    app = FastAPI()
    app.add_middleware(
        RequestIDMiddleware,
        header_name="X-Request-ID",
    )
    ```
"""

from __future__ import annotations

import uuid
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware for request ID generation and tracking.

    Generates a unique ID for each request or uses client-provided ID.
    The request ID is:
    - Stored in request.state.request_id for application access
    - Added to response headers for client tracking
    - Can be used for logging and distributed tracing

    Features:
    - Auto-generates UUID if not provided
    - Accepts client-provided request ID
    - Configurable header name
    - Thread-safe

    Args:
        app: FastAPI application
        header_name: Name of the request ID header (default: X-Request-ID)
        generator: Optional custom ID generator function

    Example:
        ```python
        # In application code
        @app.get("/items")
        async def get_items(request: Request):
            request_id = request.state.request_id
            logger.info(f"Processing request {request_id}")
            return {"items": [...]}
        ```
    """

    def __init__(
        self,
        app,
        header_name: str = "X-Request-ID",
        generator: Callable[[], str] | None = None,
    ):
        super().__init__(app)
        self.header_name = header_name
        self.generator = generator or self._default_generator

    @staticmethod
    def _default_generator() -> str:
        """Generate a UUID-based request ID."""
        return str(uuid.uuid4())

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with request ID tracking."""
        # Try to get request ID from header (client-provided)
        request_id = request.headers.get(self.header_name)

        # Generate new ID if not provided
        if not request_id:
            request_id = self.generator()

        # Store in request state for application access
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        return response
