"""OpenAPI customization for FastAPI integration.

This module provides custom OpenAPI schema modifications to support
Bento Framework's middleware features in Swagger UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def customize_openapi_for_bento(app: FastAPI) -> dict:
    """Customize OpenAPI schema to add Bento Framework headers.

    This adds custom headers to all endpoints in Swagger UI:
    - X-Idempotency-Key: For idempotent operations (write operations only)
    - X-Tenant-ID: For multi-tenant operations
    - X-Request-ID: For request tracing
    - Accept-Language: For i18n (internationalization)

    Args:
        app: FastAPI application instance

    Returns:
        Customized OpenAPI schema
    """
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema

    try:
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    except Exception as e:
        # If OpenAPI generation fails (e.g., due to Pydantic type issues),
        # return a minimal schema to allow the app to start
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to generate OpenAPI schema: {e}. Using minimal schema.")
        return {
            "openapi": "3.0.0",
            "info": {
                "title": app.title or "API",
                "version": app.version or "1.0.0",
            },
            "paths": {},
        }

    # Define custom headers as reusable components
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["parameters"] = {
        "X-Idempotency-Key": {
            "name": "X-Idempotency-Key",
            "in": "header",
            "required": False,
            "schema": {
                "type": "string",
                "example": "order-20251229-001",
            },
            "description": "Idempotency key for preventing duplicate operations. "
            "Use the same key to retry a request safely. "
            "The response will be cached for 24 hours.",
        },
        "X-Tenant-ID": {
            "name": "X-Tenant-ID",
            "in": "header",
            "required": False,
            "schema": {
                "type": "string",
                "example": "tenant-123",
            },
            "description": "Tenant ID for multi-tenant operations. "
            "Isolates data and operations by tenant.",
        },
        "X-Request-ID": {
            "name": "X-Request-ID",
            "in": "header",
            "required": False,
            "schema": {
                "type": "string",
                "example": "req-abc123",
            },
            "description": "Request ID for tracing and logging. Auto-generated if not provided.",
        },
        "Accept-Language": {
            "name": "Accept-Language",
            "in": "header",
            "required": False,
            "schema": {
                "type": "string",
                "enum": ["zh-CN", "en-US"],
                "example": "zh-CN",
            },
            "description": "Preferred language for response messages (i18n). "
            "Supported values: zh-CN (Chinese), en-US (English). "
            "Defaults to zh-CN if not specified.",
        },
    }

    # Add custom headers to operations
    write_methods = {"post", "put", "patch", "delete"}
    all_methods = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}

    for path_item in openapi_schema.get("paths", {}).values():
        for method, operation in path_item.items():
            method_lower = method.lower()

            # Skip non-HTTP methods
            if method_lower not in all_methods or not isinstance(operation, dict):
                continue

            # Add parameters if not already present
            if "parameters" not in operation:
                operation["parameters"] = []

            # Add X-Idempotency-Key to write operations only
            if method_lower in write_methods:
                operation["parameters"].append(
                    {"$ref": "#/components/parameters/X-Idempotency-Key"}
                )

            # Add X-Tenant-ID to all operations (for multi-tenant data isolation)
            operation["parameters"].append({"$ref": "#/components/parameters/X-Tenant-ID"})

            # Add X-Request-ID to all operations (for request tracing)
            operation["parameters"].append({"$ref": "#/components/parameters/X-Request-ID"})

            # Add Accept-Language to all operations (for i18n)
            operation["parameters"].append({"$ref": "#/components/parameters/Accept-Language"})

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_bento_openapi(app: FastAPI) -> None:
    """Setup custom OpenAPI schema for Bento Framework features.

    This configures the FastAPI application to use Bento's custom OpenAPI schema
    which includes support for:
    - Idempotency headers (X-Idempotency-Key)
    - Multi-tenant headers (X-Tenant-ID)
    - Request tracing headers (X-Request-ID)
    - i18n language headers (Accept-Language)

    Args:
        app: FastAPI application instance

    Example:
        ```python
        from fastapi import FastAPI
        from bento.runtime.integrations.fastapi_openapi import setup_bento_openapi

        app = FastAPI()
        setup_bento_openapi(app)
        ```
    """
    app.openapi = lambda: customize_openapi_for_bento(app)
