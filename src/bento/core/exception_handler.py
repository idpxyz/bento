"""FastAPI exception handler for Bento framework.

This module provides exception handlers that convert framework exceptions
into consistent JSON API responses.

Example:
    ```python
    from fastapi import FastAPI
    from bento.core.error_handler import register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)
    ```
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from bento.core.exceptions import BentoException, ExceptionCategory

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for FastAPI application.

    This function sets up handlers for:
    - BentoException (framework exceptions)
    - Unexpected exceptions (fallback)

    Args:
        app: FastAPI application instance

    Example:
        ```python
        from fastapi import FastAPI
        from bento.core.error_handler import register_exception_handlers

        app = FastAPI(title="My API")
        register_exception_handlers(app)

        @app.get("/orders/{order_id}")
        async def get_order(order_id: str):
            # Exceptions are automatically converted to JSON responses
            order = await order_service.get_order(order_id)
            return order
        ```
    """

    @app.exception_handler(BentoException)
    async def handle_bento_exception(  # type: ignore[reportUnknownReturnType]
        request: Request,
        exc: BentoException,
    ) -> JSONResponse:
        """Handle Bento framework exceptions.

        Converts BentoException to structured JSON response with appropriate
        HTTP status code.

        Args:
            request: FastAPI request
            exc: BentoException instance

        Returns:
            JSON response with error details
        """
        # Build log message
        log_message = f"[{exc.category.value.upper()}] {exc.reason_code}: {exc.message}"

        # Log exception with different levels based on category
        log_extra: dict[str, Any] = {
            "category": exc.category.value,
            "reason_code": exc.reason_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        }

        # Log based on severity
        if exc.category == ExceptionCategory.INFRASTRUCTURE:
            # Infrastructure errors are more serious
            logger.error(
                log_message,
                extra=log_extra,
                exc_info=exc.cause,  # Include cause for debugging
            )
        elif exc.category == ExceptionCategory.APPLICATION:
            # Application errors are warnings
            logger.warning(log_message, extra=log_extra)
        else:
            # Domain/Interface errors are info (expected business errors)
            logger.info(log_message, extra=log_extra)

        # Log cause if present (for debugging)
        if exc.cause:
            logger.debug(
                f"Caused by: {type(exc.cause).__name__}: {exc.cause}",
                exc_info=exc.cause,
            )

        # Return JSON response
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    # Import and handle IdempotencyConflictError
    from bento.application.decorators import IdempotencyConflictError
    from bento.persistence.interceptor import OptimisticLockException

    @app.exception_handler(OptimisticLockException)
    async def handle_optimistic_lock(  # type: ignore[reportUnknownReturnType]
        request: Request,
        exc: OptimisticLockException,
    ) -> JSONResponse:
        """Handle optimistic lock conflicts (custom exception)."""
        logger.warning(
            f"Optimistic lock conflict: {exc}",
            extra={"path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=409,
            content={
                "reason_code": "OPTIMISTIC_LOCK_CONFLICT",
                "message": "Resource was modified by another request. Please retry.",
                "category": "infrastructure",
                "details": {},
            },
        )

    # Handle SQLAlchemy native StaleDataError (version_id_col)
    from sqlalchemy.orm.exc import StaleDataError

    @app.exception_handler(StaleDataError)
    async def handle_stale_data(  # type: ignore[reportUnknownReturnType]
        request: Request,
        exc: StaleDataError,
    ) -> JSONResponse:
        """Handle SQLAlchemy native optimistic lock conflicts."""
        logger.warning(
            f"Stale data error (optimistic lock): {exc}",
            extra={"path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=409,
            content={
                "reason_code": "OPTIMISTIC_LOCK_CONFLICT",
                "message": "Resource was modified by another request. Please retry.",
                "category": "infrastructure",
                "details": {},
            },
        )

    @app.exception_handler(IdempotencyConflictError)
    async def handle_idempotency_conflict(  # type: ignore[reportUnknownReturnType]
        request: Request,
        exc: IdempotencyConflictError,
    ) -> JSONResponse:
        """Handle idempotency conflict errors.

        Returns 409 Conflict when same idempotency key is used with different data.
        """
        logger.warning(
            f"Idempotency conflict: {exc}",
            extra={"path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=409,
            content={
                "reason_code": "IDEMPOTENCY_CONFLICT",
                "message": str(exc),
                "category": "application",
                "details": {"idempotency_key": exc.key},
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(  # type: ignore[reportUnknownReturnType]
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions (fallback handler).

        Catches all unhandled exceptions and returns a generic error response
        to avoid exposing internal details.

        Args:
            request: FastAPI request
            exc: Exception instance

        Returns:
            JSON response with generic error message
        """
        # Log unexpected error
        logger.exception(
            f"Unexpected error: {type(exc).__name__}: {exc}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
            },
        )

        # Return generic error response (don't expose internal details)
        return JSONResponse(
            status_code=500,
            content={
                "reason_code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "category": "system",
                "details": {},
            },
        )


def get_exception_responses_schema() -> dict[int, dict[str, Any]]:
    """Get OpenAPI schema for error responses.

    Use this to document error responses in FastAPI route definitions.

    Returns:
        Dictionary mapping HTTP status codes to response schemas

    Example:
        ```python
        from bento.core.error_handler import get_error_responses_schema

        @app.get(
            "/orders/{order_id}",
            responses=get_error_responses_schema()
        )
        async def get_order(order_id: str):
            ...
        ```
    """
    error_response_schema = {
        "type": "object",
        "properties": {
            "reason_code": {
                "type": "string",
                "description": "Reason code from contracts",
                "example": "NOT_FOUND",
            },
            "message": {
                "type": "string",
                "description": "Error message",
                "example": "Order not found",
            },
            "category": {
                "type": "string",
                "description": "Error category",
                "enum": ["domain", "application", "infrastructure", "interface"],
                "example": "domain",
            },
            "details": {
                "type": "object",
                "description": "Additional error details",
                "example": {"order_id": "123"},
            },
        },
    }

    return {
        400: {
            "description": "Bad Request",
            "content": {"application/json": {"schema": error_response_schema}},
        },
        401: {
            "description": "Unauthorized",
            "content": {"application/json": {"schema": error_response_schema}},
        },
        403: {
            "description": "Forbidden",
            "content": {"application/json": {"schema": error_response_schema}},
        },
        404: {
            "description": "Not Found",
            "content": {"application/json": {"schema": error_response_schema}},
        },
        409: {
            "description": "Conflict",
            "content": {"application/json": {"schema": error_response_schema}},
        },
        500: {
            "description": "Internal Server Error",
            "content": {"application/json": {"schema": error_response_schema}},
        },
    }
