"""全局异常处理器 - 提供友好的错误响应"""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理请求验证错误 - 400 Bad Request"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "message": "请求数据格式不正确",
            "details": exc.errors(),
            "path": str(request.url.path),
        },
    )


async def response_validation_exception_handler(
    request: Request, exc: ResponseValidationError
) -> JSONResponse:
    """处理响应验证错误 - 返回友好的错误信息

    这通常表示服务器内部的数据格式问题，但不应该让用户看到 500 错误。
    记录详细日志供开发者调试。
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.error(
        f"Response validation failed for {request.url.path}: {exc.errors()}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "服务器返回数据格式异常，请稍后重试或联系技术支持",
            "request_id": request.headers.get("X-Request-ID", "unknown"),
            # 生产环境不应该暴露详细错误
            # "details": exc.errors() if settings.DEBUG else None,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常 - 500 Internal Server Error"""
    import logging

    logger = logging.getLogger(__name__)
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
