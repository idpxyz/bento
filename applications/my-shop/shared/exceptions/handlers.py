"""全局异常处理器 - 提供友好的错误响应

这个模块定义了应用层的异常处理策略，遵循 DDD 原则：
- ValidationException (400) - 请求数据格式错误
- ApplicationException (400/404) - 业务规则验证失败
- ValueError (400) - 领域模型验证失败
- 其他异常 (500) - 未预期的系统错误

使用方式：
    from shared.exceptions import (
        validation_exception_handler,
        response_validation_exception_handler,
        generic_exception_handler,
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
"""

import logging

from bento.core.exceptions import ApplicationException
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理请求验证错误 - 400 Bad Request"""
    # 类型转换以获取错误详情
    validation_exc = exc if isinstance(exc, RequestValidationError) else None

    # 获取 request_id（由 RequestIDMiddleware 设置）
    request_id = getattr(request.state, 'request_id', request.headers.get("X-Request-ID", "unknown"))

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "message": "请求数据格式不正确",
            "details": validation_exc.errors() if validation_exc else str(exc),
            "path": str(request.url.path),
            "request_id": request_id,
        },
    )


async def response_validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理响应验证错误 - 返回友好的错误信息

    这通常表示服务器内部的数据格式问题，但不应该让用户看到 500 错误。
    记录详细日志供开发者调试。
    """
    # 获取 request_id（由 RequestIDMiddleware 设置）
    request_id = getattr(request.state, 'request_id', request.headers.get("X-Request-ID", "unknown"))

    logger.error(
        f"[{request_id}] Response validation failed for {request.url.path}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "服务器返回数据格式异常，请稍后重试或联系技术支持",
            "request_id": request_id,
        },
    )


async def application_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理应用层异常 (ApplicationException)"""
    app_exc = exc if isinstance(exc, ApplicationException) else None

    if not app_exc:
        # 不是 ApplicationException，交给通用处理器
        return await generic_exception_handler(request, exc)

    # 获取 request_id（由 RequestIDMiddleware 设置）
    request_id = getattr(request.state, 'request_id', request.headers.get("X-Request-ID", "unknown"))

    logger.warning(
        f"[{request_id}] Application exception for {request.url.path}: {app_exc.reason_code} - {app_exc.details}",
    )

    # 根据错误类型映射 HTTP 状态码
    status_code = status.HTTP_400_BAD_REQUEST
    error_message = str(app_exc)

    # Resource not found 应该返回 404
    if app_exc.reason_code == "NOT_FOUND" or "not found" in error_message.lower():
        status_code = status.HTTP_404_NOT_FOUND
        error_message = "Resource not found"

    return JSONResponse(
        status_code=status_code,
        content={
            "error": "Application Error",
            "message": error_message,
            "reason_code": str(app_exc.reason_code),
            "details": app_exc.details,
            "path": str(request.url.path),
            "request_id": request_id,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常

    - ApplicationException: 应用层异常 → 400 Bad Request
    - ValueError: 业务验证错误 → 400 Bad Request
    - 其他异常: 500 Internal Server Error
    """
    # 应用层异常（Use Case 抛出的业务错误）
    if isinstance(exc, ApplicationException):
        return await application_exception_handler(request, exc)

    # 获取 request_id（由 RequestIDMiddleware 设置）
    request_id = getattr(request.state, 'request_id', request.headers.get("X-Request-ID", "unknown"))

    # 业务验证错误（领域模型抛出的 ValueError）
    if isinstance(exc, ValueError):
        logger.warning(
            f"[{request_id}] Business validation error for {request.url.path}: {exc}",
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Business Validation Error",
                "message": "业务规则验证失败",
                "details": str(exc),
                "path": str(request.url.path),
                "request_id": request_id,
            },
        )

    # 其他未预期的异常
    logger.error(
        f"[{request_id}] Unhandled exception for {request.url.path}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "服务器内部错误，请稍后重试",
            "request_id": request_id,
        },
    )
