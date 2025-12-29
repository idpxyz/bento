"""OpenAPI customization for Swagger UI.

This module provides custom OpenAPI schema modifications to support
custom HTTP headers in Swagger UI.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi_schema(app: FastAPI) -> dict:
    """Customize OpenAPI schema to add global header parameters.

    This adds custom headers to all endpoints in Swagger UI:
    - X-Idempotency-Key: For idempotent operations
    - X-Tenant-ID: For multi-tenant operations
    - X-Request-ID: For request tracing (optional, auto-generated if not provided)

    Args:
        app: FastAPI application instance

    Returns:
        Customized OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

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
            "description": "Request ID for tracing and logging. "
                          "Auto-generated if not provided.",
        },
    }

    # Add custom headers to all POST, PUT, PATCH, DELETE operations
    write_methods = {"post", "put", "patch", "delete"}

    for path_item in openapi_schema.get("paths", {}).values():
        for method, operation in path_item.items():
            if method.lower() in write_methods:
                # Add parameters if not already present
                if "parameters" not in operation:
                    operation["parameters"] = []

                # Add X-Idempotency-Key to write operations
                operation["parameters"].append({
                    "$ref": "#/components/parameters/X-Idempotency-Key"
                })

                # Add X-Tenant-ID to all operations (optional)
                operation["parameters"].append({
                    "$ref": "#/components/parameters/X-Tenant-ID"
                })

                # Add X-Request-ID to all operations (optional)
                operation["parameters"].append({
                    "$ref": "#/components/parameters/X-Request-ID"
                })

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """Setup custom OpenAPI schema for the application.

    Args:
        app: FastAPI application instance
    """
    app.openapi = lambda: custom_openapi_schema(app)
