"""my-shop - Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.exception_handlers import (
    generic_exception_handler,
    response_validation_exception_handler,
    validation_exception_handler,
)
from api.router import api_router
from config import settings


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="完整测试项目",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ==================== 全局异常处理器 ====================
    # 请求验证错误（400 Bad Request）
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # 响应验证错误（500 Internal Server Error，但返回友好信息）
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)

    # 未捕获的异常（500 Internal Server Error）
    app.add_exception_handler(Exception, generic_exception_handler)

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
