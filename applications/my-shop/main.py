"""my-shop - Main FastAPI application entry point."""

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware

from config import settings

# Import context routers
from contexts.catalog.interfaces.category_api import router as categories_router
from contexts.catalog.interfaces.product_api import router as products_router
from contexts.identity.interfaces.user_api import router as users_router
from contexts.ordering.interfaces.order_api import router as orders_router

# Import exception handlers
from shared.exceptions.handlers import (
    generic_exception_handler,
    response_validation_exception_handler,
    validation_exception_handler,
)


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

    # ==================== API 路由聚合 ====================
    # Create API router
    api_router = APIRouter()

    # Health check endpoints
    @api_router.get("/ping")
    async def ping():
        """Ping endpoint for testing"""
        return {"message": "pong"}

    @api_router.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "healthy", "service": "my-shop"}

    # Include domain context routers
    api_router.include_router(products_router, prefix="/products", tags=["products"])
    api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
    api_router.include_router(users_router, prefix="/users", tags=["users"])
    api_router.include_router(categories_router, prefix="/categories", tags=["categories"])

    # Mount API router
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
