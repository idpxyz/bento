"""全局异常处理器 - 提供友好的错误响应"""

import logging

from bento.core.errors import ApplicationException
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理请求验证错误 - 400 Bad Request"""
    # 类型转换以获取错误详情
    validation_exc = exc if isinstance(exc, RequestValidationError) else None

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "message": "请求数据格式不正确",
            "details": validation_exc.errors() if validation_exc else str(exc),
            "path": str(request.url.path),
        },
    )


async def response_validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理响应验证错误 - 返回友好的错误信息

    这通常表示服务器内部的数据格式问题，但不应该让用户看到 500 错误。
    记录详细日志供开发者调试。
    """
    logger.error(
        f"Response validation failed for {request.url.path}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "服务器返回数据格式异常，请稍后重试或联系技术支持",
            "request_id": request.headers.get("X-Request-ID", "unknown"),
        },
    )


async def application_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理应用层异常 (ApplicationException)"""
    app_exc = exc if isinstance(exc, ApplicationException) else None

    if not app_exc:
        # 不是 ApplicationException，交给通用处理器
        return await generic_exception_handler(request, exc)

    logger.warning(
        f"Application exception for {request.url.path}: {app_exc.error_code} - {app_exc.details}",
    )

    # 提取错误码（只返回 code 字符串，不是整个对象）
    error_code = (
        app_exc.error_code.code if hasattr(app_exc.error_code, "code") else str(app_exc.error_code)
    )

    # 获取错误消息（使用框架自带的消息）
    error_message = (
        app_exc.error_code.message if hasattr(app_exc.error_code, "message") else str(app_exc)
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": error_message,
            "error_code": error_code,
            "details": app_exc.details,
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

    # 业务验证错误（领域模型抛出的 ValueError）
    if isinstance(exc, ValueError):
        logger.warning(
            f"Business validation error for {request.url.path}: {exc}",
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Business Validation Error",
                "message": "业务规则验证失败",
                "details": str(exc),
                "path": str(request.url.path),
            },
        )

    # 其他未预期的异常
    logger.error(
        f"Unhandled exception for {request.url.path}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "服务器内部错误，请稍后重试",
            "request_id": request.headers.get("X-Request-ID", "unknown"),
        },
    )
