"""Middleware Configuration - FastAPI middleware stack setup.

Responsible for configuring all middleware in the correct order.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bento.multitenancy import HeaderTenantResolver, add_tenant_middleware
from bento.runtime import BentoRuntime
from bento.runtime.integrations import setup_security
from bento.runtime.middleware import (
    IdempotencyMiddleware,
    RateLimitingMiddleware,
    RequestIDMiddleware,
    StructuredLoggingMiddleware,
    TracingMiddleware,
)

from config import settings

logger = logging.getLogger(__name__)


def configure_middleware(app: FastAPI, runtime: BentoRuntime) -> None:
    """Configure all middleware for the FastAPI application.

    Middleware are applied in reverse order (last added = first executed).

    Args:
        app: FastAPI application instance
        runtime: BentoRuntime instance for accessing services
    """
    logger.info("Configuring middleware stack...")

    # 1. Security - Authentication and Authorization
    from shared.auth import StubAuthenticator

    setup_security(
        app,
        authenticator=StubAuthenticator(),
        require_auth=True,
        exclude_paths=["/health", "/ping", "/docs", "/openapi.json", "/redoc"],
    )
    logger.info("✅ Security middleware registered (authenticator: StubAuthenticator)")

    # 2. Tenant Context - Multi-tenant identification
    add_tenant_middleware(
        app,
        resolver=HeaderTenantResolver(header_name="X-Tenant-ID"),
        require_tenant=False,
        exclude_paths=["/health", "/ping", "/docs", "/openapi.json", "/redoc"],
        sync_to_security_context=True,
    )
    logger.info("✅ Tenant middleware registered (header: X-Tenant-ID, auto-synced to SecurityContext)")

    # 3. Request ID - Generate unique ID for each request
    app.add_middleware(
        RequestIDMiddleware,
        header_name="X-Request-ID",
    )
    logger.info("✅ RequestID middleware registered (header: X-Request-ID)")

    # 4. Tracing - Automatic distributed tracing for all HTTP requests
    try:
        observability = runtime.container.get("observability")
        app.add_middleware(
            TracingMiddleware,
            observability=observability,
        )
        logger.info("✅ TracingMiddleware registered (automatic HTTP request tracing)")
    except KeyError:
        # Runtime not fully initialized yet (e.g., in tests)
        # TracingMiddleware will be added after runtime initialization
        logger.warning("⚠️ TracingMiddleware skipped (observability not available yet)")

    # 5. Structured Logging - Log all requests with structured data
    app.add_middleware(
        StructuredLoggingMiddleware,
        logger_name="my-shop",
        log_request_body=False,
        log_response_body=False,
        skip_paths={"/health", "/ping", "/metrics"},
    )
    logger.info("✅ StructuredLogging middleware registered (logger: my-shop)")

    # 6. Rate Limiting - Protect API from abuse
    if os.getenv("TESTING") != "true":
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=60,
            requests_per_hour=1000,
            key_func=lambda req: req.client.host if req.client else "unknown",
            skip_paths={"/health", "/ping"},
        )
        logger.info("✅ RateLimiting middleware registered (60 req/min, 1000 req/hour per IP)")
    else:
        logger.info("⚠️ RateLimiting middleware disabled (testing mode)")

    # 7. Idempotency - Prevent duplicate operations
    app.add_middleware(
        IdempotencyMiddleware,
        header_name="X-Idempotency-Key",
        ttl_seconds=86400,
        tenant_id="default",
    )
    logger.info("✅ Idempotency middleware registered (TTL: 24h, header: X-Idempotency-Key)")

    # 8. CORS - Cross-Origin Resource Sharing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"✅ CORS middleware registered (origins: {settings.cors_origins})")

    logger.info("Middleware stack configuration completed")
