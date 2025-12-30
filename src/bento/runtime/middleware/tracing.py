"""HTTP Tracing Middleware - Automatic request tracing.

Provides automatic distributed tracing for all HTTP requests with zero code changes.
Creates a span for each request and records HTTP-level metrics.

Example:
    ```python
    from bento.runtime.middleware import TracingMiddleware

    observability = runtime.container.get("observability")
    app.add_middleware(
        TracingMiddleware,
        observability=observability,
    )
    ```
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from bento.application.ports.observability import ObservabilityProvider

__all__ = ["TracingMiddleware"]


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic HTTP request tracing.

    Automatically creates a span for each HTTP request with:
    - Request method, path, query params
    - Response status code
    - Request duration
    - Client IP
    - Error tracking

    This middleware provides the first layer of observability (HTTP layer),
    which automatically creates parent spans for application-level spans.
    """

    def __init__(self, app, observability: ObservabilityProvider):
        """Initialize tracing middleware.

        Args:
            app: FastAPI application
            observability: Observability provider for tracing/metrics/logging
        """
        super().__init__(app)
        self.tracer = observability.get_tracer("http")
        self.meter = observability.get_meter("http")
        self.logger = observability.get_logger("http")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request with tracing.

        Args:
            request: HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response
        """
        # Create span for this request
        span_name = f"{request.method} {request.url.path}"

        async with self.tracer.start_span(span_name) as span:
            # Set span attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.path", request.url.path)
            span.set_attribute("http.scheme", request.url.scheme)

            if request.client:
                span.set_attribute("http.client_ip", request.client.host)

            if request.url.query:
                span.set_attribute("http.query", request.url.query)

            # Record request start
            start_time = time.time()

            try:
                # Process request
                response = await call_next(request)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Set response attributes
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.duration_ms", duration_ms)

                # Set span status based on HTTP status code
                if response.status_code < 400:
                    span.set_status("ok")
                else:
                    span.set_status("error", f"HTTP {response.status_code}")

                # Record metrics
                self._record_request_metrics(
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                )

                # Log request
                self.logger.info(
                    "HTTP request completed",
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    client_ip=request.client.host if request.client else "unknown",
                )

                return response

            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Record exception
                span.record_exception(e)
                span.set_status("error", str(e))
                span.set_attribute("http.duration_ms", duration_ms)

                # Record failure metrics
                counter = self.meter.create_counter("http_requests_failed")
                counter.add(1, {
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                })

                # Log error
                self.logger.error(
                    "HTTP request failed",
                    method=request.method,
                    path=request.url.path,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_ms=round(duration_ms, 2),
                )

                raise

    def _record_request_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Record HTTP request metrics.

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
        """
        # Record request count
        counter = self.meter.create_counter("http_requests_total")
        counter.add(1, {
            "method": method,
            "path": path,
            "status": status_code,
        })

        # Record request duration
        histogram = self.meter.create_histogram("http_request_duration_ms")
        histogram.record(duration_ms, {
            "method": method,
            "path": path,
        })

        # Record status code distribution
        counter = self.meter.create_counter(f"http_status_{status_code // 100}xx")
        counter.add(1, {
            "method": method,
            "path": path,
        })
