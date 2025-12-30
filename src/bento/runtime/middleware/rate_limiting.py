"""Rate limiting middleware for API protection.

This middleware provides rate limiting to protect APIs from abuse and DDoS attacks.
Supports multiple strategies and storage backends.

Usage:
    ```python
    from bento.runtime.middleware import RateLimitingMiddleware

    app = FastAPI()
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=60,
        key_func=lambda request: request.client.host,
    )
    ```
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for API rate limiting.

    Implements rate limiting using a sliding window algorithm to prevent
    API abuse and ensure fair usage across clients.

    Features:
    - Sliding window rate limiting
    - Configurable limits per time window
    - Custom key extraction (IP, user, API key, etc.)
    - Rate limit headers (X-RateLimit-*)
    - In-memory storage (can be extended to Redis)

    Args:
        app: FastAPI application
        requests_per_minute: Maximum requests per minute (default: 60)
        requests_per_hour: Maximum requests per hour (default: None)
        key_func: Function to extract rate limit key from request
        skip_paths: Paths to skip rate limiting

    Headers added to response:
        X-RateLimit-Limit: Maximum requests allowed
        X-RateLimit-Remaining: Remaining requests in current window
        X-RateLimit-Reset: Unix timestamp when limit resets

    Example:
        ```python
        # Rate limit by IP
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=60,
            key_func=lambda req: req.client.host,
        )

        # Rate limit by user ID
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=100,
            key_func=lambda req: req.state.user.id,
        )

        # Rate limit by API key
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=1000,
            key_func=lambda req: req.headers.get("X-API-Key"),
        )
        ```
    """

    DEFAULT_SKIP_PATHS = {
        "/health",
        "/ping",
        "/metrics",
    }

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int | None = None,
        key_func: Callable[[Request], str] | None = None,
        skip_paths: set[str] | None = None,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.key_func = key_func or self._default_key_func
        self.skip_paths = skip_paths or self.DEFAULT_SKIP_PATHS

        # In-memory storage: {key: [(timestamp, count), ...]}
        # For production, use Redis or similar distributed cache
        self._storage: dict[str, list[tuple[float, int]]] = defaultdict(list)

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Default key function: use client IP."""
        return request.client.host if request.client else "unknown"

    def _cleanup_old_entries(self, key: str, window_seconds: int) -> None:
        """Remove entries older than the time window."""
        now = time.time()
        cutoff = now - window_seconds
        self._storage[key] = [
            (ts, count) for ts, count in self._storage[key]
            if ts > cutoff
        ]

    def _get_request_count(self, key: str, window_seconds: int) -> int:
        """Get total request count in the time window."""
        self._cleanup_old_entries(key, window_seconds)
        return sum(count for _, count in self._storage[key])

    def _record_request(self, key: str) -> None:
        """Record a new request."""
        now = time.time()
        self._storage[key].append((now, 1))

    def _get_reset_time(self, window_seconds: int) -> int:
        """Get Unix timestamp when the rate limit resets."""
        return int(time.time() + window_seconds)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # Extract rate limit key
        try:
            key = self.key_func(request)
        except Exception:
            # If key extraction fails, allow request
            return await call_next(request)

        # Check minute limit
        minute_window = 60
        minute_count = self._get_request_count(key, minute_window)
        minute_limit = self.requests_per_minute
        minute_remaining = max(0, minute_limit - minute_count)

        # Check hour limit (if configured)
        if self.requests_per_hour:
            hour_window = 3600
            hour_count = self._get_request_count(key, hour_window)
            hour_limit = self.requests_per_hour
            hour_remaining = max(0, hour_limit - hour_count)

            # Use the more restrictive limit
            if hour_remaining == 0:
                return self._rate_limit_exceeded_response(
                    limit=hour_limit,
                    remaining=0,
                    reset=self._get_reset_time(hour_window),
                )

        # Check if rate limit exceeded
        if minute_count >= minute_limit:
            return self._rate_limit_exceeded_response(
                limit=minute_limit,
                remaining=0,
                reset=self._get_reset_time(minute_window),
            )

        # Record request
        self._record_request(key)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(minute_limit)
        response.headers["X-RateLimit-Remaining"] = str(minute_remaining - 1)
        response.headers["X-RateLimit-Reset"] = str(self._get_reset_time(minute_window))

        return response

    def _rate_limit_exceeded_response(
        self, limit: int, remaining: int, reset: int
    ) -> JSONResponse:
        """Return 429 Too Many Requests response."""
        return JSONResponse(
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "limit": limit,
                "remaining": remaining,
                "reset": reset,
            },
            status_code=429,
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset),
                "Retry-After": str(reset - int(time.time())),
            },
        )
