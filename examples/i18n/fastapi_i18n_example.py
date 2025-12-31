"""FastAPI i18n integration example.

This example shows how to integrate i18n with FastAPI middleware.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from bento.core import (
    DomainException,
    LocaleContext,
    set_global_message_renderer,
)

# Translation catalog
CATALOG = {
    "zh-CN": {
        "STATE_CONFLICT": "当前状态不允许此操作",
        "NOT_FOUND": "资源不存在: {resource_id}",
        "UNAUTHORIZED": "需要身份认证",
    },
    "en-US": {
        "STATE_CONFLICT": "Current state does not allow this operation",
        "NOT_FOUND": "Resource not found: {resource_id}",
        "UNAUTHORIZED": "Authentication required",
    },
}


class MessageRenderer:
    """Message renderer for FastAPI application."""

    def __init__(self, catalog: dict, default_locale: str = "en-US"):
        self._catalog = catalog
        self._default = default_locale

    def render(
        self,
        reason_code: str,
        fallback: str,
        locale: str | None = None,
        **context,
    ) -> str:
        loc = locale or self._default
        msg = self._catalog.get(loc, {}).get(reason_code, fallback)

        if context:
            try:
                msg = msg.format(**context)
            except (KeyError, ValueError):
                pass

        return msg


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - register i18n renderer."""
    # Register i18n renderer
    renderer = MessageRenderer(CATALOG, default_locale="en-US")
    set_global_message_renderer(renderer)

    print("✅ i18n renderer registered")

    yield

    # Cleanup
    set_global_message_renderer(None)
    print("✅ i18n renderer unregistered")


# Create FastAPI app
app = FastAPI(
    title="Bento i18n Example",
    description="FastAPI application with i18n support",
    lifespan=lifespan,
)


# Locale middleware
@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    """Set locale from Accept-Language header."""
    # Parse Accept-Language header
    accept_lang = request.headers.get("Accept-Language", "en-US")

    # Simple locale detection
    if "zh" in accept_lang.lower():
        locale = "zh-CN"
    else:
        locale = "en-US"

    # Set locale context
    LocaleContext.set(locale)

    try:
        response = await call_next(request)
        return response
    finally:
        # Always clear context
        LocaleContext.clear()


# Exception handler
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    """Handle domain exceptions with i18n support."""
    return {
        "error": {
            "reason_code": exc.reason_code,
            "message": exc.message,  # Already translated by framework
            "locale": LocaleContext.get(),
            "details": exc.details,
        }
    }


# API endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    locale = LocaleContext.get()
    return {
        "message": "Bento i18n Example API",
        "locale": locale,
        "tip": "Set Accept-Language header to 'zh-CN' or 'en-US'",
    }


@app.get("/test/state-conflict")
async def test_state_conflict():
    """Test STATE_CONFLICT exception."""
    raise DomainException(reason_code="STATE_CONFLICT")


@app.get("/test/not-found/{resource_id}")
async def test_not_found(resource_id: str):
    """Test NOT_FOUND exception with interpolation."""
    raise DomainException(
        reason_code="NOT_FOUND",
        details={"resource_id": resource_id}  # Pass via details for interpolation
    )


@app.get("/test/unauthorized")
async def test_unauthorized():
    """Test UNAUTHORIZED exception."""
    raise DomainException(reason_code="UNAUTHORIZED")


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("Starting Bento i18n Example API")
    print("=" * 60)
    print("\nTest endpoints:")
    print("  - GET http://localhost:8000/")
    print("  - GET http://localhost:8000/test/state-conflict")
    print("  - GET http://localhost:8000/test/not-found/123")
    print("  - GET http://localhost:8000/test/unauthorized")
    print("\nTry with different Accept-Language headers:")
    print("  - Accept-Language: en-US")
    print("  - Accept-Language: zh-CN")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
