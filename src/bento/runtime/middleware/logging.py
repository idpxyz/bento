"""Structured logging middleware for request/response tracking.

This middleware provides automatic structured logging for all HTTP requests,
enabling observability, debugging, and security auditing.

Usage:
    ```python
    from bento.runtime.middleware import StructuredLoggingMiddleware

    app = FastAPI()
    app.add_middleware(
        StructuredLoggingMiddleware,
        logger_name="api",
        log_request_body=True,
        log_response_body=False,
    )
    ```
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging.

    Logs HTTP requests and responses in structured JSON format for:
    - Performance monitoring (request duration)
    - Security auditing (who accessed what)
    - Debugging (request/response details)
    - Compliance (audit trail)

    Features:
    - Structured JSON logging
    - Request/response metadata
    - Performance metrics
    - Sensitive data filtering
    - Configurable log levels

    Args:
        app: FastAPI application
        logger_name: Logger name (default: "bento.http")
        log_request_body: Whether to log request body (default: False)
        log_response_body: Whether to log response body (default: False)
        sensitive_headers: Headers to redact (default: Authorization, Cookie, etc.)
        skip_paths: Paths to skip logging (default: /health, /ping)

    Example:
        ```python
        # Logged output (JSON):
        {
            "timestamp": "2025-12-29T10:30:00Z",
            "request_id": "abc-123",
            "method": "POST",
            "path": "/api/v1/orders",
            "status_code": 201,
            "duration_ms": 45.2,
            "client_ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
        }
        ```
    """

    DEFAULT_SENSITIVE_HEADERS = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
        "x-csrf-token",
    }

    DEFAULT_SKIP_PATHS = {
        "/health",
        "/ping",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(
        self,
        app,
        logger_name: str = "bento.http",
        log_request_body: bool = False,
        log_response_body: bool = False,
        sensitive_headers: set[str] | None = None,
        skip_paths: set[str] | None = None,
    ):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.sensitive_headers = (
            sensitive_headers or self.DEFAULT_SENSITIVE_HEADERS
        )
        self.skip_paths = skip_paths or self.DEFAULT_SKIP_PATHS

    def _filter_headers(self, headers: dict) -> dict:
        """Filter sensitive headers."""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value
        return filtered

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with structured logging."""
        # Skip logging for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Extract request metadata
        request_id = getattr(request.state, "request_id", "unknown")
        client_ip = request.client.host if request.client else "unknown"

        # Prepare request log data
        log_data = {
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", "unknown"),
        }

        # Optionally log request headers
        if self.logger.isEnabledFor(logging.DEBUG):
            log_data["headers"] = self._filter_headers(dict(request.headers))

        # Optionally log request body
        if self.log_request_body and request.method in {"POST", "PUT", "PATCH"}:
            try:
                body = await request.body()
                if body:
                    log_data["request_body"] = json.loads(body.decode("utf-8"))
                # Restore body for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": body, "more_body": False}
                request._receive = receive  # type: ignore[attr-defined]
            except Exception:
                log_data["request_body"] = "<unable to parse>"

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Prepare response log data
            log_data.update({
                "event": "http_response",
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            })

            # Optionally log response body
            if self.log_response_body and hasattr(response, "body"):
                try:
                    body_content = response.body
                    if isinstance(body_content, (bytes, bytearray)):
                        log_data["response_body"] = json.loads(
                            body_content.decode("utf-8")
                        )
                    else:
                        log_data["response_body"] = str(body_content)
                except Exception:
                    log_data["response_body"] = "<unable to parse>"

            # Log based on status code
            if response.status_code >= 500:
                self.logger.error(json.dumps(log_data))
            elif response.status_code >= 400:
                self.logger.warning(json.dumps(log_data))
            else:
                self.logger.info(json.dumps(log_data))

            return response

        except Exception as e:
            # Log exception
            duration_ms = (time.time() - start_time) * 1000
            log_data.update({
                "event": "http_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(duration_ms, 2),
            })
            self.logger.error(json.dumps(log_data), exc_info=True)
            raise
